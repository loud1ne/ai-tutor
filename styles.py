# styles.py

def get_css():
    return """
    <style>
        /* IMPORT FONT POPPINS */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }

        footer {visibility: hidden;}
        header[data-testid="stHeader"] {background: transparent;}

        /* --- LOGIN BOX --- */
        .login-container {
            padding: 2rem;
            border-radius: 10px;
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            margin-top: 2rem;
        }

        /* --- TITOLO PRINCIPALE --- */
        .main-title {
            font-size: 3rem;
            font-weight: 700;
            background: -webkit-linear-gradient(45deg, #4A90E2, #9013FE);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .sub-title {
            font-size: 1.2rem;
            color: var(--text-color);
            opacity: 0.8;
            margin-bottom: 2rem;
        }

        /* --- CHAT & CARDS --- */
        .feature-card {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s ease;
            height: 100%;
        }
        .feature-card:hover { transform: translateY(-5px); border-color: #4A90E2; }
        .feature-card h3 { color: #4A90E2; font-weight: 600; margin-bottom: 10px; }
        
        .stChatMessage {
            border-radius: 15px;
            border: 1px solid rgba(128, 128, 128, 0.1);
        }
        .stChatMessage .stImage {
            border-radius: 50%;
            border: 2px solid #4A90E2;
        }
    </style>
    """

def get_landing_page_html():
    return """
    <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>🔒 Area Personale</h3>
                <p>Crea un account per salvare le tue dispense e riprendere le conversazioni dove le hai lasciate.</p>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>🧠 Mappe Mentali</h3>
                <p>Genera automaticamente schemi visivi e grafici per memorizzare concetti complessi.</p>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>📚 RAG Avanzato</h3>
                <p>Carica PDF infiniti, fai quiz e flashcards con la potenza di Gemini Pro.</p>
            </div>
        </div>
    </div>
    """
