import streamlit as st
import os
import warnings
import time

# --- 1. SETUP & CONFIGURAZIONE ---
warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="AI Study Master", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CSS AVANZATO (DESIGN SYSTEM) ---
st.markdown("""
<style>
    /* IMPORT FONT MODERNO (Poppins) */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }

    /* NASCONDI ELEMENTI STANDARD */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* TITOLO GRADIENTE */
    .title-text {
        font-weight: 700;
        font-size: 50px !important;
        background: -webkit-linear-gradient(45deg, #4A90E2, #9013FE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: -10px;
    }
    
    /* CARD DI BENVENUTO */
    .feature-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.2s;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
    }
    
    /* CHAT BUBBLES STILE MESSENGER */
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #F0F4F8; /* User - Grigio/Blu */
        border-left: 5px solid #4A90E2;
    }
    .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #FFFFFF; /* Bot - Bianco */
        border: 1px solid #E0E0E0;
    }

    /* FILE UPLOADER PIÙ BELLO */
    .stFileUploader section {
        background-color: #ffffff;
        border: 2px dashed #4A90E2;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- IMPORT ---
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document

# --- FUNZIONI DI UTILITÀ ---
def reset_conversation():
    st.session_state.messages = []

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
        st.error(f"Errore: {e}")
    return text

def stream_response(chain, input_text):
    for chunk in chain.stream({"input": input_text}):
        if 'answer' in chunk:
            yield chunk['answer']

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712009.png", width=60)
    st.markdown("### Control Panel")
    
    # API KEY LOGIC (Sicura per il Cloud)
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key Connessa")
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

# --- MAIN PAGE ---
def main():
    # Header Personalizzato
    st.markdown('<p class="title-text">AI Study Master</p>', unsafe_allow_html=True)
    st.markdown("**Il tuo assistente universitario alimentato da Gemini 2.5 Pro**")
    st.write("") # Spacer

    # Se non c'è API key, fermati qui
    if not api_key:
        st.info("👈 Per favore, inserisci la tua Google API Key nella barra laterale.")
        return

    # File Uploader
    uploaded_file = st.file_uploader("📂 Trascina qui le tue dispense (PDF)", type="pdf")

    # --- LANDING PAGE (VISIBILE SE NON C'È FILE) ---
    if not uploaded_file:
        st.markdown("---")
        st.subheader("🚀 Cosa posso fare per te?")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <h3>📚 Riassunti</h3>
                <p>Carica libri interi. Chiedimi di riassumere capitoli o concetti complessi in secondi.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="feature-card">
                <h3>❓ Quiz Esame</h3>
                <p>Ti interrogo io. Genero domande d'esame realistiche per testare la tua preparazione.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class="feature-card">
                <h3>🃏 Flashcards</h3>
                <p>Creo tabelle e schemi pronti per memorizzare definizioni e date velocemente.</p>
            </div>
            """, unsafe_allow_html=True)

    # --- LOGICA CHAT (VISIBILE SE C'È FILE) ---
    else:
        os.environ["GOOGLE_API_KEY"] = api_key

        if "vectorstore" not in st.session_state:
            with st.status("⚙️ Configurazione Tutor in corso...", expanded=True) as status:
                try:
                    st.write("📖 Lettura documento...")
                    raw_text = get_pdf_text(uploaded_file)
                    if not raw_text:
                        st.error("PDF Vuoto.")
                        return

                    st.write("🧠 Indicizzazione concetti...")
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    chunks = text_splitter.split_text(raw_text)
                    docs = [Document(page_content=t) for t in chunks]

                    embeddings = get_local_embeddings()
                    vectorstore = FAISS.from_documents(docs, embeddings)
                    st.session_state.vectorstore = vectorstore
                    
                    status.update(label="✅ Tutto pronto! Inizia a chiedere.", state="complete", expanded=False)
                    time.sleep(1) 
                    st.rerun() # Ricarica per pulire lo schermo
                except Exception as e:
                    st.error(f"Errore critico: {e}")
                    return
        
        vectorstore = st.session_state.vectorstore
        retriever = vectorstore.as_retriever()

        # LLM
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.3, streaming=True)
        
        # Logica Prompt Avanzata
        style_instr = {
            "Sintetico": "Sii estremamente conciso. Usa elenchi puntati.",
            "Bilanciato": "Rispondi in modo chiaro e completo.",
            "Esaustivo": "Approfondisci ogni dettaglio come un libro di testo."
        }[response_style]

        if study_mode == "💬 Chat / Spiegazione":
            role = f"Sei un tutor universitario paziente ed esperto. {style_instr}"
        elif study_mode == "❓ Simulazione Quiz":
            role = (f"Sei un professore d'esame. Genera ORA {num_questions} domande difficili sull'argomento richiesto. "
                    "Numera le domande. NON dare soluzioni subito.")
        elif study_mode == "🃏 Flashcards":
            role = f"Crea materiale di studio schematico. {style_instr}. Formatta: **Concetto** -> _Definizione_."

        system_prompt = (
            f"RUOLO: {role}\n"
            "RISPONDI SOLO BASANDOTI SUL CONTESTO SEGUENTE:\n"
            "{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        qa_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, qa_chain)

        # Chat UI
        chat_container = st.container()

        if "messages" not in st.session_state:
            st.session_state.messages = []

        with chat_container:
            for message in st.session_state.messages:
                avatar = "🧑‍🎓" if message["role"] == "user" else "🤖"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

        # Input Area
        placeholder = "Fai una domanda sull'esame..."
        if study_mode == "❓ Simulazione Quiz":
            placeholder = f"Scrivi 'VIA' per generare {num_questions} domande..."

        if user_input := st.chat_input(placeholder):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with chat_container.chat_message("user", avatar="🧑‍🎓"):
                st.markdown(user_input)

            with chat_container.chat_message("assistant", avatar="🤖"):
                response_stream = stream_response(rag_chain, user_input)
                full_response = st.write_stream(response_stream)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == '__main__':
    main()
