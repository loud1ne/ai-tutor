import streamlit as st
import os
import warnings
import time
import sqlite3
import hashlib
from datetime import datetime

# --- IMPORT LOGICA AI ---
try:
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
except ImportError as e:
    st.error(f"⚠️ Errore critico librerie: {e}. Controlla requirements.txt.")
    st.stop()

# --- IMPORT GRAFICA (Gestione Errore) ---
try:
    import styles
    HAS_STYLES = True
except ImportError:
    HAS_STYLES = False

# --- SETUP FIREBASE (OPZIONALE) ---
try:
    from google.oauth2 import service_account
    from google.cloud import firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# --- 1. SETUP INIZIALE ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="AI Study Master", page_icon="🎓", layout="wide")

if HAS_STYLES:
    st.markdown(styles.get_css(), unsafe_allow_html=True)

# --- 2. GESTIONE DATABASE IBRIDO (SQLITE + FIRESTORE) ---

def get_db_mode():
    """Rileva se usare Firebase (Cloud) o SQLite (Locale)"""
    if FIREBASE_AVAILABLE and "FIREBASE_CONFIG" in st.secrets:
        return "firestore"
    return "sqlite"

def get_firestore_client():
    key_dict = dict(st.secrets["FIREBASE_CONFIG"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return firestore.Client(credentials=creds)

def init_db():
    mode = get_db_mode()
    if mode == "sqlite":
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
    mode = get_db_mode()
    pwd_hash = hash_password(password)
    
    if mode == "firestore":
        db = get_firestore_client()
        doc_ref = db.collection('users').document(username)
        if doc_ref.get().exists:
            return False
        doc_ref.set({'password': pwd_hash})
        return True
    else:
        conn = sqlite3.connect('study_master.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, pwd_hash))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

def login_user(username, password):
    mode = get_db_mode()
    pwd_hash = hash_password(password)
    
    if mode == "firestore":
        db = get_firestore_client()
        doc = db.collection('users').document(username).get()
        if doc.exists:
            return doc.to_dict().get('password') == pwd_hash
        return False
    else:
        conn = sqlite3.connect('study_master.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, pwd_hash))
        return c.fetchone() is not None

def save_message_to_db(username, role, content):
    mode = get_db_mode()
    
    if mode == "firestore":
        db = get_firestore_client()
        db.collection('chat_history').add({
            'username': username,
            'role': role,
            'content': content,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    else:
        conn = sqlite3.connect('study_master.db')
        c = conn.cursor()
        c.execute("INSERT INTO chat_history (username, role, content) VALUES (?, ?, ?)", (username, role, content))
        conn.commit()
        conn.close()

def load_chat_history(username):
    mode = get_db_mode()
    messages = []
    
    if mode == "firestore":
        db = get_firestore_client()
        docs = db.collection('chat_history').where('username', '==', username).stream()
        temp_msgs = []
        for doc in docs:
            d = doc.to_dict()
            if d.get('timestamp'):
                temp_msgs.append(d)
        
        # Ordina per data
        temp_msgs.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.now())
        
        for msg in temp_msgs:
            messages.append({"role": msg['role'], "content": msg['content']})
    else:
        conn = sqlite3.connect('study_master.db')
        c = conn.cursor()
        c.execute("SELECT role, content FROM chat_history WHERE username = ? ORDER BY timestamp ASC", (username,))
        rows = c.fetchall()
        conn.close()
        messages = [{"role": row[0], "content": row[1]} for row in rows]
        
    return messages

def clear_user_history(username):
    mode = get_db_mode()
    if mode == "firestore":
        db = get_firestore_client()
        docs = db.collection('chat_history').where('username', '==', username).stream()
        for doc in docs:
            doc.reference.delete()
    else:
        conn = sqlite3.connect('study_master.db')
        c = conn.cursor()
        c.execute("DELETE FROM chat_history WHERE username = ?", (username,))
        conn.commit()
        conn.close()

# --- 3. LOGICA AI ---

@st.cache_resource(show_spinner=False)
def get_local_embeddings():
    # Usa un modello di embedding leggero per CPU
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
    # Aumentiamo k=6 per avere più contesto
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 6})
    
    # --- CONFIGURAZIONE MODELLO ---
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1) # Temperature bassa per fedeltà
    
    # Prompt STRICT MODE per vincolare al PDF
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """{system_instruction}
        
        SEI IN MODALITÀ "DOCUMENTO ATTIVO".
        
        REGOLE TASSATIVE (STRICT MODE):
        1. DEVI rispondere alla domanda dell'utente BASANDOTI ESCLUSIVAMENTE sui seguenti estratti dal documento PDF fornito.
        2. NON usare la tua conoscenza interna per rispondere a domande che non trovano riscontro nel testo.
        3. Se l'informazione richiesta non è presente nel documento, DEVI RISPONDERE: "Mi dispiace, ma questa informazione non è presente nel documento PDF caricato." (Puoi suggerire di cercare online se rilevante, ma non inventare la risposta).
        4. Cita il documento quando possibile per confermare le tue affermazioni.
        
        CONTESTO ESTRATTO DAL PDF:
        {context}"""),
        ("human", "{input}"),
    ])
    
    qa_chain = create_stuff_documents_chain(llm, prompt_template)
    return create_retrieval_chain(retriever, qa_chain)

