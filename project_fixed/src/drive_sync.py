import gspread
from google.oauth2.service_account import Credentials
import os
import streamlit as st

def conectar_planilha(nome_planilha):
    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # 1. Tenta conectar via Streamlit Secrets (MODO WEB)
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            # Corrige as quebras de linha da chave privada que vem do TOML
            if "private_key" in creds_info:
                creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            
            credenciais = Credentials.from_service_account_info(creds_info, scopes=escopos)
            return gspread.authorize(credenciais)

        # 2. Se não estiver no Streamlit, tenta o arquivo local (MODO VS CODE)
        # Ajustei para procurar na raiz ou na pasta config conforme sua estrutura
        caminhos_possiveis = [
            "credentials.json",
            os.path.join("config", "credentials.json"),
            os.path.join(os.path.dirname(__file__), "..", "config", "credentials.json")
        ]
        
        caminho_final = None
        for p in caminhos_possiveis:
            if os.path.exists(p):
                caminho_final = p
                break
        
        if caminho_final:
            credenciais = Credentials.from_service_account_file(caminho_final, scopes=escopos)
            return gspread.authorize(credenciais)
        else:
            st.error("❌ Arquivo credentials.json não encontrado localmente e Secrets não configuradas.")
            return None

    except Exception as e:
        st.error(f"❌ Erro na conexão: {e}")
        return None