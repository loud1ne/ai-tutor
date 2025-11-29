import streamlit as st
import os
import warnings
import time
import sqlite3
import hashlib

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
from langchain_core.messages import SystemMessage, HumanMessage

# --- 1. SETUP INIZIALE ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="AI Study Station", page_icon="🧠", layout="wide")
st.markdown(styles.get_css(), unsafe_allow_html=True)

# Definiamo il modello qui per facilità di modifica (Usa 1.5-pro o flash per stabilità)
MODEL_NAME = "gemini-1.5-flash" 

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

# --- 3. LOGICA RAG & PDF ---

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
    """Chain per quando c'è un PDF"""
    retriever = vectorstore.as_retriever()
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.3)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "{system_instruction}\n\nUsa il seguente contesto PDF per rispondere, ma se la domanda è generica, rispondi con la tua conoscenza:\n{context}"),
        ("human", "{input}"),
    ])
    
    qa_chain = create_stuff_documents_chain(llm, prompt_template)
    return create_retrieval_chain(retriever, qa_chain)

def get_general_response(user_input, system_instruction):
    """Chiamata diretta all'LLM quando NON c'è un PDF"""
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.4)
    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=user_input)
    ]
    response = llm.invoke(messages)
    return response.content

def get_system_instruction(mode, style, num_questions):
    style_map = {
        "Sintetico": "Sii conciso e diretto.",
        "Bilanciato": "Risposta chiara, completa ma non prolissa.",
        "Esaustivo": "Approfondisci ogni dettaglio con esempi."
    }
    style_text = style_map.get(style, "Rispondi normalmente.")

    if mode == "💬 Tutor Generale":
        role = f"Sei un assistente di studio universitario versatile. Puoi rispondere a domande di cultura generale O analizzare documenti se forniti. {style_text}"
    elif mode == "❓ Generatore Quiz":
        role = (f"Sei un professore severo. Genera {num_questions} domande sull'argomento richiesto (o sul PDF se presente). "
                "Non dare le soluzioni subito.")
    elif mode == "🃏 Flashcards":
        role = f"Crea schemi di studio. {style_text}. Formatta rigorosamente: **Concetto** -> _Definizione_."
    else:
        role = "Sei un assistente utile."

    return f"RUOLO: {role}"

# --- 4. FUNZIONI TIMER (POMODORO) ---
def format_time(seconds):
    mins, secs = divmod(seconds, 60)
    return f"{mins:02d}:{secs:02d}"

# --- 5. INTERFACCIA MAIN ---

