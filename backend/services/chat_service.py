"""
services/chat_service.py — Orchestrates the full chat pipeline.

Flow:
  user_message
    → IntentRouter.classify()
    → SkillRegistry.resolve()
    → skill.run() [skill owns retrieval internally]
    → persist Message + Artifact
    → return ChatResult (for SSE streaming via API layer)
"""

import json
import uuid

import structlog

from backend.llm_service.llm_service import LLMService
from backend.models.orm import Message
from backend.repositories.artifact_repo import ArtifactRepository
from backend.repositories.message_repo import MessageRepository
from backend.repositories.session_repo import SessionRepository
from backend.retrieval.retrieval_service import RetrievalService
from backend.router.intent_router import IntentRouter
from backend.services.artifact_service import ArtifactService
from backend.services.session_service import SessionService
from backend.skills.registry import build_registry

logger = structlog.get_logger(__name__)


class ChatService:
    def __init__(
        self,
        llm_service: LLMService,
        retrieval_service: RetrievalService,
        session_repo: SessionRepository,
        message_repo: MessageRepository,
        artifact_repo: ArtifactRepository,
    ) -> None:
        self._llm = llm_service
        self._retrieval = retrieval_service
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._artifact_repo = artifact_repo
        self._router = IntentRouter(llm_service)
        self._artifact_svc = ArtifactService(artifact_repo)
        self._session_svc = SessionService(session_repo, message_repo, llm_service)

    async def handle(
        self,
        session_id: str,
        user_message_text: str,
        request_id: str = "",
    ) -> dict:
        """Full non-streaming pipeline. Returns result dict.

        For streaming, use handle_stream() instead.
        """
        session = await self._session_repo.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        # 1. Persist user message
        user_msg = await self._message_repo.create(
            session_id=session_id,
            role="user",
            content=user_message_text,
        )

        # 2. Generate session title from first message (if still default)
        if session.title == "New Chat":
            await self._session_svc.generate_title(session_id, user_message_text)

        # 3. Load history
        history = await self._session_svc.get_history_as_dicts(session_id)
        # Exclude the current user message (just persisted)
        history = [h for h in history if not (h["role"] == "user" and h["content"] == user_message_text)]

        # 4. Route to skill
        routing = await self._router.classify(user_message_text, history, request_id)
        logger.info("chat_routed", session_id=session_id, **routing.to_log_dict())

        # 5. Build skill registry and resolve
        registry = build_registry(self._llm, self._retrieval)
        skill = registry.resolve(routing.skill)

        # 6. Run skill
        output = await skill.run(user_message_text, history)

        # 7. Persist assistant message
        sources_json = output.sources.model_dump() if output.sources else None
        assistant_msg = await self._message_repo.create(
            session_id=session_id,
            role="assistant",
            content=output.content,
            skill_used=skill.name,
            routing_intent=routing.intent,
            sources_json=sources_json,
        )

        # 8. Persist artifact if produced
        artifact_data = None
        if output.artifact_content and output.artifact_type:
            artifact = await self._artifact_svc.create(
                message_id=assistant_msg.id,
                session_id=session_id,
                artifact_type=output.artifact_type,
                content=output.artifact_content,
                title=output.artifact_title,
            )
            artifact_data = {
                "id": artifact.id,
                "type": artifact.type,
                "content": artifact.content,
                "version": artifact.version,
                "title": artifact.title,
            }

        return {
            "message_id": assistant_msg.id,
            "content": output.content,
            "skill_used": skill.name,
            "routing_intent": routing.intent,
            "sources": sources_json,
            "artifact": artifact_data,
        }

    async def handle_stream(self, session_id: str, user_message_text: str, request_id: str = ""):
        """Streaming generator — yields SSE event dicts.

        Usage (in API layer):
            async for event in chat_service.handle_stream(...):
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
        """
        session = await self._session_repo.get(session_id)
        if session is None:
            yield {"event": "error", "data": {"message": f"Session not found: {session_id}"}}
            return

        # 1. Persist user message
        await self._message_repo.create(
            session_id=session_id,
            role="user",
            content=user_message_text,
        )
        # Commit immediately so the user message is saved and locks are released before long LLM calls
        await self._message_repo.db.commit()

        # 2. Title generation (non-blocking feel)
        if session.title == "New Chat":
            try:
                title = await self._session_svc.generate_title(session_id, user_message_text)
                yield {"event": "session_title", "data": {"title": title}}
                await self._session_repo.db.commit()
            except Exception as e:
                logger.warning("title_generation_failed", error=str(e))
                # Rollback to clear any failed transaction state (e.g. from a DB timeout during flush)
                await self._session_repo.db.rollback()

        # 3. Load history
        history = await self._session_svc.get_history_as_dicts(session_id)
        history = [h for h in history if not (h["role"] == "user" and h["content"] == user_message_text)]

        # 4. Route
        try:
            routing = await self._router.classify(user_message_text, history, request_id)
        except Exception as e:
            yield {"event": "error", "data": {"message": str(e)}}
            return

        yield {"event": "routing", "data": routing.to_log_dict()}

        # 5. For streaming, use QA skill with streaming if qa skill
        registry = build_registry(self._llm, self._retrieval)
        skill = registry.resolve(routing.skill)

        # 6. Run skill (non-streaming — stream only for QA)
        try:
            if routing.skill == "qa":
                # Stream QA responses token by token
                from backend.skills.qa_skill import QASkill
                qa_skill: QASkill = skill

                # Retrieval first
                attribution = await self._retrieval.retrieve(user_message_text)
                from backend.skills.qa_skill import MIN_RELEVANCE_SCORE
                from backend.models.source import SourceAttribution
                relevant = [c for c in attribution.chunks if c.similarity_score >= MIN_RELEVANCE_SCORE]

                if not relevant:
                    yield {"event": "token", "data": {"text": "I don't have information about that in Lenny's transcripts."}}
                    yield {"event": "done", "data": {"sources": None, "artifact": None}}
                    return

                filtered = SourceAttribution(chunks=relevant, retrieval_mode=attribution.retrieval_mode)

                # Build context
                from backend.context.context_builder import ContextBuilder
                from backend.prompts.qa_prompts import QA_SYSTEM_PROMPT, build_retrieval_context
                cb = ContextBuilder(self._llm)
                chunk_dicts = [{"episode_title": c.episode_title, "similarity_score": c.similarity_score, "chunk_text": c.chunk_text} for c in relevant]
                context = await cb.build(history, filtered, user_message_text, QA_SYSTEM_PROMPT)

                # Stream
                full_response = ""
                async for token in self._llm.generate_stream(context.messages, QA_SYSTEM_PROMPT):
                    full_response += token
                    yield {"event": "token", "data": {"text": token}}

                # Emit sources
                sources_json = filtered.model_dump()
                yield {"event": "sources", "data": sources_json}

                # Persist
                assistant_msg = await self._message_repo.create(
                    session_id=session_id, role="assistant", content=full_response,
                    skill_used="qa", routing_intent=routing.intent, sources_json=sources_json,
                )
                yield {"event": "done", "data": {"message_id": assistant_msg.id, "artifact": None}}

            else:
                # Ship30 and Artifact — full generation then emit
                output = await skill.run(user_message_text, history)
                sources_json = output.sources.model_dump() if output.sources else None

                # Stream content as single token chunk
                yield {"event": "token", "data": {"text": output.content}}

                # Persist assistant message
                assistant_msg = await self._message_repo.create(
                    session_id=session_id, role="assistant", content=output.content,
                    skill_used=skill.name, routing_intent=routing.intent, sources_json=sources_json,
                )

                # Artifact
                artifact_data = None
                if output.artifact_content and output.artifact_type:
                    artifact = await self._artifact_svc.create(
                        message_id=assistant_msg.id, session_id=session_id,
                        artifact_type=output.artifact_type, content=output.artifact_content,
                        title=output.artifact_title,
                    )
                    artifact_data = {"id": artifact.id, "type": artifact.type,
                                     "content": artifact.content, "version": artifact.version,
                                     "title": artifact.title}
                    yield {"event": "artifact", "data": artifact_data}

                if sources_json:
                    yield {"event": "sources", "data": sources_json}

                yield {"event": "done", "data": {"message_id": assistant_msg.id}}

        except RuntimeError as e:
            yield {"event": "error", "data": {"message": str(e)}}
        except Exception as e:
            logger.error("chat_service_error", error=str(e))
            yield {"event": "error", "data": {"message": "An unexpected error occurred. Please try again."}}
