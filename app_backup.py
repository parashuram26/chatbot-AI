import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# App imports
from src.utils import (
    KB_DIR,
    CHROMA_PERSIST_DIR,
    SIMILARITY_THRESHOLD,
    GEMINI_API_KEY,
    MarkdownParser
)
from src.embeddings import EmbeddingEngine
from src.rag_engine import RAGEngine
from src.llm_helper import LLMHelper
from src.ticket_handler import TicketHandler

# Page setup
st.set_page_config(
    page_title="SD01 Helpdesk AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Custom premium CSS styling for UI
st.markdown("""
<style>
    .reportview-container {
        background: #0F172A;
    }
    .main-header {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        background: linear-gradient(90deg, #3B82F6 0%, #8B5CF6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .confidence-badge {
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        margin-left: 0.5rem;
    }
    .confidence-high {
        background-color: #065F46;
        color: #34D399;
        border: 1px solid #059669;
    }
    .confidence-low {
        background-color: #7F1D1D;
        color: #F87171;
        border: 1px solid #B91C1C;
    }
</style>
""", unsafe_allow_html=True)

# Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_escalation" not in st.session_state:
    st.session_state.show_escalation = False
if "api_key" not in st.session_state:
    st.session_state.api_key = GEMINI_API_KEY or ""

# Cached initializations
@st.cache_resource
def get_embedding_engine():
    return EmbeddingEngine()

@st.cache_resource
def get_rag_engine():
    return RAGEngine()

@st.cache_resource
def get_ticket_handler():
    return TicketHandler()

def get_llm_helper():
    key = st.session_state.api_key
    if not key:
        return None
    try:
        return LLMHelper(api_key=key)
    except Exception as e:
        st.error(f"Failed to initialize LLMHelper: {e}")
        return None

# Sidebar Control Console
with st.sidebar:
    st.image("https://img.icons8.com/nolan/128/bot.png", width=70)
    st.markdown("## SD01 Chatbot Panel")
    
    # 1. API Configuration
    st.markdown("### API Credentials")
    api_key_input = st.text_input(
        "Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        help="Input your Google Gemini API Key if it's not set in the .env file."
    )
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
        st.rerun()

    llm_helper = get_llm_helper()
    if not llm_helper:
        st.warning("⚠️ Gemini API Key is missing. Configure it to enable chatbot replies.")

    # 2. Ingestion Controls
    st.markdown("---")
    st.markdown("### Document Ingestion")
    
    rag_engine = get_rag_engine()
    embedder = get_embedding_engine()
    ticket_handler = get_ticket_handler()
    
    files = list(KB_DIR.glob("*.md")) if KB_DIR.exists() else []
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Indexed Chunks", rag_engine.get_document_count())
    with col2:
        st.metric("Source SOPs", len(files))

    if st.button("🔄 Ingest & Re-index", use_container_width=True):
        if not files:
            st.error(f"No Markdown SOP files found in: `{KB_DIR.resolve()}`")
        else:
            with st.spinner("Parsing & Indexing SOPs..."):
                rag_engine.reset_collection()
                all_chunks = []
                for file_path in files:
                    chunks = MarkdownParser.chunk_file(file_path)
                    all_chunks.extend(chunks)
                
                if all_chunks:
                    ids = [f"chunk_{i}" for i in range(len(all_chunks))]
                    texts = [c["text"] for c in all_chunks]
                    embeddings = embedder.embed_documents(texts)
                    metadatas = [c["metadata"] for c in all_chunks]
                    
                    rag_engine.add_documents(
                        ids=ids,
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas
                    )
                    st.success(f"Successfully indexed {len(all_chunks)} chunks!")
                    st.rerun()
                else:
                    st.warning("No text sections parsed from documents.")

    if st.button("🗑️ Clear Vector Database", use_container_width=True, type="secondary"):
        rag_engine.reset_collection()
        st.success("Vector DB wiped clean!")
        st.rerun()

    # 3. Escalated Tickets Dashboard
    st.markdown("---")
    st.markdown("### Escalation Dashboard")
    tickets = ticket_handler.get_all_tickets()
    
    if not tickets:
        st.info("No tickets escalated yet.")
    else:
        st.success(f"🎫 {len(tickets)} Escalated Tickets")
        for t in tickets[-3:]:  # Show last 3 tickets
            with st.expander(f"🔴 {t['Ticket ID']} - {t['Ticket Title']}"):
                st.markdown(f"**Requester:** {t['Name']} ({t['Email']})")
                st.markdown(f"**Priority:** `{t['Priority']}` | **Team:** `{t['Recommended Team']}`")
                st.markdown(f"**Problem Summary:** *{t['Problem Summary']}*")
                st.markdown(f"**Additional Details:** {t['Description']}")
                st.caption(f"Created: {t['Created At']}")

# Main Content Panel
st.markdown("<h1 class='main-header'>SD01 Helpdesk AI Assistant</h1>", unsafe_allow_html=True)
st.markdown("This chatbot provides self-service IT support. Grounded in standard SOPs, the chatbot triggers ticket escalation if response confidence drops.")

# Render existing chat
for idx, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    with st.chat_message(role):
        if role == "assistant" and "confidence" in msg:
            conf_class = "confidence-high" if msg["confidence"] == "High" else "confidence-low"
            st.markdown(
                f"**Assistant** <span class='confidence-badge {conf_class}'>{msg['confidence']} Confidence (Score: {msg['score']:.0f})</span>",
                unsafe_allow_html=True
            )
            st.markdown(msg["content"])
            
            # Show citations if they exist
            if "citations" in msg and msg["citations"]:
                with st.expander("📚 Citations"):
                    for cit in msg["citations"]:
                        st.markdown(f"- `{cit}`")
            
            # Show retrieved chunks references
            if "chunks" in msg and msg["chunks"]:
                with st.expander("🔍 View Grounding References"):
                    for c_idx, chunk in enumerate(msg["chunks"]):
                        st.markdown(f"**Ref #{c_idx+1}** (Match Similarity: {chunk['similarity']:.2f})")
                        st.markdown(f"- *Source:* `{chunk['metadata'].get('source')}`")
                        st.markdown(f"- *Heading:* `{chunk['metadata'].get('headers')}`")
                        st.code(chunk["text"], language="markdown")
                        
            # Escalate button when confidence is below 70
            if msg["score"] < 70 and not st.session_state.show_escalation:
                if st.button("🎫 Escalate to IT Helpdesk", key=f"escalate_btn_{idx}"):
                    st.session_state.show_escalation = True
                    st.rerun()
        else:
            st.markdown(msg["content"])

# Ticket Escalation Form
if st.session_state.show_escalation:
    st.markdown("### 🎫 File Support Ticket")
    st.markdown("Our automated assistant was unable to resolve this issue confidently. Fill out this form to escalate this chat to the L1 Support team.")
    
    with st.form("escalation_form"):
        user_name = st.text_input("Full Name", placeholder="John Doe")
        user_email = st.text_input("Email Address", placeholder="john.doe@company.com")
        issue_desc = st.text_area("Additional Context (Optional)", placeholder="Please elaborate on your problem...")
        
        submitted = st.form_submit_button("Submit Escalation Ticket")
        if submitted:
            if not user_name or not user_email:
                st.error("Name and Email are required to submit an escalation.")
            elif not llm_helper:
                st.error("Unable to generate summary. Gemini API Key is missing.")
            else:
                with st.spinner("Submitting ticket..."):
                    # Find the last user message and the last assistant message with chunks
                    original_question = ""
                    context_chunks = []
                    for m in reversed(st.session_state.messages):
                        if m["role"] == "user" and not original_question:
                            original_question = m["content"]
                        if m["role"] == "assistant" and "chunks" in m and not context_chunks:
                            context_chunks = m["chunks"]
                    
                    ticket = ticket_handler.create_ticket(
                        name=user_name,
                        email=user_email,
                        description=issue_desc,
                        user_question=original_question,
                        retrieved_context=context_chunks,
                        llm_helper=llm_helper
                    )
                    
                    st.success(f"🎉 Support ticket **{ticket['ticket_id']}** created! Details logged to CSV files.")
                    st.session_state.show_escalation = False
                    
                    # Log ticket status into conversation
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"📝 **System Notification:** Filed support ticket [{ticket['ticket_id']}]. Title: *{ticket['ticket_title']}*. Priority: `{ticket['priority']}`. Team: `{ticket['recommended_team']}`."
                    })
                    
                    # Save history to json
                    ticket_handler.save_chat_history(st.session_state.messages)
                    st.rerun()

