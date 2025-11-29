# styles.py

def get_css():
    return """
    <style>
        /* IMPORT FONT POPPINS */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }

        /* RIMOSSO IL BLOCCO CHE NASCONDEVA L'HEADER E IL MENU */
        footer {visibility: hidden;}
        
        /* Se vuoi nascondere solo la linea decorativa colorata in alto ma tenere il menu, usa questo: */
        header[data-testid="stHeader"] {
            background: transparent;
        }

        /* --- TITOLO PRINCIPALE (Adattivo) --- */
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

        /* --- CARD DELLA LANDING PAGE (Adattive) --- */
        .feature-card {
            background-color: var(--secondary-background-color);
            border: 1px solid var(--text-color); 
            border-color: rgba(128, 128, 128, 0.2);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            height: 100%;
        }
        
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            border-color: #4A90E2;
        }

        .feature-card h3 {
            color: #4A90E2;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .feature-card p {
            color: var(--text-color);
            font-size: 0.9rem;
            opacity: 0.8;
        }

        /* --- STILE CHAT --- */
        .stChatMessage {
            border-radius: 15px;
            border: 1px solid rgba(128, 128, 128, 0.1);
        }

        /* Avatar */
        .stChatMessage .stImage {
            border-radius: 50%;
            border: 2px solid #4A90E2;
        }

        /* --- STATUS BOX --- */
        div[data-testid="stStatusWidget"] {
            border-radius: 10px;
            border: 1px solid #4A90E2;
        }
    </style>
    """

def get_landing_page_html():
    return """
    <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>📚 Riassunti Smart</h3>
                <p>Carica dispense infinite. Ottieni sintesi chiare, punti chiave e spiegazioni semplificate in secondi.</p>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>❓ Simulazione Esame</h3>
                <p>Il sistema si trasforma in un prof severo. Genera domande d'esame realistiche per testarti.</p>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>🃏 Flashcards</h3>
                <p>Genera automaticamente tabelle e schemi Concetto-Definizione pronti per il ripasso veloce.</p>
            </div>
        </div>
    </div>
    """
