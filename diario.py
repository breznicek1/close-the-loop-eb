"""
diario.py — Leitura do Diário de Bordo via Google Sheets API
Planilha: DIARIO DE BORDO OPERAÇÃO - ESTRELA BET MG
"""

import os
import json
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta


# ─────────────────────────────────────────────
# CONEXÃO GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_diario_raw():
    """Carrega os dados brutos do Diário de Bordo do Google Sheets."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        # Credenciais do secret do Streamlit
        creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
        if not creds_json:
            return None, "Secret GOOGLE_CREDENTIALS não configurado."

        # Limpa possíveis aspas extras
        creds_json = creds_json.strip().strip("'").strip('"')
        creds_dict = json.loads(creds_json)

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gc = gspread.authorize(creds)

        sheet_id = os.environ.get("GOOGLE_SHEETS_ID", "1N26oSEdJuGoV5DBYGvqw5C66A6ePT-ruMmoVGnK8CZU")
        sh = gc.open_by_key(sheet_id)

        # Ler aba "Diario de Bordo - EB"
        ws = sh.worksheet("Diario de Bordo - EB")
        data = ws.get_all_values()
        return data, None

    except Exception as e:
        return None, str(e)


def parse_diario(raw_data):
    """
    Transforma os dados brutos em DataFrame estruturado:
    Colunas: data, dia_semana, lider, ocorrencia
    """
    if not raw_data or len(raw_data) < 5:
        return pd.DataFrame()

    # Linha 0 = índices de coluna (A, B, C...)
    # Linha 1 = datas (24/ago., 25/ago....)
    # Linha 2 = dia da semana
    # Linha 3 = nome do líder (se preenchido)
    # Linha 4 = "Ocorrências" (label)
    # Linha 5 em diante = texto

    # Montar mapa: col_index → data
    row_datas   = raw_data[0] if len(raw_data) > 0 else []
    row_diasem  = raw_data[1] if len(raw_data) > 1 else []

    # Identificar estrutura: lider → row_index do texto
    # Padrão: row com nome do líder, row seguinte "Ocorrências", row seguinte = texto
    lideres_rows = {}  # {lider_nome: row_index_texto}

    i = 0
    while i < len(raw_data):
        row = raw_data[i]
        if not row:
            i += 1
            continue
        val = row[1] if len(row) > 1 else ""
        # Detecta linha de líder (não é data, dia, "Ocorrências" e não é vazia)
        dias_sem = {"dom.","seg.","ter.","qua.","qui.","sex.","sáb.","sab","dom","seg","terça","Quarta","Quinta","Sexta","Sabado","Domingo"}
        if (val and
            val not in dias_sem and
            val != "Ocorrências" and
            val != "Ocorrências - Madrugada" and
            not val.startswith("0") and
            "/" not in val and
            not val[0].isdigit()):
            # Próxima linha deve ser "Ocorrências", depois vem o texto
            if i + 2 < len(raw_data):
                texto_row = i + 2
                lider_key = val
                if lider_key not in lideres_rows:
                    lideres_rows[lider_key] = []
                lideres_rows[lider_key].append(texto_row)
        i += 1

    # Montar DataFrame
    records = []
    ano_atual = 2025

    for col_idx in range(1, len(row_datas)):
        data_str = row_datas[col_idx] if col_idx < len(row_datas) else ""
        dia_sem  = row_diasem[col_idx] if col_idx < len(row_diasem) else ""

        if not data_str or "/" not in data_str:
            continue

        # Parse da data
        try:
            partes = data_str.replace(".", "").split("/")
            dia = int(partes[0])
            mes_str = partes[1].lower()
            mes_map = {"jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,
                       "jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12}
            mes = mes_map.get(mes_str, 0)
            if mes == 0:
                continue
            # Ajusta ano (ago-dez = 2025, jan-abr = 2026)
            ano = 2026 if mes <= 7 else 2025
            dt = date(ano, mes, dia)
        except:
            continue

        # Para cada líder, pega o texto da coluna
        for lider, texto_rows in lideres_rows.items():
            for tr in texto_rows:
                if tr < len(raw_data):
                    row_texto = raw_data[tr]
                    texto = row_texto[col_idx] if col_idx < len(row_texto) else ""
                    if texto and texto.strip():
                        records.append({
                            "data":       dt,
                            "dia_semana": dia_sem,
                            "lider":      lider,
                            "ocorrencia": texto.strip(),
                        })
                        break  # pega só a primeira entrada do líder por dia

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values("data", ascending=False).reset_index(drop=True)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def get_diario():
    """Retorna DataFrame do diário já parseado."""
    raw, err = load_diario_raw()
    if err:
        return pd.DataFrame(), err
    return parse_diario(raw), None
