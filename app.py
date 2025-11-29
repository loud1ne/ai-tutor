import streamlit as st
import os
import warnings
import time
import sqlite3
import hashlib
import streamlit.components.v1 as components

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
st.markdown(styles.get_css(), unsafe_allow_html=True)

# --- 2. GESTIONE DATABASE E AUTH (NUOVO) ---

def init_db():
    """Inizializza il database SQLite locale"""
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    # Tabella Utenti
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    # Tabella Messaggi
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT, role TEXT, content TEXT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                  (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
              (username, hash_password(password)))
    return c.fetchone() is not None

def save_message_to_db(username, role, content):
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (username, role, content) VALUES (?, ?, ?)", 
              (username, role, content))
    conn.commit()
    conn.close()

def load_chat_history(username):
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM chat_history WHERE username = ? ORDER BY timestamp ASC", (username,))
    rows = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def clear_user_history(username):
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE username = ?", (username,))
    conn.commit()
    conn.close()

# --- 3. RENDERER GRAFICI (NUOVO) ---

def mermaid(code: str):
    """Renderizza diagrammi Mermaid.js usando un component HTML/JS"""
    html_code = f"""
    <div class="mermaid">
    {code}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    """
    components.html(html_code, height=500, scrolling=True)

# --- 4. LOGICA RAG & PDF ---

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
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.3) # Streaming disattivato per Mermaid handling
    
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

    # Logica specifica per le modalità
    if mode == "🗺️ Mappa Concettuale":
        role = ("Sei un esperto di visualizzazione dati. "
                "Genera il codice per un diagramma Mermaid.js (graph TD o mindmap) che riassume i concetti. "
                "IMPORTANTE: Restituisci SOLO il blocco di codice iniziando con ```mermaid e finendo con ```. "
                "Non aggiungere altro testo.")
    elif mode == "💬 Chat / Spiegazione":
        role = f"Sei un tutor universitario esperto. {style_text}"
    elif mode == "❓ Simulazione Quiz":
        role = (f"Sei un professore d'esame. Genera ORA {num_questions} domande difficili sull'argomento. "
                "Numera le domande. NON dare le soluzioni.")
    elif mode == "🃏 Flashcards":
        role = f"Crea materiale di studio schematico. {style_text}. Formatta: **Termine** -> _Definizione_."
    else:
        role = "Sei un assistente utile."

    return f"RUOLO: {role}"

# --- 5. INTERFACCIA MAIN ---

