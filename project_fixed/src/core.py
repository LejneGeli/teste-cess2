import json
import os
from datetime import datetime, timedelta

def extenso_mes(data_str):
    """Converte '16/02' para '16 de fevereiro'."""
    meses = {
        "01": "janeiro", "02": "fevereiro", "03": "março", "04": "abril",
        "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
        "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro"
    }
    try:
        dia, mes = data_str.split("/")
        nome_mes = meses.get(mes, "")
        return f"{int(dia)} de {nome_mes}"
    except:
        return data_str

def gerar_timestamp(data_str, hora_str, offset=0):
    """Gera timestamp Unix ajustado para fuso -3h (Brasília) com delay de 40s por curso."""
    try:
        data_completa = f"{data_str}/2026 {hora_str}"
        dt = datetime.strptime(data_completa, "%d/%m/%Y %H:%M")
        dt_ajustado = dt + timedelta(hours=3, seconds=offset)
        return int(dt_ajustado.timestamp())
    except:
        return 0

def calcular_data_especifica(data_str, dias_adicionais):
    """Calcula uma data futura (D+X) a partir de uma data base."""
    try:
        data_completa = f"{data_str}/2026"
        dt_inicio = datetime.strptime(data_completa, "%d/%m/%Y")
        dt_alvo = dt_inicio + timedelta(days=dias_adicionais)
        return dt_alvo.strftime("%d/%m")
    except:
        return data_str

def limpar_para_json(texto):
    """Remove caracteres que quebram a estrutura do arquivo JSON."""
    if not texto: return ""
    return str(texto).replace('"', '').replace('\n', ' ').replace('\r', '').strip()

def calcular_delay_retomada(total_cursos):
    """
    Retorna o delay em segundos por curso baseado no total de cursos do fluxo de RETOMADA.
    Tabela:
      até 20 cursos  → 120s (2 min)
      21 a 30 cursos →  60s (1 min)
      31 a 50 cursos →  45s
      51+ cursos     →  40s
    """
    if total_cursos <= 20:
        return 120
    elif total_cursos <= 30:
        return 60
    elif total_cursos <= 50:
        return 45
    else:
        return 40

