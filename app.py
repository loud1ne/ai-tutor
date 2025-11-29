import streamlit as st
import os
import warnings

# --- 1. SETUP & CONFIGURAZIONE ---
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="AI Study Master Pro", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZZATO PER UI MIGLIORE ---
st.markdown("""
<style>
    /* Nasconde menu hamburger e footer standard */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Stile per il titolo */
    .big-font {
        font-size:30px !important;
        font-weight: bold;
        color: #4A90E2;
    }
    
    /* Bordo colorato per la chat dell'assistente */
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- IMPORT LIBRERIE ---
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document

# --- TITOLO PRINCIPALE ---
col1, col2 = st.columns([1, 5])
with col1:
    # Icona generica educativa
    st.markdown("## 🎓")
with col2:
    st.title("AI Study Master")
    st.caption("Motore: **Gemini 2.5 Pro** | *Streaming Mode Active* ⚡")

with st.sidebar:
    st.header("⚙️ Configurazione")
    

    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ Chiave API caricata dal Cloud sicura.")
    else:
        api_key = st.text_input("Inserisci Google API Key", type="password")
        if not api_key:
            st.warning("⚠️ Inserisci la chiave per iniziare")

    st.subheader("🎯 Obiettivo Studio")
    
    study_mode = st.radio(
        "Modalità:",
        ["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards & Schemi"],
        captions=["Tutor personale", "Test pre-esame", "Memorizzazione rapida"]
    )
    
    st.markdown("---")
    
    response_style = st.select_slider(
        "Livello Dettaglio:",
        options=["Sintetico", "Bilanciato", "Esaustivo"],
        value="Bilanciato"
    )
    
    num_questions = 5
    if study_mode == "❓ Simulazione Quiz":
        st.info("⚡ Opzioni Quiz")
        num_questions = st.slider("N. Domande:", 5, 20, 5)

    st.markdown("---")
    if st.button("🗑️ Cancella Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- FUNZIONI CORE ---

# MODIFICA QUI: show_spinner=False nasconde la scritta "Running get_local_embeddings..."
@st.cache_resource(show_spinner=False)
def get_local_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_pdf_text(pdf_docs):
    text = ""
    try:
        pdf_reader = PdfReader(pdf_docs)
        for page in pdf_reader.pages:
            t = page.extract_text()
            if t: text += t
    except Exception as e:
        st.error(f"Errore lettura PDF: {e}")
    return text

# --- GENERATORE DI STREAMING ---
def stream_response(chain, input_text):
    for chunk in chain.stream({"input": input_text}):
        if 'answer' in chunk:
            yield chunk['answer']

# --- MAIN ---
def main():
    uploaded_file = st.file_uploader("📂 Carica le tue dispense (PDF)", type="pdf")

    if uploaded_file and api_key:
        os.environ["GOOGLE_API_KEY"] = api_key

        if "vectorstore" not in st.session_state:
            # Status Box elegante
            with st.status("🚀 Indicizzazione documenti in corso...", expanded=True) as status:
                try:
                    # 1. Lettura
                    # st.write("📖 Lettura PDF...") # Decommenta se vuoi vedere i passaggi
                    raw_text = get_pdf_text(uploaded_file)
                    if not raw_text:
                        st.error("PDF Vuoto.")
                        return

                    # 2. Chunking
                    # st.write("✂️ Suddivisione concetti...")
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    chunks = text_splitter.split_text(raw_text)
                    docs = [Document(page_content=t) for t in chunks]

                    # 3. Embeddings (Senza scritta fastidiosa ora)
                    # st.write("🧠 Creazione memoria locale...")
                    embeddings = get_local_embeddings()
                    vectorstore = FAISS.from_documents(docs, embeddings)
                    
                    st.session_state.vectorstore = vectorstore
                    status.update(label="✅ Documenti pronti! Puoi chattare.", state="complete", expanded=False)
                
                except Exception as e:
                    st.error(f"Errore critico: {e}")
                    return
        
        vectorstore = st.session_state.vectorstore
        retriever = vectorstore.as_retriever()

        # 4. LLM
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.3, streaming=True)
        
        # 5. Prompt Logic
        if response_style == "Sintetico":
            style_instr = "Sii telegrafico. Usa elenchi puntati. Massimo rendimento, minimo testo."
        elif response_style == "Esaustivo":
            style_instr = "Spiega tutto nei minimi dettagli. Includi contesto, esempi e definizioni complete."
        else:
            style_instr = "Risposta chiara ed equilibrata."

        if study_mode == "💬 Chat / Spiegazione":
            role_instr = f"Sei un tutor eccellente. {style_instr}"
        elif study_mode == "❓ Simulazione Quiz":
            role_instr = (f"Sei un professore d'esame. Genera SUBITO {num_questions} domande difficili. "
                          "NON dare soluzioni. Aspetta la risposta studente.")
        elif study_mode == "🃏 Flashcards & Schemi":
            role_instr = f"Crea schemi di studio. {style_instr}. Formatta: CONCETTO -> DEFINIZIONE."

        system_prompt = (
            f"RUOLO: {role_instr}\n"
            "FONTE: Rispondi SOLO basandoti sul contesto fornito.\n"
            "CONTESTO:\n{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        qa_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, qa_chain)

        # --- INTERFACCIA CHAT ---
        message_container = st.container()

        if "messages" not in st.session_state:
            st.session_state.messages = []

        with message_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        placeholder = "Chiedi qualcosa..."
        if study_mode == "❓ Simulazione Quiz":
            placeholder = f"Scrivi 'VIA' per generare {num_questions} domande..."

        if user_input := st.chat_input(placeholder):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with message_container.chat_message("user"):
                st.markdown(user_input)

            with message_container.chat_message("assistant"):
                response_stream = stream_response(rag_chain, user_input)
                full_response = st.write_stream(response_stream)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})

    elif not uploaded_file:
        st.info("👈 Carica un PDF nella barra laterale per attivare il Tutor.")

if __name__ == '__main__':

    main()
