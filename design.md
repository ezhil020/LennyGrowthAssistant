# UI/UX Design Document

## Design Philosophy

The Lenny Growth Assistant is designed to feel like a premium, professional-grade developer tool (inspired by interfaces like Cursor, Vercel, and Linear). The core philosophy is **"Information Density with Elegance."** 

Because users (Product Managers, Founders, Engineers) are dealing with complex strategic concepts and long-form podcast transcripts, the UI must stay out of the way while providing powerful mechanisms to drill down into the data.

## Core Layout Structure

The application follows a responsive, multi-pane layout:

1. **The Global Sidebar (Left)**
   - Dedicated to session management and navigation.
   - Contains the "New Chat" button and a chronological list of past sessions.
   - Sessions are auto-titled by the backend LLM based on the first message, keeping the sidebar clean and scannable.

2. **The Chat Interface (Center)**
   - The primary interaction zone.
   - **User Turns**: Right-aligned (or distinct styling) to clearly separate human intent from AI response.
   - **Assistant Turns**: Features a custom `✦` avatar. Responses stream in real-time via Server-Sent Events (SSE) to eliminate perceived latency.
   - **Thinking Indicators**: Smooth CSS animations (`fadeSlideIn`) while waiting for the first token, ensuring the user knows the system is processing (especially important during RAG vector searches).

3. **The Artifact Pane (Right / Split View)**
   - Triggers dynamically when the AI generates a structured document (e.g., a Markdown PRD or an HTML/CSS dashboard).
   - Splits the screen smoothly so the user can continue chatting on the left while reviewing the generated artifact on the right.
   - Features syntax-highlighted source views and live rendering (via secure iframes for HTML).

## UX Details & Micro-Interactions

### 1. Source Attribution (Trust & Verification)
A core challenge of RAG (Retrieval-Augmented Generation) is hallucination. To build trust, every grounded response includes a **Sources Panel**.
- Rendered as a sleek, collapsible accordion below the message.
- Shows exactly how many chunks were retrieved and the retrieval mode (`hybrid`, `vector`, etc.).
- Inside, it displays confidence scores (`similarity_score`) and links directly to the GitHub transcript source.

### 2. Skill Badges
Because the backend uses an Agentic Router to select different "Skills" (QA, Ship30, Artifact, Chat), the UI displays a subtle badge (e.g., `⬡ Q&A` or `✍ Ship30`) next to the assistant's name. This provides transparency into *how* the agent decided to route the query.

### 3. Streaming and Auto-Scroll
- The chat pane intelligently auto-scrolls as tokens stream in.
- The input textarea auto-resizes based on content height (up to a max height) to accommodate long-form prompts without breaking the layout.

## Aesthetics & Theming (Impeccable Style)

We opted for **Vanilla CSS** with a robust CSS Variable design system rather than relying on heavy utility frameworks, allowing for pixel-perfect control over the styling.

- **Color Palette**: A deep, sophisticated dark mode (`#0f1115` background) with subtle borders (`#222`) and vibrant, high-contrast accents for interactive elements.
- **Typography**: Uses modern sans-serif stacks (Inter, system-ui) optimized for legibility at high densities.
- **Micro-animations**: Hover states on source chips, smooth expansion of the sources accordion, and the pulsing of the `Thinking...` dots all contribute to a feeling of a "living" application.
