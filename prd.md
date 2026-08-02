# Product Requirements Document (PRD)
**Product Name:** Lenny Growth Assistant
**Date:** August 2026

## 1. Executive Summary
Lenny Growth Assistant is a specialized, agentic RAG (Retrieval-Augmented Generation) chatbot. It enables Product Managers, Founders, and Growth Engineers to interactively query and extract actionable insights from the vast repository of Lenny's Podcast Transcripts. The system goes beyond basic Q&A by dynamically routing intents to specialized skills (e.g., generating Markdown templates, HTML UI components, or Ship30 essays) based on the conversation context.

## 2. Target Audience
- **Product Managers**: Seeking frameworks for roadmapping, OKRs, and team alignment.
- **Founders**: Looking for zero-to-one growth strategies and GTM advice.
- **Growth Engineers**: Researching retention, acquisition loops, and monetization tactics.

## 3. Core Objectives
- **High-Fidelity Retrieval**: Surface the most relevant podcast transcript segments with high semantic accuracy.
- **Agentic Routing**: Intelligently classify user queries (e.g., QA vs. Artifact Generation vs. Chit-chat) without requiring manual mode switching by the user.
- **Artifact Generation**: Produce persistent, formatted documents (Markdown/HTML) side-by-side with the chat.
- **Local-First & Privacy**: Support running entirely locally via Ollama to ensure proprietary company queries aren't sent to third-party APIs (while retaining OpenAI/Anthropic fallback for speed/quality if desired).

## 4. Key Features & Requirements

### 4.1. Chat & Conversational UX
- **Real-time Streaming**: LLM responses must stream token-by-token to ensure low perceived latency.
- **Session Management**: Users must be able to create, resume, and delete chat sessions. Sessions should be auto-titled.
- **Source Attribution**: Every grounded response must explicitly show the podcast episodes and specific transcript chunks used, including confidence scores and links.

### 4.2. Agentic Routing Logic
The system must parse incoming user messages and route them to one of four skills:
1. **QA Skill**: Performs hybrid RAG retrieval and answers domain questions.
2. **Chat Skill**: Bypasses RAG to answer conversational meta-questions (e.g., "What did I just ask?") to prevent hallucination.
3. **Artifact Skill**: Generates structured markdown documents or HTML/CSS components.
4. **Ship30 Skill**: Specialized prompt chain to convert insights into Twitter/LinkedIn essays.

### 4.3. Ingestion & Vector DB
- **Automated Ingestion**: Background tasks to pull markdown files from the official GitHub repo, chunk them intelligently (preserving episode context), and embed them.
- **Hybrid Search**: Utilize `pgvector` for dense embedding search combined with traditional lexical search (optional fallback).

## 5. Non-Functional Requirements
- **Performance**: Time-to-first-token (TTFT) should be under 2 seconds.
- **Extensibility**: The "Skill" registry must be decoupled so new agentic behaviors can be added simply by creating a new Python class.
- **Resilience**: The ingestion pipeline must be resumable in case of network failure or API rate limits.

## 6. Out of Scope for v1
- Audio processing (we rely purely on the existing text transcripts).
- Multi-user authentication and RBAC (Role-Based Access Control). Single-tenant local deployment is the v1 focus.
