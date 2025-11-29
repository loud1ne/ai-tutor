import streamlit as st
import os
import warnings
import time

# Importiamo la grafica dal file styles.py
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

# Carica il CSS dal file esterno
st.markdown(styles.get_css(), unsafe_allow_html=True)

# --- 2. FUNZIONI DI LOGICA (IL CERVELLO) ---

def reset_conversation():
    """Resetta la chat quando si cambia modalità"""
    st.session_state.messages = []

@st.cache_resource(show_spinner=False)
def get_local_embeddings():
    """Carica il modello per vettorizzare il testo (CPU Locale)"""
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_pdf_text(uploaded_file):
    """Estrae il testo dal PDF"""
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

def build_rag_chain(vectorstore, model_name="gemini-2.5-pro"):
    """Costruisce la catena di intelligenza artificiale"""
    retriever = vectorstore.as_retriever()
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.3, streaming=True)
    
    # Il prompt viene iniettato dinamicamente nel main, qui prepariamo la struttura
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}"),
        ("human", "{input}"),
    ])
    
    qa_chain = create_stuff_documents_chain(llm, prompt_template)
    return create_retrieval_chain(retriever, qa_chain)

def get_system_instruction(mode, style, num_questions):
    """Crea il prompt perfetto in base alle impostazioni"""
    
    # Definizione Stile
    style_map = {
        "Sintetico": "Sii estremamente conciso. Usa elenchi puntati. Risposte brevi.",
        "Bilanciato": "Fornisci una risposta chiara, completa ma non verbosa.",
        "Esaustivo": "Spiega ogni dettaglio, includi contesto, esempi e definizioni approfondite."
    }
    style_text = style_map.get(style, "Rispondi normalmente.")

    # Definizione Ruolo
    if mode == "💬 Chat / Spiegazione":
        role = f"Sei un tutor universitario esperto. {style_text}"
    elif mode == "❓ Simulazione Quiz":
        role = (f"Sei un professore d'esame. Genera ORA {num_questions} domande difficili sull'argomento. "
                "Numera le domande. NON dare le soluzioni.")
    elif mode == "🃏 Flashcards":
        role = f"Crea materiale di studio schematico. {style_text}. Formatta: **Termine** -> _Definizione_."
    else:
        role = "Sei un assistente utile."

    return (
        f"RUOLO: {role}\n"
        "RISPONDI SOLO BASANDOTI SUL CONTESTO SEGUENTE:\n"
        "{context}"
    )

# --- 3. INTERFACCIA UTENTE (IL CORPO) ---

def main():
    # --- HEADER ---
    st.markdown('<div class="main-title">AI Study Master</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Il tuo assistente universitario personale con Gemini 2.5 Pro</div>', unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Configurazione")
        
        # Gestione API Key (Sicura)
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ API Key Cloud Attiva")
        else:
            api_key = st.text_input("🔑 Google API Key", type="password")
            if not api_key:
                st.warning("Inserisci la chiave per iniziare")

        st.markdown("---")
        
        # Menu Modalità
        study_mode = st.radio(
            "🧠 Modalità Studio:",
            ["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards"],
            on_change=reset_conversation
        )
        
        # Menu Stile
        response_style = st.select_slider(
            "📏 Lunghezza Risposta:",
            options=["Sintetico", "Bilanciato", "Esaustivo"],
            value="Bilanciato",
            on_change=reset_conversation
        )
        
        # Menu Quiz (Condizionale)
        num_questions = 5
        if study_mode == "❓ Simulazione Quiz":
            num_questions = st.slider("Domande:", 5, 20, 5, on_change=reset_conversation)

        st.markdown("---")
        if st.button("🔄 Nuova Chat", use_container_width=True):
            reset_conversation()
            st.rerun()

    # --- MAIN CONTENT AREA ---
    
    # Se manca la chiave, stop.
    if not api_key:
        st.info("👈 Configura la chiave API nel menu a sinistra.")
        # Mostra la landing page anche se manca la chiave, per bellezza
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)
        return

    # Upload File
    uploaded_file = st.file_uploader("📂 Trascina qui le dispense (PDF)", type="pdf")

    # SCENARIO A: NESSUN FILE -> MOSTRA LANDING PAGE
    if not uploaded_file:
        st.markdown("---")
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)

    # SCENARIO B: FILE CARICATO -> MOSTRA CHAT
    else:
        os.environ["GOOGLE_API_KEY"] = api_key

        # Indicizzazione (Eseguita una volta sola)
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

        # Recupero risorse
        vectorstore = st.session_state.vectorstore
        rag_chain = build_rag_chain(vectorstore)
        
        # Preparazione Prompt Dinamico
        system_instr = get_system_instruction(study_mode, response_style, num_questions)

        # --- CHAT UI ---
        chat_container = st.container()

        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Renderizza messaggi passati
        with chat_container:
            for message in st.session_state.messages:
                avatar = "🧑‍🎓" if message["role"] == "user" else "🤖"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

        # Input Box
        placeholder = "Fai una domanda..."
        if study_mode == "❓ Simulazione Quiz":
            placeholder = f"Scrivi 'VIA' per generare {num_questions} domande..."

        if user_input := st.chat_input(placeholder):
            # 1. Mostra input utente
            st.session_state.messages.append({"role": "user", "content": user_input})
            with chat_container.chat_message("user", avatar="🧑‍🎓"):
                st.markdown(user_input)

            # 2. Genera risposta (Streaming)
            with chat_container.chat_message("assistant", avatar="🤖"):
                # Passiamo l'istruzione di sistema specifica per questa chiamata
                response_stream = rag_chain.stream({
                    "input": user_input,
                    "system_instruction": system_instr
                })
                
                # Funzione generatore per estrarre solo il testo della risposta
                def stream_text():
                    for chunk in response_stream:
                        if 'answer' in chunk:
                            yield chunk['answer']
                
                full_response = st.write_stream(stream_text)
            
            # 3. Salva storia
            st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == '__main__':
    main()