def get_general_response(user_input, system_instruction):
    # --- CONFIGURAZIONE MODELLO ---
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.5)
    
    messages = [
        SystemMessage(content=system_instruction),
        HumanMessage(content=user_input)
    ]
    response = llm.invoke(messages)
    return response.content

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
        role = (f"Sei un professore d'esame. Genera ORA {num_questions} domande difficili basate SOLO sul materiale fornito. "
                "Numera le domande. NON dare le soluzioni.")
    elif mode == "🃏 Flashcards":
        role = f"Crea materiale di studio schematico basato SOLO sul testo. {style_text}. Formatta: **Termine** -> _Definizione_."
    else:
        role = "Sei un assistente utile."

    return f"RUOLO: {role}"

# --- HELPER PER BLOCCARE LA UI ---
def lock_ui():
    """Funzione callback chiamata quando l'utente preme invio."""
    st.session_state.processing = True

# --- 4. INTERFACCIA MAIN ---

def main():
    init_db()
    
    # Inizializza stato elaborazione
    if "processing" not in st.session_state:
        st.session_state.processing = False
    
    st.markdown('<div class="main-title">AI Study Master</div>', unsafe_allow_html=True)
    
    # Debug info
    db_mode = get_db_mode()
    if db_mode == "firestore":
        st.markdown('<div style="text-align:center;"><span style="color:green; font-size:0.8em;">☁️ Cloud Database Attivo</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;"><span style="color:orange; font-size:0.8em;">💾 Database Locale (Dati volatili)</span></div>', unsafe_allow_html=True)

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
        
        if HAS_STYLES:
            st.markdown(styles.get_landing_page_html(), unsafe_allow_html=True)
        return

    # --- APP DOPO LOGIN ---
    
    # Variabile di stato per disabilitare i controlli durante l'elaborazione AI
    is_locked = st.session_state.processing

    # --- SIDEBAR: GESTIONE COMPLETA (UPLOAD + SETTINGS) ---
    with st.sidebar:
        st.write(f"👤 Utente: **{st.session_state.user_id}**")
        if st.button("Logout", disabled=is_locked, use_container_width=True):
            st.session_state.user_id = None
            st.session_state.messages = []
            if "vectorstore" in st.session_state: del st.session_state.vectorstore
            st.rerun()
        
        st.markdown("---")
        
        # === SEZIONE DOCUMENTI (Ancorata qui per essere sempre visibile) ===
        st.header("📂 Documenti")
        
        pdf_mode = False # Default
        
        # Logica: Mostra File Attivo O Uploader
        if "vectorstore" in st.session_state and st.session_state.vectorstore is not None:
            pdf_mode = True
            st.success(f"Attivo: **{st.session_state.get('current_filename', 'Doc')}**")
            
            if st.button("❌ Chiudi File", disabled=is_locked, use_container_width=True):
                del st.session_state.vectorstore
                if "current_filename" in st.session_state: del st.session_state.current_filename
                st.rerun()
        else:
            # Uploader sempre visibile se nessun file è caricato
            uploaded_file = st.file_uploader("Carica PDF", type="pdf", disabled=is_locked, label_visibility="visible")
            
            if uploaded_file and not is_locked:
                with st.status("⚙️ Indicizzazione PDF...", expanded=True) as status:
                    try:
                        raw_text = get_pdf_text(uploaded_file)
                        if raw_text:
                            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                            chunks = text_splitter.split_text(raw_text)
                            docs = [Document(page_content=t) for t in chunks]
                            embeddings = get_local_embeddings()
                            st.session_state.vectorstore = FAISS.from_documents(docs, embeddings)
                            st.session_state.current_filename = uploaded_file.name
                            status.update(label="✅ Completato!", state="complete")
                            time.sleep(1)
                            st.rerun()
                        else: 
                            status.update(label="❌ PDF Vuoto", state="error")
                            st.error("Il PDF sembra vuoto o non leggibile.")
                    except Exception as e:
                        status.update(label="❌ Errore", state="error")
                        st.error(f"Errore: {e}")

        st.markdown("---")
        st.header("⚙️ Studio")
        
        # API Key
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            # st.success("✅ API Key Cloud Attiva") # Meno rumore visivo
        else:
            api_key = st.text_input("🔑 Google API Key", type="password", disabled=is_locked)

        if "study_mode" not in st.session_state: st.session_state.study_mode = "💬 Chat / Spiegazione"
        if "response_style" not in st.session_state: st.session_state.response_style = "Bilanciato"
        if "num_questions" not in st.session_state: st.session_state.num_questions = 5

        st.session_state.study_mode = st.radio(
            "Modalità:",
            ["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards"],
            index=["💬 Chat / Spiegazione", "❓ Simulazione Quiz", "🃏 Flashcards"].index(st.session_state.study_mode),
            disabled=is_locked
        )
        
        st.session_state.response_style = st.select_slider(
            "Lunghezza:", 
            options=["Sintetico", "Bilanciato", "Esaustivo"], 
            value=st.session_state.response_style,
            disabled=is_locked
        )
        
        if st.session_state.study_mode == "❓ Simulazione Quiz":
            st.session_state.num_questions = st.slider(
                "N. Domande:", 5, 20, st.session_state.num_questions, disabled=is_locked
            )
        
        st.markdown("---")
        if st.button("🗑️ Reset Chat", disabled=is_locked, use_container_width=True):
            clear_user_history(st.session_state.user_id)
            st.session_state.messages = []
            st.rerun()

    if not api_key:
        st.info("👈 Configura la chiave API nel menu laterale per iniziare.")
        return
    
    os.environ["GOOGLE_API_KEY"] = api_key

    # --- CHAT UI ---
    
    system_instr = get_system_instruction(st.session_state.study_mode, st.session_state.response_style, st.session_state.num_questions)
    
    if "messages" not in st.session_state or len(st.session_state.messages) == 0:
         st.session_state.messages = load_chat_history(st.session_state.user_id)

    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            if pdf_mode:
                st.info(f"📂 **{st.session_state.get('current_filename')}** attivo.\n\nFai una domanda specifica sul contenuto del documento.")
            else:
                st.info("👋 Ciao! Sono il tuo Tutor. Carica un PDF dalla barra laterale per domande specifiche, o chiedimi qualsiasi cosa per iniziare.")

        for message in st.session_state.messages:
            avatar = "🧑‍🎓" if message["role"] == "user" else "🤖"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

    placeholder = "Chiedi al documento..." if pdf_mode else "Fai una domanda..."
    
    # INPUT BAR con callback di blocco
    if user_input := st.chat_input(placeholder, on_submit=lock_ui, disabled=is_locked):
        
        # 1. Salva subito il messaggio utente
        save_message_to_db(st.session_state.user_id, "user", user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        with chat_container.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(user_input)

        # 2. Genera risposta AI
        with chat_container.chat_message("assistant", avatar="🤖"):
            with st.spinner("Sto elaborando..."):
                try:
                    if pdf_mode:
                        rag_chain = build_rag_chain(st.session_state.vectorstore)
                        response = rag_chain.invoke({
                            "input": user_input,
                            "system_instruction": system_instr
                        })
                        answer = response['answer']
                    else:
                        answer = get_general_response(user_input, system_instr)
                    
                    st.markdown(answer)
                    save_message_to_db(st.session_state.user_id, "assistant", answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                except Exception as e:
                    st.error(f"Errore: {e}")
                
                finally:
                    # Al termine (successo o errore), sblocca e ricarica
                    st.session_state.processing = False
                    st.rerun()

if __name__ == '__main__':
    main()
