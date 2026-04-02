"""
importar_base_historica.py
Importa a base histórica avaliada (Base_avaliada.xlsx) para o Supabase,
atualizando os campos analise_csat, oportunidade e observacao nos
registros já existentes na ctlloop_analise.
"""

import os
import pandas as pd
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

ARQUIVO = "Base avaliada.xlsx"

def importar():
    print("=== Importação base histórica avaliada ===")

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Lê o arquivo histórico
    df = pd.read_excel(ARQUIVO)
    df.columns = ["ticket_id", "analise_csat", "oportunidade", "observacao"]
    df["ticket_id"] = df["ticket_id"].astype(str)
    print(f"Registros na base histórica: {len(df)}")

    # Busca todos os ticket_ids existentes no Supabase
    existentes = {}
    offset = 0
    while True:
        res = (
            sb.table("ctlloop_analise")
            .select("id,ticket_id")
            .range(offset, offset + 999)
            .execute()
        )
        if not res.data:
            break
        for r in res.data:
            existentes[str(r["ticket_id"])] = r["id"]
        if len(res.data) < 1000:
            break
        offset += 1000

    print(f"Registros no Supabase: {len(existentes)}")

    # Filtra apenas os que existem no Supabase
    df_match = df[df["ticket_id"].isin(existentes.keys())].copy()
    df_sem_match = df[~df["ticket_id"].isin(existentes.keys())]
    print(f"Tickets com match no Supabase: {len(df_match)}")
    print(f"Tickets sem match (ignorados): {len(df_sem_match)}")

    if df_match.empty:
        print("Nada a importar.")
        return

    # Monta payload para upsert em lote
    atualizados = 0
    lote_size   = 500
    updates     = []

    for _, row in df_match.iterrows():
        tid = str(row["ticket_id"])
        updates.append({
            "id":           existentes[tid],
            "ticket_id":    tid,
            "analise_csat": row["analise_csat"] if pd.notna(row["analise_csat"]) else None,
            "oportunidade": row["oportunidade"] if pd.notna(row["oportunidade"]) else None,
            "observacao":   row["observacao"]   if pd.notna(row["observacao"])   else None,
            "status_ctl":   "Feito",
        })

    # Upsert em lotes de 500
    for i in range(0, len(updates), lote_size):
        lote = updates[i:i + lote_size]
        sb.table("ctlloop_analise").upsert(
            lote,
            on_conflict="id",
            ignore_duplicates=False
        ).execute()
        atualizados += len(lote)
        print(f"  {atualizados} atualizados...")

    print(f"=== Concluído: {atualizados} registros importados ===")
    if len(df_sem_match) > 0:
        print(f"Tickets ignorados (não encontrados no Supabase): {len(df_sem_match)}")
        print("Primeiros 10:", df_sem_match["ticket_id"].head(10).tolist())

if __name__ == "__main__":
    importar()
