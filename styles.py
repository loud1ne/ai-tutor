# styles.py

def get_css():
    return """
    <style>
        /* IMPORT FONT POPPINS */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }

        /* HEADER E FOOTER PULITI */
        footer {visibility: hidden;}
        header[data-testid="stHeader"] {background: transparent;}

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

        /* --- CONTAINER LOGIN --- */
        div[data-testid="stForm"] {
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 15px;
            padding: 20px;
            background-color: var(--secondary-background-color);
        }

        /* --- CARD --- */
        .feature-card {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s ease;
            height: 100%;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            border-color: #4A90E2;
        }

        .feature-card h3 {
            color: #4A90E2;
            font-weight: 600;
            margin-bottom: 10px;
        }

        /* --- CHAT STYLES --- */
        .stChatMessage {
            border-radius: 15px;
            border: 1px solid rgba(128, 128, 128, 0.1);
        }
        .stChatMessage .stImage {
            border-radius: 50%;
            border: 2px solid #4A90E2;
        }
        
        /* Evita trasparenze strane sui messaggi */
        .stChatMessage {
            background-color: rgba(255, 255, 255, 0.05);
        }
    </style>
    """

def get_landing_page_html():
    return """
    <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>🗣️ Tutor Universale</h3>
                <p>Fai domande generali di studio o cultura senza bisogno di documenti.</p>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>📚 Analisi PDF</h3>
                <p>Carica le tue dispense per trasformare il Tutor in uno specialista del tuo corso.</p>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>🔒 Cloud Safe</h3>
                <p>I tuoi dati e le chat sono salvati in locale nel database protetto.</p>
            </div>
        </div>
    </div>
    """
