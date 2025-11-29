import streamlit as st
import os
import warnings
import time
import sqlite3
import hashlib
import re
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

# --- 2. GESTIONE DATABASE E AUTH ---

def init_db():
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    return c.fetchone() is not None

def save_message_to_db(username, role, content):
    conn = sqlite3.connect('study_master.db')
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (username, role, content) VALUES (?, ?, ?)", (username, role, content))
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

# --- 3. RENDERER GRAFICI (MIGLIORATO) ---

def mermaid(code: str):
    """Renderizza diagrammi Mermaid.js"""
    html_code = f"""
    <div class="mermaid">
    {code}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    """
    components.html(html_code, height=500, scrolling=True)

def extract_mermaid_code(text):
    """Estrae SOLO il codice Mermaid dal testo usando Regex"""
    # Cerca il pattern ```mermaid ... ``` ignorando maiuscole/minuscole e spazi extra
    pattern = r"```mermaid\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    return None

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
    # Usa gemini-1.5-flash o gemini-1.5-pro (NON 2.5)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    
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

    if mode == "🗺️ Mappa Concettuale":
        # Prompt rafforzato per evitare errori di sintassi
        role = ("Sei un esperto di visualizzazione dati. "
                "Genera il codice per un diagramma Mermaid.js (preferisci 'graph TD' per la compatibilità) che riassume i concetti chiave. "
                "IMPORTANTE: Restituisci il codice all'interno di un blocco ```mermaid. "
                "Non aggiungere spiegazioni esterne.")
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
    init_db()
    
    st.markdown('<div class="main-title">AI Study Master</div>', unsafe_allow_html=True)

    # --- LOGIN ---
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id is None:
        tab1, tab2 = st.tabs(["🔑 Accedi", "📝 Registrati"])
        
        with tab1:
            st.markdown('<div class="sub-title">Bentornato! Accedi per i tuoi appunti.</div>', unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Accedi"):
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
                if st.form_submit_button("Registrati"):
                    if register_user(new_user, new_pass):
                        st.success("Account creato! Ora puoi accedere.")
                    else:
                        st.error("Username già esistente.")
        
        st.markdown("---")
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)
        return

    # --- APP DOPO LOGIN ---
    with st.sidebar:
        st.write(f"👤 Utente: **{st.session_state.user_id}**")
        if st.button("Logout"):
            st.session_state.user_id = None
            st.session_state.messages = []
            if "vectorstore" in st.session_state: del st.session_state.vectorstore
            st.rerun()
        
        st.markdown("---")
        st.header("⚙️ Configurazione")
        
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ API Key Cloud Attiva")
        else:
            api_key = st.text_input("🔑 Google API Key", type="password")

        if "study_mode" not in st.session_state: st.session_state.study_mode = "💬 Chat / Spiegazione"
        if "response_style" not in st.session_state: st.session_state.response_style = "Bilanciato"
        if "num_questions" not in st.session_state: st.session_state.num_questions = 5

        with st.form(key="settings_form"):
            st.subheader("Studio")
            new_study_mode = st.radio(
                "🧠 Modalità Studio:",
                ["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards", "🗺️ Mappa Concettuale"],
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

    # --- LOGICA FILE E CHAT ---
    file_processed = False
    if "vectorstore" in st.session_state and st.session_state.vectorstore is not None:
        file_processed = True
        col1, col2 = st.columns([3, 1])
        with col1:
            current_file = st.session_state.get("current_filename", "Dispense Caricate")
            st.success(f"📂 File attivo: **{current_file}**")
        with col2:
            if st.button("❌ Rimuovi File"):
                del st.session_state.vectorstore
                if "current_filename" in st.session_state: del st.session_state.current_filename
                st.rerun()
    else:
        uploaded_file = st.file_uploader("📂 Trascina qui le dispense (PDF)", type="pdf")
        if uploaded_file:
            os.environ["GOOGLE_API_KEY"] = api_key
            with st.status("⚙️ Analisi Documento...") as status:
                try:
                    raw_text = get_pdf_text(uploaded_file)
                    if raw_text:
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                        chunks = text_splitter.split_text(raw_text)
                        docs = [Document(page_content=t) for t in chunks]
                        embeddings = get_local_embeddings()
                        st.session_state.vectorstore = FAISS.from_documents(docs, embeddings)
                        st.session_state.current_filename = uploaded_file.name
                        status.update(label="✅ Pronto!", state="complete")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("PDF Vuoto")
                except Exception as e: st.error(f"Errore: {e}")

    # --- CHAT UI ---
    if file_processed:
        rag_chain = build_rag_chain(st.session_state.vectorstore)
        system_instr = get_system_instruction(st.session_state.study_mode, st.session_state.response_style, st.session_state.num_questions)

        db_history = load_chat_history(st.session_state.user_id)
        st.session_state.messages = db_history

        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                avatar = "🧑‍🎓" if message["role"] == "user" else "🤖"
                with st.chat_message(message["role"], avatar=avatar):
                    # Controlla se è codice mermaid
                    code_found = extract_mermaid_code(message["content"])
                    if code_found:
                        mermaid(code_found)
                    else:
                        st.markdown(message["content"])

        placeholder = "Fai una domanda o chiedi una mappa..."
        if user_input := st.chat_input(placeholder):
            save_message_to_db(st.session_state.user_id, "user", user_input)
            st.session_state.messages.append({"role": "user", "content": user_input})
            with chat_container.chat_message("user", avatar="🧑‍🎓"):
                st.markdown(user_input)

            with chat_container.chat_message("assistant", avatar="🤖"):
                with st.spinner("Sto pensando..."):
                    try:
                        response = rag_chain.invoke({
                            "input": user_input,
                            "system_instruction": system_instr
                        })
                        answer = response['answer']
                        
                        # LOGICA MIGLIORATA PER VISUALIZZAZIONE
                        mermaid_code = extract_mermaid_code(answer)
                        if mermaid_code:
                            mermaid(mermaid_code)
                        else:
                            st.markdown(answer)
                            
                        save_message_to_db(st.session_state.user_id, "assistant", answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    except Exception as e:
                        st.error(f"Errore durante la generazione: {e}")

    elif not file_processed and api_key:
        st.info("👆 Carica un PDF per iniziare.")
    else:
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)

if __name__ == '__main__':
    main()
