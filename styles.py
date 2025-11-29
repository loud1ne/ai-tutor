# styles.py

def get_css(is_dark_mode):
    # DEFINIZIONE COLORI (Chiaro vs Scuro)
    if is_dark_mode:
        # TEMA SCURO
        main_bg = "#0E1117"
        sidebar_bg = "#262730"
        text_color = "#FAFAFA"
        card_bg = "#262730"
        card_border = "#4A4A4A"
        
        # Chat
        user_bg = "#1E2A36" # Blu scuro
        user_border = "#4A90E2"
        bot_bg = "#262730"  # Grigio scuro
        bot_border = "#4A4A4A"
        input_bg = "#262730"
    else:
        # TEMA CHIARO (Default)
        main_bg = "#FFFFFF"
        sidebar_bg = "#F0F2F6"
        text_color = "#31333F"
        card_bg = "#F8F9FA"
        card_border = "#E9ECEF"
        
        # Chat
        user_bg = "#F0F8FF" # Azzurrino
        user_border = "#CCE5FF"
        bot_bg = "#FFFFFF"  # Bianco
        bot_border = "#E0E0E0"
        input_bg = "#FFFFFF"

    return f"""
    <style>
        /* IMPORT FONT POPPINS */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {{
            font-family: 'Poppins', sans-serif;
            color: {text_color} !important;
        }}

        /* --- FORZATURA SFONDO APP --- */
        .stApp {{
            background-color: {main_bg};
        }}
        
        /* --- FORZATURA SFONDO SIDEBAR --- */
        [data-testid="stSidebar"] {{
            background-color: {sidebar_bg};
        }}

        /* NASCONDI ELEMENTI STANDARD */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* --- TITOLO PRINCIPALE --- */
        .main-title {{
            font-size: 3rem;
            font-weight: 700;
            background: -webkit-linear-gradient(45deg, #4A90E2, #9013FE);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        
        .sub-title {{
            font-size: 1.2rem;
            color: {text_color};
            opacity: 0.8;
            margin-bottom: 2rem;
        }}

        /* --- CARD LANDING PAGE --- */
        .feature-card {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s ease;
        }}
        .feature-card:hover {{
            transform: translateY(-5px);
            border-color: #4A90E2;
        }}
        .feature-card h3 {{
            color: #4A90E2;
            font-weight: 600;
        }}
        .feature-card p {{
            color: {text_color};
            opacity: 0.8;
        }}

        /* --- CHAT BUBBLES --- */
        .stChatMessage[data-testid="stChatMessage"]:nth-child(odd) {{
            background-color: {user_bg}; 
            border: 1px solid {user_border};
            border-radius: 20px 20px 0px 20px;
        }}
        .stChatMessage[data-testid="stChatMessage"]:nth-child(even) {{
            background-color: {bot_bg}; 
            border: 1px solid {bot_border};
            border-radius: 20px 20px 20px 0px;
        }}

        /* Input Box */
        .stTextInput input {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
        }}
    </style>
    """

def get_landing_page_html():
    return """
    <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>📚 Riassunti Smart</h3>
                <p>Carica dispense infinite. Ottieni sintesi chiare in secondi.</p>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>❓ Simulazione Esame</h3>
                <p>Il sistema si trasforma in un prof severo per testarti.</p>
            </div>
        </div>
        <div style="flex: 1; min-width: 250px;">
            <div class="feature-card">
                <h3>🃏 Flashcards</h3>
                <p>Genera automaticamente tabelle Concetto-Definizione.</p>
            </div>
        </div>
    </div>
    """
