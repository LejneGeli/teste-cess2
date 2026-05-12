import streamlit as st
import json
import io
import zipfile
import re
import os
import sys

# Garante que o Python encontra src/ independente de onde o Streamlit é iniciado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.drive_sync import (
    conectar_planilha,
    buscar_mapeamento_contas,
    buscar_cores_linhas,
)
from src.core import processar_curso

# Configuração da Interface
st.set_page_config(page_title="CESS Automation Web", page_icon="🚀", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def template_path(nome_arquivo):
    return os.path.join(BASE_DIR, "templates", nome_arquivo)

# Mapeamento Global dos Fluxos
TEMPLATES = {
    "1":  {"nome": "Inscrição",     "path": template_path("esqueleto_fluxo_insc.json"),    "subpasta": "Fluxo_insc"},
    "2":  {"nome": "Pré-Inscrição", "path": template_path("esqueleto_fluxo_pre_insc.json"),"subpasta": "Fluxo_pre_insc"},
    "3":  {"nome": "Fluxo 1",       "path": template_path("esqueleto_fluxo_1.json"),        "subpasta": "Fluxo_1"},
    "4":  {"nome": "Fluxo 2",       "path": template_path("esqueleto_fluxo_2.json"),        "subpasta": "Fluxo_2"},
    "15": {"nome": "F2.1",          "path": template_path("esqueleto_fluxo_2.1.json"),      "subpasta": "Fluxo_F2_1"},
    "5":  {"nome": "Fluxo 3",       "path": template_path("esqueleto_fluxo_3.json"),        "subpasta": "Fluxo_3"},
    "6":  {"nome": "Fluxo 4",       "path": template_path("esqueleto_fluxo_4.json"),        "subpasta": "Fluxo_4"},
    "7":  {"nome": "Fluxo 5",       "path": template_path("esqueleto_fluxo_5.json"),        "subpasta": "Fluxo_5"},
    "17": {"nome": "F5.1",          "path": template_path("esqueleto_fluxo_5.1.json"),      "subpasta": "Fluxo_F5_1"},
    "8":  {"nome": "Fluxo 6",       "path": template_path("esqueleto_fluxo_6.json"),        "subpasta": "Fluxo_6"},
    "9":  {"nome": "Fluxo 7",       "path": template_path("esqueleto_fluxo_7.json"),        "subpasta": "Fluxo_7"},
    "10": {"nome": "Fluxo 8",       "path": template_path("esqueleto_fluxo_8.json"),        "subpasta": "Fluxo_8"},
    "11": {"nome": "SC1",           "path": template_path("esqueleto_fluxo_sc1.json"),      "subpasta": "Fluxo_SC1"},
    "12": {"nome": "SC2",           "path": template_path("esqueleto_fluxo_sc2.json"),      "subpasta": "Fluxo_SC2"},
    "13": {"nome": "SC3",           "path": template_path("esqueleto_fluxo_sc3.json"),      "subpasta": "Fluxo_SC3"},
    "16": {"nome": "RETOMADA",      "path": template_path("esqueleto_retomada.json"),       "subpasta": "Fluxo_Retomada"},
    "14": {"nome": "Docs",          "path": template_path("esqueleto_docs.json"),           "subpasta": "Fluxo_Docs"}
}

st.title("🚀 Gerador de Fluxos CESS")
st.markdown("Gere e baixe seus arquivos JSON de automação de forma simples e rápida.")

# --- 1. CONFIGURAÇÃO DE ENTRADA ---
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        fluxo_label = st.selectbox(
            "Selecione o Fluxo:",
            ["Inscrição", "Pré-Inscrição", "F1", "F2", "F2.1", "F3", "F4", "F5", "F5.1",
             "F6", "F7", "F8", "SC1", "SC2", "SC3", "RETOMADA", "Docs (Em breve) 🔒", "GERAR TODOS"]
        )
        map_labels = {
            "Inscrição":"1", "Pré-Inscrição":"2", "F1":"3", "F2":"4", "F2.1":"15", "F3":"5",
            "F4":"6", "F5":"7", "F5.1":"17", "F6":"8", "F7":"9", "F8":"10", "SC1":"11",
            "SC2":"12", "SC3":"13", "RETOMADA":"16", "Docs (Em breve) 🔒": "14", "GERAR TODOS":"99"
        }
        id_fluxo = map_labels[fluxo_label]

    with col2:
        data_semana = st.text_input("Data do Curso (para as tags de Clique):", value="16/02")

# --- LÓGICA ESPECÍFICA PARA RETOMADA ---
ano_retomada = None
if fluxo_label == "RETOMADA":
    st.info("📂 **Configuração de Retomada**")
    nome_fluxo_retomada = st.text_input("Nome do Fluxo (Ex: Retomada - T 2023):", placeholder="Retomada - T 2023")
    match_ano = re.search(r"202\d", nome_fluxo_retomada)
    if match_ano:
        ano_retomada = match_ano.group(0)
    else:
        st.warning("⚠️ Digite o ano no campo acima para gerar os links corretamente.")

# --- LÓGICA DE FLUXO RETROATIVO ---
st.divider()
is_retro = st.checkbox("🔄 Este fluxo é retroativo? (Ex: curso de Janeiro rodando agora)")
data_disparo_manual = None

if is_retro:
    data_disparo_manual = st.text_input("Data da Segunda-feira que vai RODAR (DD/MM):", placeholder="Ex: 02/02")
    if data_disparo_manual:
        st.info(f"""
        💡 **Modo Retroativo Ativado:**
        * **Tags de Inscritos (Exclusão):** Geradas para a semana de **{data_disparo_manual}** (D+0, D+7, D+14).
        * **Agendamento (Timestamps):** Programados para a semana de **{data_disparo_manual}** (Terça a Sexta).
        * **Identidade do Fluxo:** Mantida como safra de **{data_semana}** (Cliques e Tags Internas).
        """)

# --- 2. BUSCA DE DADOS ---
if st.button("🔍 Buscar Cursos na Planilha", use_container_width=True):
    with st.spinner("Acessando Google Sheets..."):
        client = conectar_planilha("Informações Webhook")
        if client:
            try:
                aba = client.open("Informações Webhook").worksheet("Cursos 2026")
                dados = aba.get_all_values(value_render_option='FORMATTED_VALUE')

                inicio = next(
                    (i + 2 for i, l in enumerate(dados) if len(l) > 1 and data_semana in str(l[1])),
                    None
                )

                if inicio:
                    cursos_encontrados = []
                    for i in range(inicio, len(dados)):
                        linha = dados[i]
                        if not linha or not linha[0].strip() or (len(linha) > 1 and "Semana" in str(linha[1])):
                            break
                        cursos_encontrados.append(linha[0].strip())

                    # ── NOVIDADE: busca cores e mapeamento de contas ──────────────
                    with st.spinner("Lendo cores das contas na planilha..."):
                        mapeamento_contas = buscar_mapeamento_contas(client, "Informações Webhook")

                        cores_lista = buscar_cores_linhas(
                            client,
                            "Informações Webhook",
                            "Cursos 2026",
                            inicio + 1,          # converte índice Python (base 0) para linha real (base 1)
                            len(cursos_encontrados),
                        )

                    # Mapeia: índice dentro de 'dados' -> cor hex do curso
                    cores_por_indice = {
                        inicio + j: cor
                        for j, cor in enumerate(cores_lista)
                    }
                    # ─────────────────────────────────────────────────────────────

                    st.session_state['cursos']           = cursos_encontrados
                    st.session_state['dados_planilha']   = dados
                    st.session_state['index_inicio']     = inicio
                    st.session_state['mapeamento_contas']= mapeamento_contas
                    st.session_state['cores_por_indice'] = cores_por_indice

                    st.success(f"✅ {len(cursos_encontrados)} cursos encontrados!")

                    # Exibe preview do mapeamento detectado
                    if mapeamento_contas:
                        itens = " · ".join(
                            [f"**{conta}** `{hex_cor}`" for hex_cor, conta in mapeamento_contas.items()]
                        )
                        st.info(f"🎨 Contas detectadas: {itens}")
                    else:
                        st.warning("⚠️ Não foi possível detectar as cores das contas. Verifique a aba 'Como funciona?'.")
                else:
                    st.error(f"❌ A data '{data_semana}' não foi encontrada na Coluna B da planilha.")
            except Exception as e:
                st.error(f"❌ Erro ao abrir a planilha/aba: {e}")

# --- 3. FILTRO E GERAÇÃO ---
if 'cursos' in st.session_state:
    st.divider()
    st.subheader("Configuração da Geração")

    curso_filtro = st.multiselect(
        "Selecione cursos específicos (ou deixe vazio para todos):",
        st.session_state['cursos']
    )

    if id_fluxo == "14":
        st.warning("🔒 O fluxo de **Docs** ainda está em desenvolvimento e o template não foi carregado.")
        btn_disabled = True
    else:
        btn_disabled = False

    if st.button("🏗️ Gerar Arquivos e Preparar ZIP", use_container_width=True, disabled=btn_disabled):
        zip_buffer = io.BytesIO()

        if id_fluxo == "99":
            fluxos_alvo = [v for k, v in TEMPLATES.items() if k != "14"]
        else:
            fluxos_alvo = [TEMPLATES[id_fluxo]]

        arquivos_criados = 0
        mapeamento_contas  = st.session_state.get('mapeamento_contas', {})
        cores_por_indice   = st.session_state.get('cores_por_indice', {})

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for config in fluxos_alvo:
                contador_delay = 0
                nome_fluxo_ativo = (
                    config['nome']
                    if any(x in config['nome'] for x in ["SC", "Docs", "F2.1", "F5.1", "RETOMADA"])
                    else "F1"
                )

                total_cursos_semana = None
                if nome_fluxo_ativo == "RETOMADA":
                    total_cursos_semana = 0
                    for i in range(st.session_state['index_inicio'], len(st.session_state['dados_planilha'])):
                        linha_aux = st.session_state['dados_planilha'][i]
                        if not linha_aux or not linha_aux[0].strip() or (len(linha_aux) > 1 and "Semana" in str(linha_aux[1])):
                            break
                        total_cursos_semana += 1

                for i in range(st.session_state['index_inicio'], len(st.session_state['dados_planilha'])):
                    linha = st.session_state['dados_planilha'][i]
                    if not linha or not linha[0].strip() or (len(linha) > 1 and "Semana" in str(linha[1])):
                        break

                    nome_curso = linha[0].strip()
                    if curso_filtro and nome_curso not in curso_filtro:
                        continue

                    try:
                        json_data = processar_curso(
                            linha,
                            data_semana,
                            config['path'],
                            contador_delay,
                            tipo_fluxo=nome_fluxo_ativo,
                            data_disparo=data_disparo_manual,
                            ano_retomada=ano_retomada,
                            total_cursos=total_cursos_semana
                        )

                        nome_limpo = nome_curso.replace(" ", "_").replace("/", "-").replace(":", "")

                        # ── NOVIDADE: determina a subpasta da conta pela cor ──────
                        cor_curso   = cores_por_indice.get(i, "#FFFFFF")
                        conta_pasta = mapeamento_contas.get(cor_curso, "Sem_Conta")
                        # ─────────────────────────────────────────────────────────

                        caminho_zip = f"{config['subpasta']}/{conta_pasta}/{nome_limpo}.json"

                        zip_file.writestr(caminho_zip, json.dumps(json_data, indent=2, ensure_ascii=False))
                        arquivos_criados += 1
                        contador_delay += 1
                    except Exception as e:
                        st.error(f"Erro no curso '{nome_curso}': {e}")

        if arquivos_criados > 0:
            st.success(f"🚀 {arquivos_criados} arquivos processados!")
            st.download_button(
                label="⬇️ Baixar Arquivos (.ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"automacao_cess_{data_semana.replace('/','-')}.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.warning("Nenhum arquivo gerado.")

st.divider()
st.caption("CESS Automation System 2026 - Versão Web Estável")
