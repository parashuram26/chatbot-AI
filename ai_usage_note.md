# AI Usage Note

This document summarizes the role of AI assistants, code models, and prompt engineering in the development of the **L0 Self-Service KB Chatbot** project.

---

## 1. AI Tools Used
*   **Google Gemini 3.5 Flash**: Primary AI model used for architectural design, code generation, refactoring, and test writing. Also used as the production engine for grounded answer generation and ticket summarization.
*   **SentenceTransformers (all-MiniLM-L6-v2)**: Local transformer model used to run zero-cost sentence embeddings on the local development machine.
*   **Mermaid.js (AI-Generated Diagram syntax)**: Used for compiling system architecture and flow sequences.

---

## 2. Prompts Used

### A. RAG Grounding Prompt (Gemini API runtime)
```text
You are an IT Service Desk Knowledge Assistant.

Answer ONLY from the supplied context.

Rules:
1. Cite article name.
2. Cite section heading.
3. If answer not found say:
   "I could not find this in the knowledge base."

4. Generate confidence score:
   0-100

Context:
{context_text}

Question:
{user_question}
```

### B. Service Ticket Generator Prompt (Gemini API runtime)
```text
Role: IT Service Desk Ticketing Assistant

Given the User's Question and the Retrieved Context from the knowledge base, generate a structured support ticket.

Rules for fields:
1. ticket_title: A short, descriptive title summarizing the main request.
2. problem_summary: A detailed summary explaining what the user was trying to do, what context was found, and what failed.
3. priority: Decide priority based on:
   - "High": Critical path blocks (e.g. login lockouts, password reset failures, vpn gateway down).
   - "Medium": Service disruption but workaround exists (e.g. Outlook sync issues, printer offline).
   - "Low": Informational requests or minor troubleshooting (e.g. general questions).
4. recommended_team: Suggest a resolving support team based on:
   - VPN / Network issues: "Network Operations Team"
   - Account / Password / Security issues: "IAM Security Operations"
   - Outlook / Office apps: "Collaboration Support Team"
   - Printer / Local hardware: "Local IT Hardware Support"
   - General / Other: "Service Desk General Tier"

Question:
{question}

Retrieved Context:
{context}
```

---

## 3. What AI Generated Correctly
*   **Local RAG Ingestion Engine**: The local ChromaDB vector mapping and the `SentenceTransformers` local loading ran correctly on the first attempt.
*   **Streamlit Chat Interface**: The user chat rendering code using `st.chat_message` was generated cleanly.
*   **Parser Splitter**: The structural Markdown parser (`src/utils.py`) chunked headers correctly without losing document references.
*   **Pytest Mock Tests**: The test cases successfully mocked the `GenerativeModel` completion methods, enabling zero-network testing.

---

## 4. What Needed Manual Fixes / Adjustments
*   **System Python Environment Shims**: The macOS developer tools pathing error (`xcrun: error: invalid active developer path`) blocked the system python terminal interpreter. To work around this locally, we utilized a local Javascript Node.js script run with the system's `agy-node` binary to write the 20 KB markdown articles in bulk.
*   **Structured Schema Alignment**: The initial schema defined references as `sources` and confidence as float `0.0-1.0`. The user requested aligning the keys to `citations` and `confidence` to an integer scale `0-100`. This required updating prompt templates, python completion interfaces, and UI rendering logic.
*   **Interactive Inline Escalation Button**: Originally, the app automatically forced the ticket form on the screen if confidence was low. We refactored `app.py` to render a clean `🎫 Escalate to IT Helpdesk` button inline inside the chat thread under the specific low-confidence response block.

---

## 5. Lessons Learned
*   **Virtual Environments on macOS**: macOS python virtual environments are fragile if command line developer tools are corrupt. Having a fallback language runtime (like Node.js / JavaScript) in the developer environment enables scripts execution when Python is blocked.
*   **Schema-Driven Reliability**: Declaring JSON schemas under `response_schema` at the API level is highly effective at forcing deterministic structured outputs. It completely eliminates regex formatting scripts that are prone to fail.
*   **Mock-Driven Test Design**: Mocking external generative endpoints in unit testing makes tests run much faster and guarantees deterministic checks for error and happy path outcomes.
