import streamlit as st
import os
import warnings
import time

# Importiamo la grafica
import styles 

# --- IMPORT LOGICA AI ---
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document

# --- 1. SETUP INIZIALE ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="AI Study Master", page_icon="🎓", layout="wide")

# --- 2. FUNZIONI DI LOGICA ---

def reset_conversation():
    st.session_state.messages = []

@st.cache_resource(show_spinner=False)
def get_local_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_pdf_text(uploaded_file):
    text = ""
    try:
        pdf_reader = PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            t = page.extract_text()
            if t: text += t
    except Exception as e:
        st.error(f"Errore lettura PDF: {e}")
        return None
    return text

def build_rag_chain(vectorstore):
    retriever = vectorstore.as_retriever()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.3, streaming=True)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}\n\nRISPONDI USANDO SOLO QUESTO CONTESTO:\n{context}"),
        ("human", "{input}"),
    ])
    
    qa_chain = create_stuff_documents_chain(llm, prompt_template)
    return create_retrieval_chain(retriever, qa_chain)

def get_system_instruction(mode, style, num_questions):
    style_map = {
        "Sintetico": "Sii estremamente conciso. Usa elenchi puntati.",
        "Bilanciato": "Fornisci una risposta chiara e completa.",
        "Esaustivo": "Spiega ogni dettaglio, includi contesto ed esempi."
    }
    style_text = style_map.get(style, "Rispondi normalmente.")

    if mode == "💬 Chat / Spiegazione":
        role = f"Sei un tutor universitario esperto. {style_text}"
    elif mode == "❓ Simulazione Quiz":
        role = (f"Sei un professore d'esame. Genera ORA {num_questions} domande difficili. "
                "Numera le domande. NON dare le soluzioni.")
    elif mode == "🃏 Flashcards":
        role = f"Crea materiale di studio schematico. {style_text}. Formatta: **Termine** -> _Definizione_."
    else:
        role = "Sei un assistente utile."

    return f"RUOLO: {role}"

# --- 3. INTERFACCIA UTENTE ---

def main():
    # --- SIDEBAR ---
    with st.sidebar:
        # LOGO E TITOLO
        st.image("https://cdn-icons-png.flaticon.com/512/4712/4712009.png", width=50)
        st.markdown("### Configurazione")
        
        # --- PULSANTE TEMA (NUOVO!) ---
        # Questo toggle controlla tutto il CSS
        dark_mode = st.toggle("🌙 Modalità Notte", value=False)
        
        # Carica il CSS in base alla scelta dell'utente
        st.markdown(styles.get_css(is_dark_mode=dark_mode), unsafe_allow_html=True)
        
        st.markdown("---")

        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ API Key Attiva")
        else:
            api_key = st.text_input("🔑 Google API Key", type="password")
            if not api_key:
                st.warning("Inserisci la chiave")

        st.markdown("---")
        
        study_mode = st.radio(
            "🧠 Modalità Studio:",
            ["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards"],
            on_change=reset_conversation
        )
        
        response_style = st.select_slider(
            "📏 Lunghezza:",
            options=["Sintetico", "Bilanciato", "Esaustivo"],
            value="Bilanciato",
            on_change=reset_conversation
        )
        
        num_questions = 5
        if study_mode == "❓ Simulazione Quiz":
            num_questions = st.slider("Domande:", 5, 20, 5, on_change=reset_conversation)

        st.markdown("---")
        if st.button("🔄 Pulisci Chat", use_container_width=True):
            reset_conversation()
            st.rerun()

    # --- MAIN AREA ---
    
    # Header
    st.markdown('<div class="main-title">AI Study Master</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Il tuo assistente universitario con Gemini 2.5 Pro</div>', unsafe_allow_html=True)

    # Verifica Key
    if not api_key:
        st.info("👈 Configura la chiave API a sinistra.")
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)
        return

    # Upload
    uploaded_file = st.file_uploader("📂 Trascina qui le dispense (PDF)", type="pdf")

    if not uploaded_file:
        st.markdown("---")
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)

    else:
        os.environ["GOOGLE_API_KEY"] = api_key

        if "vectorstore" not in st.session_state:
            with st.status("⚙️ Analisi Documento...", expanded=True) as status:
                try:
                    raw_text = get_pdf_text(uploaded_file)
                    if not raw_text:
                        st.error("PDF Vuoto.")
                        return
                    
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    chunks = text_splitter.split_text(raw_text)
                    docs = [Document(page_content=t) for t in chunks]

                    embeddings = get_local_embeddings()
                    vectorstore = FAISS.from_documents(docs, embeddings)
                    st.session_state.vectorstore = vectorstore
                    
                    status.update(label="✅ Pronto!", state="complete", expanded=False)
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore critico: {e}")
                    return

        # Setup Chain
        vectorstore = st.session_state.vectorstore
        rag_chain = build_rag_chain(vectorstore)
        system_instr = get_system_instruction(study_mode, response_style, num_questions)

        # Chat
        chat_container = st.container()

        if "messages" not in st.session_state:
            st.session_state.messages = []

        with chat_container:
            for message in st.session_state.messages:
                # Icona diversa in base al tema? No, usiamo emoji standard
                avatar = "🧑‍🎓" if message["role"] == "user" else "🤖"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

        # Input
        placeholder = "Fai una domanda..."
        if study_mode == "❓ Simulazione Quiz":
            placeholder = f"Scrivi 'VIA' per generare {num_questions} domande..."

        if user_input := st.chat_input(placeholder):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with chat_container.chat_message("user", avatar="🧑‍🎓"):
                st.markdown(user_input)

            with chat_container.chat_message("assistant", avatar="🤖"):
                response_stream = rag_chain.stream({
                    "input": user_input,
                    "system_instruction": system_instr
                })
                
                def stream_text():
                    for chunk in response_stream:
                        if 'answer' in chunk:
                            yield chunk['answer']
                
                full_response = st.write_stream(stream_text)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == '__main__':
    main()