# Chat Input Flow
if prompt := st.chat_input("Ask an IT question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)
    
    # Save user message to history json
    ticket_handler.save_chat_history(st.session_state.messages)
    
    with st.chat_message("assistant"):
        if not llm_helper:
            ans = "I'm sorry, I cannot answer questions. The Gemini API key has not been configured in the Sidebar/Env settings."
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            ticket_handler.save_chat_history(st.session_state.messages)
        else:
            with st.spinner("Analyzing knowledge base..."):
                query_vector = embedder.embed_query(prompt)
                results = rag_engine.query_similarity(query_vector, n_results=10)
                
                best_similarity = results[0]["similarity"] if results else 0.0
                
                if not results or best_similarity < SIMILARITY_THRESHOLD:
                    ans = "I could not find this in the knowledge base."
                    st.markdown(
                        f"**Assistant** <span class='confidence-badge confidence-low'>Low Confidence (Score: {best_similarity * 100:.0f})</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown(ans)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ans,
                        "confidence": "Low",
                        "score": best_similarity * 100,
                        "chunks": results
                    })
                    ticket_handler.save_chat_history(st.session_state.messages)
                    st.rerun()
                else:
                    llm_response = llm_helper.generate_answer(prompt, results)
                    
                    answer = llm_response.get("answer", "")
                    llm_confidence = llm_response.get("confidence", 0)
                    citations = llm_response.get("citations", [])
                    
                    if llm_confidence >= 70:
                        st.markdown(
                            f"**Assistant** <span class='confidence-badge confidence-high'>High Confidence (Score: {llm_confidence:.0f})</span>",
                            unsafe_allow_html=True
                        )
                        st.markdown(answer)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "confidence": "High",
                            "score": llm_confidence,
                            "chunks": results,
                            "citations": citations
                        })
                        ticket_handler.save_chat_history(st.session_state.messages)
                    else:
                        fallback_msg = f"I found some relevant document sections, but I cannot confidently resolve your request (Confidence: {llm_confidence:.0f}): *{answer}*\n\nWould you like to file a support ticket?"
                        st.markdown(
                            f"**Assistant** <span class='confidence-badge confidence-low'>Low Confidence (Score: {llm_confidence:.0f})</span>",
                            unsafe_allow_html=True
                        )
                        st.markdown(fallback_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": fallback_msg,
                            "confidence": "Low",
                            "score": llm_confidence,
                            "chunks": results,
                            "citations": citations
                        })
                        ticket_handler.save_chat_history(st.session_state.messages)
                        st.rerun()
