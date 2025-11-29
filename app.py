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

# Carica il CSS
st.markdown(styles.get_css(), unsafe_allow_html=True)

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
    """Costruisce la catena RAG correggendo l'errore del context"""
    retriever = vectorstore.as_retriever()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.3, streaming=True)
    
    # --- CORREZIONE QUI ---
    # Definiamo esplicitamente {context} nel template, altrimenti LangChain si rompe.
    # {system_instruction} verrà riempito dinamicamente a runtime.
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}\n\nRISPONDI USANDO SOLO QUESTO CONTESTO:\n{context}"),
        ("human", "{input}"),
    ])
    
    qa_chain = create_stuff_documents_chain(llm, prompt_template)
    return create_retrieval_chain(retriever, qa_chain)

def get_system_instruction(mode, style, num_questions):
    """Genera solo la parte 'istruttiva' del prompt"""
    
    # Stile
    style_map = {
        "Sintetico": "Sii estremamente conciso. Usa elenchi puntati.",
        "Bilanciato": "Fornisci una risposta chiara e completa.",
        "Esaustivo": "Spiega ogni dettaglio, includi contesto ed esempi."
    }
    style_text = style_map.get(style, "Rispondi normalmente.")

    # Ruolo
    if mode == "💬 Chat / Spiegazione":
        role = f"Sei un tutor universitario esperto. {style_text}"
    elif mode == "❓ Simulazione Quiz":
        role = (f"Sei un professore d'esame. Genera ORA {num_questions} domande difficili sull'argomento. "
                "Numera le domande. NON dare le soluzioni.")
    elif mode == "🃏 Flashcards":
        role = f"Crea materiale di studio schematico. {style_text}. Formatta: **Termine** -> _Definizione_."
    else:
        role = "Sei un assistente utile."

    # Nota: Non aggiungiamo più {context} qui perché è già nel template sopra
    return f"RUOLO: {role}"

# --- 3. INTERFACCIA UTENTE ---

def main():
    # Header
    st.markdown('<div class="main-title">AI Study Master</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Il tuo assistente universitario personale con Gemini 2.5 Pro</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurazione")
        
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ API Key Cloud Attiva")
        else:
            api_key = st.text_input("🔑 Google API Key", type="password")
            if not api_key:
                st.warning("Inserisci la chiave per iniziare")

        st.markdown("---")
        
        study_mode = st.radio(
            "🧠 Modalità Studio:",
            ["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards"],
            on_change=reset_conversation
        )
        
        response_style = st.select_slider(
            "📏 Lunghezza Risposta:",
            options=["Sintetico", "Bilanciato", "Esaustivo"],
            value="Bilanciato",
            on_change=reset_conversation
        )
        
        num_questions = 5
        if study_mode == "❓ Simulazione Quiz":
            num_questions = st.slider("Domande:", 5, 20, 5, on_change=reset_conversation)

        st.markdown("---")
        if st.button("🔄 Nuova Chat", use_container_width=True):
            reset_conversation()
            st.rerun()

    # Main Content
    if not api_key:
        st.info("👈 Configura la chiave API nel menu a sinistra.")
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)
        return

    uploaded_file = st.file_uploader("📂 Trascina qui le dispense (PDF)", type="pdf")

    if not uploaded_file:
        st.markdown("---")
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)

    else:
        os.environ["GOOGLE_API_KEY"] = api_key

        # Indicizzazione
        if "vectorstore" not in st.session_state:
            with st.status("⚙️ Analisi Documento...", expanded=True) as status:
                try:
                    raw_text = get_pdf_text(uploaded_file)
                    if not raw_text:
                        st.error("PDF Vuoto.")
                        return
                    
                    st.write("🧠 Indicizzazione Concetti...")
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    chunks = text_splitter.split_text(raw_text)
                    docs = [Document(page_content=t) for t in chunks]

                    embeddings = get_local_embeddings()
                    vectorstore = FAISS.from_documents(docs, embeddings)
                    st.session_state.vectorstore = vectorstore
                    
                    status.update(label="✅ Pronto! Inizia a studiare.", state="complete", expanded=False)
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore critico: {e}")
                    return

        # Setup Chain
        vectorstore = st.session_state.vectorstore
        rag_chain = build_rag_chain(vectorstore)
        
        # Recupero istruzione dinamica
        system_instr = get_system_instruction(study_mode, response_style, num_questions)

        # Chat UI
        chat_container = st.container()

        if "messages" not in st.session_state:
            st.session_state.messages = []

        with chat_container:
            for message in st.session_state.messages:
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
                # Passiamo l'istruzione specifica a runtime
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
