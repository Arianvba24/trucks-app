import pandas as pd
import time
import streamlit as st
import json
import hashlib
import hmac

TEXT_OPERATORS = ["es igual a", "no es igual a", "contiene", "no contiene"]
NUMBER_OPERATORS = [
    "es igual a",
    "no es igual a",
    "mayor que",
    "menor que",
    "mayor o igual que",
    "menor o igual que",
]


def apply_single_filter(df: pd.DataFrame, column: str, condition: dict) -> pd.DataFrame:
    """Aplica una única condición sobre el dataframe recibido."""
    if column not in df.columns:
        return df

    operator = condition.get("operator")
    value = condition.get("value")

    if value is None or value == "":
        return df

    if condition.get("kind") == "number":
        series = pd.to_numeric(df[column], errors="coerce")
        try:
            target = float(value)
        except (TypeError, ValueError):
            return df

        operations = {
            "es igual a": series == target,
            "no es igual a": series != target,
            "mayor que": series > target,
            "menor que": series < target,
            "mayor o igual que": series >= target,
            "menor o igual que": series <= target,
        }
        mask = operations.get(operator)
    else:
        series = df[column].astype("string").fillna("")
        target = str(value)

        if operator == "es igual a":
            mask = series.str.casefold() == target.casefold()
        elif operator == "no es igual a":
            mask = series.str.casefold() != target.casefold()
        elif operator == "contiene":
            mask = series.str.contains(target, case=False, regex=False, na=False)
        elif operator == "no contiene":
            mask = ~series.str.contains(target, case=False, regex=False, na=False)
        else:
            mask = None

    if mask is None:
        return df

    return df.loc[mask.fillna(False)].copy()

def show_cool_loading_screen():
    loading = st.empty()

    with loading.container():
        st.markdown("""
        <style>
        /* OCULTAR TODOS LOS ELEMENTOS DE STREAMLIT */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* PANTALLA COMPLETA DE CARGA */
        .loading-fullscreen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            color: white;
        }

        /* MENSAJE DE BIENVENIDA */
        .welcome-message {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 10px;
            text-align: center;
            background: linear-gradient(135deg, #ffffff, #f0f0f0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .welcome-subtitle {
            font-size: 18px;
            font-weight: 300;
            margin-bottom: 40px;
            text-align: center;
            opacity: 0.9;
        }

        .pulse-container { 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            margin: 30px 0; 
        }

        .pulse-circle {
            width: 100px; 
            height: 100px; 
            background: white; 
            border-radius: 50%; 
            position: relative;
            animation: pulse 2s infinite; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            font-size: 50px; 
            color: #764ba2;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .pulse-circle::before, .pulse-circle::after {
            content: ''; 
            position: absolute; 
            border: 2px solid white; 
            border-radius: 50%;
            width: 100%; 
            height: 100%; 
            animation: ripple 2s infinite;
            opacity: 0.7;
        }

        .pulse-circle::after { 
            animation-delay: 0.5s; 
        }

        @keyframes pulse { 
            0% { 
                transform: scale(0.95); 
                box-shadow: 0 0 0 0 rgba(255,255,255,0.7); 
            }
            70% { 
                transform: scale(1); 
                box-shadow: 0 0 0 30px rgba(255,255,255,0); 
            }
            100% { 
                transform: scale(0.95); 
                box-shadow: 0 0 0 0 rgba(255,255,255,0); 
            } 
        }

        @keyframes ripple { 
            0% { 
                transform: scale(1); 
                opacity: 1; 
            } 
            100% { 
                transform: scale(2); 
                opacity: 0; 
            } 
        }

        .loading-text { 
            font-size: 20px; 
            font-weight: 300; 
            margin-top: 30px; 
            text-align: center; 
            opacity: 0.8;
        }

        .progress-container { 
            width: 400px; 
            height: 6px; 
            background: rgba(255,255,255,0.2); 
            border-radius: 3px; 
            margin-top: 30px; 
            overflow: hidden; 
        }

        .progress-bar { 
            height: 100%; 
            background: linear-gradient(90deg, #ffffff, #f0f0f0); 
            width: 0%; 
            border-radius: 3px; 
            animation: progress 3s ease-in-out; 
        }

        @keyframes progress { 
            0% { 
                width: 0%; 
            } 
            100% { 
                width: 100%; 
            } 
        }

        /* OCULTAR CONTENIDO MIENTRAS CARGA */
        .app-content {
            display: none;
        }
        </style>
        """, unsafe_allow_html=True)

        # PANTALLA DE CARGA CON MENSAJE DE BIENVENIDA
        st.markdown("""
        <div class='loading-fullscreen'>
            <div class='welcome-message'>🚧 Data Labs</div>
            <div class='welcome-subtitle'>Vendedores de camiones en España</div>
            <div class='pulse-container'>
                <div class='pulse-circle'>🚛</div>
            </div>
            <div class='loading-text'>Cargando componentes...</div>
            <div class='progress-container'>
                <div class='progress-bar'></div>
            </div>
            <div style='margin-top: 20px; font-size: 12px; opacity: 0.6;'>
                Cargando columnas de texto, urls, etc...
            </div>
        </div>
        """, unsafe_allow_html=True)

        time.sleep(3)

        loading.empty()

def verify_user(username, password):

    with open("users.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    for user in data["users"]:

        if user["username"] == username:

            password_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                user["salt"].encode(),
                200000
            ).hex()

            return hmac.compare_digest(
                password_hash,
                user["password_hash"]
            )

    return False


def login():

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:

        st.title("Data Labs")
        st.subheader("Iniciar sesión")

        with st.form("login_form"):

            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")

            submitted = st.form_submit_button(
                "Iniciar sesión",
                use_container_width=True
            )

            if submitted:

                if verify_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    show_cool_loading_screen()
                    st.rerun()
                    

                else:
                    st.error("Usuario o contraseña incorrectos")

        st.stop()