def main():
    init_db()
    
    st.markdown('<div class="main-title">AI Study Station</div>', unsafe_allow_html=True)

    # --- LOGIN ---
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id is None:
        tab1, tab2 = st.tabs(["🔑 Accedi", "📝 Registrati"])
        
        with tab1:
            st.markdown('<div class="sub-title">Il tuo spazio di studio intelligente.</div>', unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Accedi"):
                    if login_user(username, password):
                        st.session_state.user_id = username
                        st.rerun()
                    else:
                        st.error("Credenziali errate.")

        with tab2:
            st.markdown('<div class="sub-title">Inizia ora il tuo percorso.</div>', unsafe_allow_html=True)
            with st.form("register_form"):
                new_user = st.text_input("Nuovo Username")
                new_pass = st.text_input("Nuova Password", type="password")
                if st.form_submit_button("Registrati"):
                    if register_user(new_user, new_pass):
                        st.success("Registrato! Accedi nel tab a fianco.")
                    else:
                        st.error("Username occupato.")
        
        st.markdown("---")
        st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)
        return

    # --- APP LOGGATA ---
    
    # 1. SIDEBAR: Configurazione & Strumenti
    with st.sidebar:
        st.write(f"👋 Ciao, **{st.session_state.user_id}**")
        
        # --- POMODORO TIMER (NUOVO) ---
        st.markdown("### ⏱️ Focus Timer")
        if "timer_duration" not in st.session_state: st.session_state.timer_duration = 25 * 60
        if "timer_running" not in st.session_state: st.session_state.timer_running = False
        if "end_time" not in st.session_state: st.session_state.end_time = 0

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            if st.button("▶️ Start 25'"):
                st.session_state.timer_running = True
                st.session_state.end_time = time.time() + (25 * 60)
        with col_t2:
            if st.button("⏹️ Reset"):
                st.session_state.timer_running = False

        if st.session_state.timer_running:
            remaining = st.session_state.end_time - time.time()
            if remaining > 0:
                st.markdown(f"<h2 style='text-align: center; color: #4A90E2;'>{format_time(int(remaining))}</h2>", unsafe_allow_html=True)
                time.sleep(1) # Refresh semplice
                st.rerun()
            else:
                st.session_state.timer_running = False
                st.success("🍅 Pomodoro Completato! Prenditi una pausa.")
        else:
             st.markdown("<h2 style='text-align: center; color: gray;'>25:00</h2>", unsafe_allow_html=True)

        st.markdown("---")
        
        # API KEY
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ AI Attiva")
        else:
            api_key = st.text_input("🔑 Google API Key", type="password")
            if not api_key: st.warning("Inserisci Key")

        # SETTAGGI STUDIO
        if "study_mode" not in st.session_state: st.session_state.study_mode = "💬 Tutor Generale"
        if "response_style" not in st.session_state: st.session_state.response_style = "Bilanciato"

        with st.form(key="settings_form"):
            st.subheader("🛠️ Modalità")
            new_mode = st.radio("Scegli:", ["💬 Tutor Generale", "❓ Generatore Quiz", "🃏 Flashcards"], 
                                index=["💬 Tutor Generale", "❓ Generatore Quiz", "🃏 Flashcards"].index(st.session_state.study_mode))
            new_style = st.select_slider("Stile:", ["Sintetico", "Bilanciato", "Esaustivo"], value=st.session_state.response_style)
            
            if st.form_submit_button("Applica"):
                st.session_state.study_mode = new_mode
                st.session_state.response_style = new_style
                st.rerun()

        # LOGOUT E PULIZIA
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.user_id = None
            st.session_state.messages = []
            if "vectorstore" in st.session_state: del st.session_state.vectorstore
            st.rerun()
        if st.button("🗑️ Cancella Chat"):
            clear_user_history(st.session_state.user_id)
            st.session_state.messages = []
            st.rerun()

    if not api_key:
        st.info("👈 Per iniziare, inserisci la tua API Key di Google.")
        return
    
    os.environ["GOOGLE_API_KEY"] = api_key

    # 2. AREA CENTRALE: Gestione PDF (Opzionale)
    
    pdf_active = False
    
    # Se abbiamo già un vectorstore, mostriamo il file attivo
    if "vectorstore" in st.session_state and st.session_state.vectorstore is not None:
        pdf_active = True
        with st.expander("📂 Gestione Documenti (File Attivo)", expanded=False):
            c1, c2 = st.columns([3, 1])
            c1.success(f"File in uso: **{st.session_state.get('current_filename', 'Doc')}**")
            if c2.button("Chiudi PDF"):
                del st.session_state.vectorstore
                st.rerun()
    else:
        # Se non c'è file, mostriamo l'uploader in un expander per non disturbare la chat generale
        with st.expander("📂 Carica Dispense (Opzionale)", expanded=False):
            uploaded_file = st.file_uploader("Carica un PDF per chattare col documento", type="pdf")
            if uploaded_file:
                with st.status("Analisi in corso...") as status:
                    raw_text = get_pdf_text(uploaded_file)
                    if raw_text:
                        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                        chunks = text_splitter.split_text(raw_text)
                        docs = [Document(page_content=t) for t in chunks]
                        embeddings = get_local_embeddings()
                        st.session_state.vectorstore = FAISS.from_documents(docs, embeddings)
                        st.session_state.current_filename = uploaded_file.name
                        status.update(label="PDF Pronto!", state="complete")
                        time.sleep(0.5)
                        st.rerun()

    # 3. CHAT INTERFACE
    
    # Carichiamo la storia
    db_history = load_chat_history(st.session_state.user_id)
    st.session_state.messages = db_history

    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.info("👋 Ciao! Sono il tuo Tutor AI. Puoi farmi domande generali, oppure caricare un PDF dal menu 'Gestione Documenti' per analizzarlo.")
        
        for message in st.session_state.messages:
            avatar = "🧑‍🎓" if message["role"] == "user" else "🧠"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

    # Input Bar
    placeholder = "Chiedi qualsiasi cosa..." if not pdf_active else "Fai una domanda sul PDF o generale..."
    if user_input := st.chat_input(placeholder):
        # Salva e mostra user input
        save_message_to_db(st.session_state.user_id, "user", user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        with chat_container.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(user_input)

        # Genera risposta
        with chat_container.chat_message("assistant", avatar="🧠"):
            with st.spinner("Elaborazione..."):
                system_instr = get_system_instruction(st.session_state.study_mode, st.session_state.response_style, 0) # num_questions default 0 here
                
                try:
                    if pdf_active:
                        # Modalità RAG (con PDF)
                        rag_chain = build_rag_chain(st.session_state.vectorstore)
                        response = rag_chain.invoke({
                            "input": user_input,
                            "system_instruction": system_instr
                        })
                        answer = response['answer']
                    else:
                        # Modalità Chat Generale (senza PDF)
                        answer = get_general_response(user_input, system_instr)
                    
                    st.markdown(answer)
                    save_message_to_db(st.session_state.user_id, "assistant", answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                except Exception as e:
                    st.error(f"Errore AI: {e}")

if __name__ == '__main__':
    main()
