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
        """Streaming generator — yields SSE event dicts."""
        session = await self._session_repo.get(session_id)
        if session is None:
            yield {"event": "error", "data": {"message": f"Session not found: {session_id}"}}
            return

        # ── 1. Incoming user message ──────────────────────────────────────────
        logger.info(
            "pipeline_start",
            stage="1_user_message",
            module="chat_service",
            request_id=request_id,
            session_id=session_id,
            user_message=user_message_text,
            user_message_len=len(user_message_text),
        )

        # 1. Persist user message
        await self._message_repo.create(
            session_id=session_id,
            role="user",
            content=user_message_text,
        )
        await self._message_repo.db.commit()

        # 2. Title generation
        if session.title == "New Chat":
            try:
                title = await self._session_svc.generate_title(session_id, user_message_text)
                yield {"event": "session_title", "data": {"title": title}}
                await self._session_repo.db.commit()
            except Exception as e:
                logger.warning("title_generation_failed", module="chat_service", error=str(e))
                await self._session_repo.db.rollback()

        # 3. Load history
        history = await self._session_svc.get_history_as_dicts(session_id)
        if history and history[-1]["role"] == "user" and history[-1]["content"] == user_message_text:
            history.pop()

        logger.info(
            "history_loaded",
            stage="2_history",
            module="chat_service",
            request_id=request_id,
            history_turns=len(history),
        )

        # ── 4. Intent routing ─────────────────────────────────────────────────
        try:
            routing = await self._router.classify(user_message_text, history, request_id)
        except Exception as e:
            yield {"event": "error", "data": {"message": str(e)}}
            return

        logger.info(
            "routing_complete",
            stage="3_routing",
            module="chat_service",
            request_id=request_id,
            skill_chosen=routing.skill,
            intent=routing.intent,
            confidence=routing.confidence,
            pass_used=routing.pass_used,
            context_signals=routing.context_signals,
        )
        yield {"event": "routing", "data": routing.to_log_dict()}

        # 5. For streaming, use QA skill with streaming if qa skill
        registry = build_registry(self._llm, self._retrieval)
        skill = registry.resolve(routing.skill)

        # 6. Run skill (non-streaming — stream only for QA)
        try:
            if routing.skill == "qa" or routing.skill == "chat":
                filtered = None

                # ── Retrieval (QA only) ───────────────────────────────────────
                if routing.skill == "qa":
                    logger.info(
                        "retrieval_start",
                        stage="4_retrieval",
                        module="chat_service",
                        request_id=request_id,
                        query=user_message_text,
                    )
                    attribution = await self._retrieval.retrieve(user_message_text)
                    from backend.skills.qa_skill import MIN_RELEVANCE_SCORE
                    from backend.models.source import SourceAttribution
                    relevant = [c for c in attribution.chunks if c.similarity_score >= MIN_RELEVANCE_SCORE]
                    filtered = SourceAttribution(chunks=relevant, retrieval_mode=attribution.retrieval_mode)

                    logger.info(
                        "retrieval_complete",
                        stage="4_retrieval",
                        module="chat_service",
                        request_id=request_id,
                        total_chunks_retrieved=len(attribution.chunks),
                        chunks_after_filter=len(relevant),
                        min_relevance_score=MIN_RELEVANCE_SCORE,
                        retrieval_mode=attribution.retrieval_mode,
                        top_episodes=[
                            f"{c.episode_title} ({c.similarity_score:.2f})"
                            for c in relevant[:3]
                        ],
                    )

                # ── Build prompt context ──────────────────────────────────────
                from backend.context.context_builder import ContextBuilder
                from backend.prompts.qa_prompts import QA_SYSTEM_PROMPT
                from backend.prompts.chat_prompts import CHAT_SYSTEM_PROMPT

                cb = ContextBuilder(self._llm)
                sys_prompt = QA_SYSTEM_PROMPT if routing.skill == "qa" else CHAT_SYSTEM_PROMPT
                context = await cb.build(history, filtered, user_message_text, sys_prompt)

                logger.info(
                    "prompt_built",
                    stage="5_prompt",
                    module="chat_service",
                    request_id=request_id,
                    skill=routing.skill,
                    num_messages=len(context.messages),
                    system_prompt_preview=context.system_prompt[:200].replace("\n", " "),
                    last_user_msg_preview=(
                        context.messages[-1]["content"][:300].replace("\n", " ")
                        if context.messages else ""
                    ),
                )

                # ── Stream from LLM ───────────────────────────────────────────
                logger.info(
                    "llm_stream_start",
                    stage="6_llm",
                    module="chat_service",
                    request_id=request_id,
                    provider=self._llm.provider.name,
                    model=self._llm.provider.model,
                )

                full_response = ""
                async for token in self._llm.generate_stream(context.messages, context.system_prompt):
                    full_response += token
                    yield {"event": "token", "data": {"text": token}}

                logger.info(
                    "llm_stream_done",
                    stage="6_llm",
                    module="chat_service",
                    request_id=request_id,
                    response_len=len(full_response),
                    response_preview=full_response[:300].replace("\n", " "),
                )

                # Emit sources
                sources_json = filtered.model_dump() if filtered else None
                if sources_json:
                    yield {"event": "sources", "data": sources_json}

                # ── Persist ───────────────────────────────────────────────────
                assistant_msg = await self._message_repo.create(
                    session_id=session_id, role="assistant", content=full_response,
                    skill_used=routing.skill, routing_intent=routing.intent, sources_json=sources_json,
                )
                logger.info(
                    "message_persisted",
                    stage="7_persist",
                    module="chat_service",
                    request_id=request_id,
                    message_id=assistant_msg.id,
                    skill_used=routing.skill,
                )
                yield {"event": "done", "data": {"message_id": assistant_msg.id, "artifact": None}}

            else:
                # Ship30 and Artifact — full generation then emit
                logger.info(
                    "skill_run_start",
                    stage="5_skill",
                    module="chat_service",
                    request_id=request_id,
                    skill=routing.skill,
                    query=user_message_text,
                )

                output = await skill.run(user_message_text, history)
                sources_json = output.sources.model_dump() if output.sources else None

                logger.info(
                    "skill_run_done",
                    stage="5_skill",
                    module="chat_service",
                    request_id=request_id,
                    skill=routing.skill,
                    response_len=len(output.content),
                    response_preview=output.content[:300].replace("\n", " "),
                    has_artifact=bool(output.artifact_content),
                    artifact_type=output.artifact_type,
                )

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
                    logger.info(
                        "artifact_created",
                        stage="7_persist",
                        module="chat_service",
                        request_id=request_id,
                        artifact_id=artifact.id,
                        artifact_type=artifact.type,
                        artifact_title=artifact.title,
                    )
                    yield {"event": "artifact", "data": artifact_data}

                if sources_json:
                    yield {"event": "sources", "data": sources_json}

                logger.info(
                    "message_persisted",
                    stage="7_persist",
                    module="chat_service",
                    request_id=request_id,
                    message_id=assistant_msg.id,
                    skill_used=skill.name,
                )
                yield {"event": "done", "data": {"message_id": assistant_msg.id}}

        except RuntimeError as e:
            yield {"event": "error", "data": {"message": str(e)}}
        except Exception as e:
            logger.error("chat_service_error", error=str(e))
            yield {"event": "error", "data": {"message": "An unexpected error occurred. Please try again."}}
