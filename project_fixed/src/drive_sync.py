import gspread
from google.oauth2.service_account import Credentials
import os
import streamlit as st

# Base da Sheets API v4
_SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"

# ─────────────────────────────────────────────
# CONEXÃO
# ─────────────────────────────────────────────

def conectar_planilha(informacoes_webhook):
    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        # 1. Streamlit Secrets (modo web / deploy)
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_info:
                creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            credenciais = Credentials.from_service_account_info(creds_info, scopes=escopos)
            return gspread.authorize(credenciais)

        # 2. Arquivo local (modo VS Code)
        caminhos_possiveis = [
            "credentials.json",
            os.path.join("config", "credentials.json"),
            os.path.join(os.path.dirname(__file__), "..", "config", "credentials.json")
        ]
        caminho_final = next((p for p in caminhos_possiveis if os.path.exists(p)), None)

        if caminho_final:
            credenciais = Credentials.from_service_account_file(caminho_final, scopes=escopos)
            return gspread.authorize(credenciais)
        else:
            st.error("❌ credentials.json não encontrado e Secrets não configuradas.")
            return None

    except Exception as e:
        st.error(f"❌ Erro na conexão: {e}")
        return None


# ─────────────────────────────────────────────
# FUNÇÕES DE COR
# ─────────────────────────────────────────────

def _rgb_para_hex(bg: dict) -> str:
    """Converte o dict RGB retornado pela API ({ red, green, blue }) para #RRGGBB."""
    r = round(bg.get("red",   1) * 255)
    g = round(bg.get("green", 1) * 255)
    b = round(bg.get("blue",  1) * 255)
    return f"#{r:02X}{g:02X}{b:02X}"


def _buscar_cores_api(client, spreadsheet_id: str, range_str: str) -> list:
    """
    Chama a Sheets API (spreadsheets.get com includeGridData) e retorna
    a lista de rowData para o range especificado.
    """
    url = f"{_SHEETS_API_BASE}/{spreadsheet_id}"
    response = client.http_client.request(
        "GET",
        url,
        params={
            "ranges": range_str,
            "fields": "sheets.data.rowData.values.effectiveFormat.backgroundColor",
            "includeGridData": "true",
        },
    )
    try:
        return response.json()["sheets"][0]["data"][0].get("rowData", [])
    except (KeyError, IndexError, ValueError):
        return []


def buscar_mapeamento_contas(client, spreadsheet_name: str) -> dict:
    """
    Lê as cores de D2:D5 da aba 'Como funciona?' e devolve o mapeamento:
        { '#RRGGBB': 'Conta_1', '#RRGGBB': 'Conta_2', ... }

    Ordem das linhas:
        D2 -> Conta_1  (Cessetembro)
        D3 -> Conta_2  (Cessetembro 2)
        D4 -> Conta_3  (Cessetembro 3)
        D5 -> Conta_4  (Cessetembro 4)
    """
    spreadsheet = client.open(spreadsheet_name)
    row_data = _buscar_cores_api(
        client,
        spreadsheet.id,
        "'Como funciona?'!D2:D5",
    )

    mapeamento = {}
    for i, row in enumerate(row_data, start=1):
        try:
            bg      = row["values"][0]["effectiveFormat"]["backgroundColor"]
            hex_cor = _rgb_para_hex(bg)
            if hex_cor != "#FFFFFF":           # ignora células sem preenchimento
                mapeamento[hex_cor] = f"Conta_{i}"
        except (KeyError, IndexError, TypeError):
            pass

    return mapeamento


def buscar_cores_linhas(
    client,
    spreadsheet_name: str,
    worksheet_name: str,
    linha_inicio_sheet: int,
    quantidade: int,
) -> list:
    """
    Retorna a cor de fundo (#RRGGBB) da coluna A para `quantidade` linhas,
    começando em `linha_inicio_sheet` (numero da linha na planilha, base 1).

    O indice 0 da lista retornada corresponde a linha `linha_inicio_sheet`.
    """
    spreadsheet = client.open(spreadsheet_name)
    linha_fim  = linha_inicio_sheet + quantidade - 1
    range_str  = f"'{worksheet_name}'!A{linha_inicio_sheet}:A{linha_fim}"

    row_data = _buscar_cores_api(client, spreadsheet.id, range_str)

    cores = []
    for row in row_data:
        try:
            bg      = row["values"][0]["effectiveFormat"]["backgroundColor"]
            hex_cor = _rgb_para_hex(bg)
        except (KeyError, IndexError, TypeError):
            hex_cor = "#FFFFFF"
        cores.append(hex_cor)

    # Garante tamanho exato (a API pode omitir linhas vazias no final)
    while len(cores) < quantidade:
        cores.append("#FFFFFF")

    return cores[:quantidade]