def main():
    init_db() # Assicuriamoci che il DB esista
    
    # Titolo
    st.markdown('<div class="main-title">AI Study Master</div>', unsafe_allow_html=True)

    # --- GESTIONE LOGIN / REGISTRAZIONE ---
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id is None:
        tab1, tab2 = st.tabs(["🔑 Accedi", "📝 Registrati"])
        
        with tab1:
            st.markdown('<div class="sub-title">Bentornato! Accedi per i tuoi appunti.</div>', unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Accedi")
                if submit:
                    if login_user(username, password):
                        st.session_state.user_id = username
                        st.success(f"Benvenuto {username}!")
                        st.rerun()
                    else:
                        st.error("Username o Password non validi.")

        with tab2:
            st.markdown('<div class="sub-title">Crea il tuo profilo studente.</div>', unsafe_allow_html=True)
            with st.form("register_form"):
                new_user = st.text_input("Nuovo Username")
                new_pass = st.text_input("Nuova Password", type="password")
                submit_reg = st.form_submit_button("Registrati")
                if submit_reg:
                    if register_user(new_user, new_pass):
                        st.success("Account creato! Ora puoi accedere.")
                    else:
                        st.error("Username già esistente.")
        
        st.markdown("---")
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)
        return  # Interrompe l'esecuzione se non loggato

    # --- APP DOPO IL LOGIN ---
    
    # Sidebar
    with st.sidebar:
        st.write(f"👤 Utente: **{st.session_state.user_id}**")
        if st.button("Logout"):
            st.session_state.user_id = None
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        
        st.header("⚙️ Configurazione")
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ API Key Cloud Attiva")
        else:
            api_key = st.text_input("🔑 Google API Key", type="password")
            if not api_key: st.warning("Inserisci la chiave")

        # Inizializza stati
        if "study_mode" not in st.session_state: st.session_state.study_mode = "💬 Chat / Spiegazione"
        if "response_style" not in st.session_state: st.session_state.response_style = "Bilanciato"
        if "num_questions" not in st.session_state: st.session_state.num_questions = 5

        with st.form(key="settings_form"):
            st.subheader("Studio")
            new_study_mode = st.radio(
                "🧠 Modalità Studio:",
                ["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards", "🗺️ Mappa Concettuale"], # Nuova modalità
                index=["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards", "🗺️ Mappa Concettuale"].index(st.session_state.study_mode)
            )
            new_response_style = st.select_slider("📏 Lunghezza:", options=["Sintetico", "Bilanciato", "Esaustivo"], value=st.session_state.response_style)
            new_num_questions = st.slider("Domande Quiz:", 5, 20, st.session_state.num_questions)
            
            if st.form_submit_button("✅ Applica Modifiche"):
                st.session_state.study_mode = new_study_mode
                st.session_state.response_style = new_response_style
                st.session_state.num_questions = new_num_questions
                st.rerun()

        if st.button("🗑️ Cancella Storia Utente"):
            clear_user_history(st.session_state.user_id)
            st.session_state.messages = []
            st.rerun()

    if not api_key:
        st.info("👈 Configura la chiave API.")
        return

    # PDF Uploader
    uploaded_file = st.file_uploader("📂 Trascina qui le dispense (PDF)", type="pdf")
    
    if uploaded_file:
        os.environ["GOOGLE_API_KEY"] = api_key
        
        # Indicizzazione (Cache semplice su session state per ora)
        if "vectorstore" not in st.session_state:
            with st.status("⚙️ Analisi Documento...") as status:
                try:
                    raw_text = get_pdf_text(uploaded_file)
                    if raw_text:
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                        chunks = text_splitter.split_text(raw_text)
                        docs = [Document(page_content=t) for t in chunks]
                        embeddings = get_local_embeddings()
                        st.session_state.vectorstore = FAISS.from_documents(docs, embeddings)
                        status.update(label="✅ Pronto!", state="complete")
                    else: st.error("PDF Vuoto")
                except Exception as e: st.error(f"Errore: {e}")

        if "vectorstore" in st.session_state:
            rag_chain = build_rag_chain(st.session_state.vectorstore)
            system_instr = get_system_instruction(st.session_state.study_mode, st.session_state.response_style, st.session_state.num_questions)

            # CARICAMENTO CRONOLOGIA DAL DB
            db_history = load_chat_history(st.session_state.user_id)
            st.session_state.messages = db_history

            chat_container = st.container()
            with chat_container:
                for message in st.session_state.messages:
                    avatar = "🧑‍🎓" if message["role"] == "user" else "🤖"
                    with st.chat_message(message["role"], avatar=avatar):
                        # Se il messaggio contiene codice mermaid, lo renderizziamo
                        if "```mermaid" in message["content"]:
                            clean_code = message["content"].replace("```mermaid", "").replace("```", "")
                            mermaid(clean_code)
                        else:
                            st.markdown(message["content"])

            placeholder = "Fai una domanda o chiedi una mappa..."
            if user_input := st.chat_input(placeholder):
                # 1. Salva User Input nel DB
                save_message_to_db(st.session_state.user_id, "user", user_input)
                
                # Aggiorna UI subito
                st.session_state.messages.append({"role": "user", "content": user_input})
                with chat_container.chat_message("user", avatar="🧑‍🎓"):
                    st.markdown(user_input)

                # 2. Genera Risposta AI
                with chat_container.chat_message("assistant", avatar="🤖"):
                    with st.spinner("Sto pensando..."):
                        response = rag_chain.invoke({
                            "input": user_input,
                            "system_instruction": system_instr
                        })
                        answer = response['answer']
                        
                        # Controllo se è un grafico Mermaid
                        if "```mermaid" in answer:
                            clean_code = answer.replace("```mermaid", "").replace("```", "")
                            mermaid(clean_code)
                            # Salviamo comunque il testo raw nel DB
                        else:
                            st.markdown(answer)

                # 3. Salva AI Response nel DB
                save_message_to_db(st.session_state.user_id, "assistant", answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

    else:
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)

if __name__ == '__main__':
    main()