def processar_curso(linha, data_ancora, path_template, index_curso, tipo_fluxo="SC1", data_disparo=None, ano_retomada=None, total_cursos=None):
    # --- 1. LÓGICA DE DEFINIÇÃO DA DATA DE DISPARO ---
    if data_disparo:
        data_envio_base = data_disparo
    else:
        data_referencia = data_ancora
        if tipo_fluxo == "SC1":
            data_envio_base = calcular_data_especifica(data_referencia, 8)
        elif tipo_fluxo == "SC2":
            data_envio_base = calcular_data_especifica(data_referencia, 17)
        elif tipo_fluxo == "F2.1":
            data_envio_base = calcular_data_especifica(data_referencia, 1)
        elif tipo_fluxo in ["SC3", "RETOMADA"] or "Retroativo" in str(tipo_fluxo):
            data_envio_base = calcular_data_especifica(data_referencia, 24)
        elif tipo_fluxo == "Docs":
            data_envio_base = calcular_data_especifica(data_referencia, 31)
        else:
            data_envio_base = calcular_data_especifica(data_referencia, 1)

    data_envio_ds = calcular_data_especifica(data_envio_base, 1)

    # --- 2. MAPEAMENTO GERAL DA PLANILHA ---
    # Mapeamento auditado contra a planilha real (Cursos 2026)
    nome_curso       = limpar_para_json(linha[0])   # A  - Nome do curso
    webhook_link     = linha[4]                     # E  - WEBHOOK Unnichat
    cd_curso_abert   = limpar_para_json(linha[9])   # J  - Código curso + abertura
    tag_foi_plan     = limpar_para_json(linha[11])  # L  - Tag "Foi pra Planilha"
    tag_insc_curso   = limpar_para_json(linha[12])  # M  - Tag "Inscrição"
    tag_cancel       = limpar_para_json(linha[13])  # N  - Tag "Cancelar Inscrição"
    tag_atrasados_f1 = limpar_para_json(linha[14])  # O  - Tag "Iniciar F."
    tag_inicio_f2    = limpar_para_json(linha[15])  # P  - Tag "Fluxo 2"
    tag_inicio_f3    = limpar_para_json(linha[16])  # Q  - Tag "Fluxo 3"
    tag_inicio_f4    = limpar_para_json(linha[17])  # R  - Tag "Fluxo 4"
    tag_inicio_f5    = limpar_para_json(linha[18])  # S  - Tag "Fluxo 5"
    tag_inicio_f6    = limpar_para_json(linha[19])  # T  - Tag "Fluxo 6"
    tag_inicio_f7    = limpar_para_json(linha[20])  # U  - Tag "Fluxo 7"
    tag_inicio_f8    = limpar_para_json(linha[21])  # V  - Tag "Fluxo 8"
    tag_presente_f8  = limpar_para_json(linha[22])  # W  - Tag "Presente"
    # CORREÇÃO: coluna X (23) = Tag Certificado Digital (ex: "4º CBFORENSE - Certificado Digital")
    # Estava sendo mapeada errado; cursos sem certificado têm essa coluna vazia — isso é esperado.
    tag_cert         = limpar_para_json(linha[23])  # X  - Tag Certificado Digital
    tag_insc_geral   = limpar_para_json(linha[24])  # Y  - Tag "Inscritos DD/MM"
    vol_pdf_2        = limpar_para_json(linha[27])  # AB - Volume 2 do PDF
    titulo_pdf       = limpar_para_json(linha[28])  # AC - Título do PDF volume 3
    gatilho_fx       = limpar_para_json(linha[31])  # AF - Gatilho de início do fluxo
    bonus_cursos     = limpar_para_json(linha[32])  # AG - Bônus
    link_hotmart_raw = linha[33]                    # AH - Link Hotmart com XXXXXXXXXXXXXXXXX
    cd_cert          = limpar_para_json(linha[34])  # AI - Código certificado
    cd_aulas         = limpar_para_json(linha[35])  # AJ - Código aulas
    cd_pdf           = limpar_para_json(linha[36])  # AK - Código PDF

    # COLUNAS SC — tags fabricadas pelo sistema
    # CORREÇÃO: AM(38)=Clicou SC1, AN(39)=Cancelar SC1, AO(40)=Clicou SC2, AP(41)=Cancelar SC2
    # AQ(42)=Clicou SC3, AR(43)=Cancelar SC3
    # O código anterior usava AQ/AR para o modo Retroativo, o que estava certo para SC3,
    # mas para SC1/SC2 precisaria das colunas AM/AN e AO/AP.
    # Como o tipo_fluxo já controla qual SC está rodando, usamos as colunas certas por tipo:
    if tipo_fluxo == "SC1":
        tag_clicou_retro   = limpar_para_json(linha[38]) if len(linha) > 38 else ""  # AM
        tag_cancelar_retro = limpar_para_json(linha[39]) if len(linha) > 39 else ""  # AN
    elif tipo_fluxo == "SC2":
        tag_clicou_retro   = limpar_para_json(linha[40]) if len(linha) > 40 else ""  # AO
        tag_cancelar_retro = limpar_para_json(linha[41]) if len(linha) > 41 else ""  # AP
    else:
        # SC3 e Retroativo
        tag_clicou_retro   = limpar_para_json(linha[42]) if len(linha) > 42 else ""  # AQ
        tag_cancelar_retro = limpar_para_json(linha[43]) if len(linha) > 43 else ""  # AR

    # COLUNAS RETOMADA: AS (44) = Clicou, AT (45) = Cancelar — confirmado na planilha real
    tag_clicou_ret_plan   = limpar_para_json(linha[44]) if len(linha) > 44 else ""  # AS
    tag_cancelar_ret_plan = limpar_para_json(linha[45]) if len(linha) > 45 else ""  # AT

    # IMAGEM CERTIFICADO: AV (47)
    link_cert_img = limpar_para_json(linha[47]) if len(linha) > 47 else ""  # AV

    # LINK PDF VOLUME 3: AW (48)
    link_pdf = limpar_para_json(linha[48]) if len(linha) > 48 else ""  # AW

    # --- 3. LÓGICA DE TAGS DINÂMICAS ---
    if "Retroativo" in str(tipo_fluxo):
        tag_clicou_sc_final   = tag_clicou_retro
        tag_cancelar_sc_final = tag_cancelar_retro
    else:
        tag_clicou_sc_final   = f"Clicou - {tipo_fluxo} - {data_ancora} - {nome_curso}"
        tag_cancelar_sc_final = f"Cancelar Envios - {tipo_fluxo} - {data_ancora} - {nome_curso}"

    dias_para_voltar = 1 if (tipo_fluxo in ["SC1", "F2.1"]) else 3
    segunda_referencia_tags = calcular_data_especifica(data_envio_base, -dias_para_voltar)

    tag_sem1 = f"Inscritos {segunda_referencia_tags}"
    tag_sem2 = f"Inscritos {calcular_data_especifica(segunda_referencia_tags, 7)}"
    tag_sem3 = f"Inscritos {calcular_data_especifica(segunda_referencia_tags, 14)}"

    # --- 4. TRATAMENTO DE LINKS E DELAY ---
    # --- LÓGICA DE DELAY DINÂMICO ---
    # Para RETOMADA: delay calculado com base no total de cursos da semana.
    # Para todos os outros fluxos: mantém 120s (2min) fixo.
    if tipo_fluxo == "RETOMADA" and total_cursos is not None:
        delay_por_curso = calcular_delay_retomada(total_cursos)
    else:
        delay_por_curso = 120  # 2min padrão para todos os outros fluxos

    offset_atual = index_curso * delay_por_curso
    data_extenso = extenso_mes(data_ancora)
    data_prazo_cert = calcular_data_especifica(data_ancora, 2)
    data_aulas_ate  = calcular_data_especifica(data_ancora, 8)

    def fix_link_padrao(utm):
        return link_hotmart_raw.replace("XXXXXXXXXXXXXXXXX", utm) if link_hotmart_raw else ""

    def fix_link_sc(sufixo):
        if not link_hotmart_raw: return ""
        link_limpo = link_hotmart_raw.replace("||", "").replace("|", "")
        return link_limpo.replace("XXXXXXXXXXXXXXXXX", f"{tipo_fluxo}_T1|{sufixo}|") + "||"

    def fix_link_retomada(sufixo):
        if not link_hotmart_raw: return ""
        ano = ano_retomada if ano_retomada else "2023"
        return link_hotmart_raw.replace("XXXXXXXXXXXXXXXXX||", f"RETOMADA{ano}_T1|{sufixo}|")

    with open(path_template, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    substituicoes = {
        "{{NOME_CURSO}}":                   nome_curso,
        "{{GATILHO_INICIO_FX}}":            gatilho_fx,
        "{{TAG_FOI_PLANILHA}}":             tag_foi_plan,
        "{{TAG_INSC_CURSO}}":               tag_insc_curso,
        "{{TAG_INSC_GERAL}}":               tag_insc_geral,
        "{{TAG_CANCEL_CURSO}}":             tag_cancel,
        "{{TAG_CERT_CURSO}}":               tag_cert,
        "{{CD_CURSO_CERT}}":                cd_cert,
        "{{CD_CURSO_AULAS}}":               cd_aulas,
        "{{CD_CURSO_PDF}}":                 cd_pdf,
        "{{CD_CURSO_ABERT}}":               cd_curso_abert,
        "{{VOL_PDF_2}}":                    vol_pdf_2,
        "{{BONUS_CURSOS}}":                 bonus_cursos,
        "{{LINK_WEBHOOK_PLANILHA}}":        webhook_link,
        "{{DT_INICIO_CURSO_EXT}}":          data_extenso,
        "{{DT_INICIO_CURSO_FORMAT}}":       data_ancora,
        "{{DT_AULAS_DISP_CURSO_FORMAT}}":   data_aulas_ate,
        "{{DT_FIM_CERT_FORMAT}}":           data_prazo_cert,
        "{{LINK_CERTIFICADO_IMG}}":         link_cert_img,
        "{{TAG_INIC_F_CURSO}}":             tag_atrasados_f1,
        "{{TAG_INIC_F2_CURSO}}":            tag_inicio_f2,
        "{{TAG_INIC_F3_CURSO}}":            tag_inicio_f3,
        "{{TAG_INIC_F4_CURSO}}":            tag_inicio_f4,
        "{{TAG_INIC_F5_CURSO}}":            tag_inicio_f5,
        "{{TAG_INIC_F6_CURSO}}":            tag_inicio_f6,
        "{{TAG_INIC_F7_CURSO}}":            tag_inicio_f7,
        "{{TAG_INIC_F8_CURSO}}":            tag_inicio_f8,
        "{{TAG_PRESENTE_F8_CURSO}}":        tag_presente_f8,
        "{{LINK_PDF_VOL_3}}":               link_pdf,
        "{{VOL_PDF_3}}":                    titulo_pdf,
        # Links Hotmart — fluxos padrão
        "{{LINK_HOTMART_F1_M1_CURSO}}":     fix_link_padrao("apis15c"),
        "{{LINK_HOTMART_F4_M1_CURSO}}":     fix_link_padrao("apiq8c"),
        "{{LINK_HOTMART_F5_M1_CURSO}}":     fix_link_padrao("apiq12c"),
        "{{LINK_HOTMART_F6_M1_CURSO}}":     fix_link_padrao("apiq18c"),
        # CORREÇÃO: F7 tinha M2, M3 e M4 faltando no código anterior
        "{{LINK_HOTMART_F7_M1_CURSO}}":     fix_link_padrao("apiq20c"),
        "{{LINK_HOTMART_F7_M2_CURSO}}":     fix_link_padrao("apiq21c"),
        "{{LINK_HOTMART_F7_M3_CURSO}}":     fix_link_padrao("apiq20t"),
        "{{LINK_HOTMART_F7_M4_CURSO}}":     fix_link_padrao("apiq21t"),
        "{{LINK_HOTMART_F8_M1_CURSO}}":     fix_link_padrao("apiq15c"),
        # Timestamps — Fluxo 1
        "{{DT_VARIA_11_F1}}":               str(gerar_timestamp(data_ancora, "11:00", offset_atual)),
        "{{DT_VARIA_14_F1}}":               str(gerar_timestamp(data_ancora, "14:00", offset_atual)),
        "{{DT_VARIA_15_F1}}":               str(gerar_timestamp(data_ancora, "15:00", offset_atual)),
        "{{DT_VARIA_19_F1}}":               str(gerar_timestamp(data_ancora, "19:00", offset_atual)),
        "{{DT_VARIA_20_F1}}":               str(gerar_timestamp(data_ancora, "20:00", offset_atual)),
        "{{DT_VARIA_21_F7}}":               str(gerar_timestamp(data_prazo_cert, "21:00", offset_atual)),
        "{{DT_VARIA_22_F7}}":               str(gerar_timestamp(data_prazo_cert, "22:00", offset_atual)),
        "{{DT_ANTES_INIC_CURSO}}":          str(gerar_timestamp(data_ancora, "08:00", 0)),
        "{{DT_ANTES_FIM_CERT}}":            str(gerar_timestamp(data_prazo_cert, "10:00", 0)),
        # Tags SC — ambos os formatos de chaves ({{}} e {}) que existem nos templates
        "{{TAG_CLICOU_SC}}":                tag_clicou_sc_final,
        "{TAG_CLICOU_SC}":                  tag_clicou_sc_final,
        "{{TAG_CANCELAR_ENVIOS_SC}}":       tag_cancelar_sc_final,
        "{TAG_CANCELAR_ENVIOS_SC}":         tag_cancelar_sc_final,
        # Tags semana (formato chave simples)
        "{TAG_INSC_SEMANA1}":               tag_sem1,
        "{TAG_INSC_SEMANA2}":               tag_sem2,
        "{TAG_INSC_SEMANA3}":               tag_sem3,
        # Timestamps SC1
        "{{DT_SC_1230_VARIA}}":             str(gerar_timestamp(data_envio_base, "12:30", offset_atual)),
        "{{DT_SC_1900_VARIA}}":             str(gerar_timestamp(data_envio_base, "19:00", offset_atual)),
        "{{DT_SC_2100_VARIA}}":             str(gerar_timestamp(data_envio_base, "21:00", offset_atual)),
        "{{DT_SC_DS_0740_VARIA}}":          str(gerar_timestamp(data_envio_ds, "07:40", offset_atual)),
        # Timestamps SC2
        "{{DT_SC2_1330_VARIA}}":            str(gerar_timestamp(data_envio_base, "13:30", offset_atual)),
        "{{DT_SC2_1930_VARIA}}":            str(gerar_timestamp(data_envio_base, "19:30", offset_atual)),
        "{{DT_SC2_2130_VARIA}}":            str(gerar_timestamp(data_envio_base, "21:30", offset_atual)),
        "{{DT_SC2_DS_0800_VARIA}}":         str(gerar_timestamp(data_envio_ds, "08:00", offset_atual)),
        # Timestamps SC3
        "{{DT_SC3_1400_VARIA}}":            str(gerar_timestamp(data_envio_base, "14:00", offset_atual)),
        "{{DT_SC3_1900_VARIA}}":            str(gerar_timestamp(data_envio_base, "19:00", offset_atual)),
        "{{DT_SC3_2100_VARIA}}":            str(gerar_timestamp(data_envio_base, "21:00", offset_atual)),
        "{{DT_SC3_DS_0740_VARIA}}":         str(gerar_timestamp(data_envio_ds, "07:40", offset_atual)),
        # Links SC
        "{{LINK_HOTMART_SC_M1_T1}}":        fix_link_sc("M1"),
        "{{LINK_HOTMART_SC_M2_T1}}":        fix_link_sc("M2"),
        "{{LINK_HOTMART_SC_M3_T1}}":        fix_link_sc("M3"),
        "{{LINK_HOTMART_SC_M4_T1}}":        fix_link_sc("M4"),
        "{{LINK_HOTMART_SC_M5_T1}}":        fix_link_sc("M5"),
        "{{LINK_HOTMART_SC_M6_T1}}":        fix_link_sc("M6"),
        "{{LINK_HOTMART_SC_M7_T1}}":        fix_link_sc("M7"),
        "{{LINK_HOTMART_SC_M8_T1}}":        fix_link_sc("M8"),
        "{{LINK_HOTMART_SC_rep1_T1}}":      fix_link_sc("rep1"),
        "{{LINK_HOTMART_SC_rep2_T1}}":      fix_link_sc("rep2"),
        "{{LINK_HOTMART_SC_mudei1_T1}}":    fix_link_sc("mudei1"),
        "{{LINK_HOTMART_SC_mudei2_T1}}":    fix_link_sc("mudei2"),
        # UTMs
        "{{UTM_SC_LOJA}}":                  f"utm_source={tipo_fluxo}",
        "{{LINK_HOTMART_SC2.1}}":           fix_link_padrao("novat"),
        # Timestamp principal do fluxo de Retomada (atraso inteligente, com offset por curso)
        "{{DT_RETOMADA_INICIO_VARIA}}":     str(gerar_timestamp(data_envio_base, "08:00", offset_atual)),
        # Retomada — AS(44)=Clicou, AT(45)=Cancelar, confirmado na planilha real
        "{{TAG_CLICOU_RETOMADA}}":          tag_clicou_ret_plan,
        "{{TAG_CANCELAR_ENVIOS_RETOMADA}}": tag_cancelar_ret_plan,
        "{{LINK_HOTMART_RETOMADA_M1}}":     fix_link_retomada("M1"),
        "{{LINK_HOTMART_RETOMADA_M2}}":     fix_link_retomada("M2"),
        "{{LINK_HOTMART_RETOMADA_M3}}":     fix_link_retomada("M3"),
        "{{LINK_HOTMART_RETOMADA_M4}}":     fix_link_retomada("M4"),
        "{{LINK_HOTMART_RETOMADA_M5}}":     fix_link_retomada("M5"),
        "{{LINK_HOTMART_RETOMADA_M6}}":     fix_link_retomada("M6"),
        "{{LINK_HOTMART_RETOMADA_M7}}":     fix_link_retomada("M7"),
        "{{LINK_HOTMART_RETOMADA_M8}}":     fix_link_retomada("M8"),
        "{{LINK_HOTMART_RETOMADA_mudei1}}": fix_link_retomada("mudei1"),
        "{{LINK_HOTMART_RETOMADA_mudei2}}": fix_link_retomada("mudei2"),
        "{{LINK_HOTMART_RETOMADA_rep1}}":   fix_link_retomada("rep1"),
        "{{LINK_HOTMART_RETOMADA_rep2}}":   fix_link_retomada("rep2"),
        "{{UTM_RETOMADA_LOJA}}":            f"utm_source=RETOMADA{ano_retomada if ano_retomada else '2023'}",
    }

    for tag, valor in substituicoes.items():
        conteudo = conteudo.replace(tag, str(valor))

    return json.loads(conteudo)
