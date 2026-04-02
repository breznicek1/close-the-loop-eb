"""
backfill_contact_identity.py
Atualiza contact_identity e comentario_cliente nos registros
sem esse campo usando UPDATE em lote via SQL direto no Supabase.
"""

import os
import mysql.connector
from supabase import create_client

MYSQL_HOST = os.environ.get("MYSQL_HOST", "db-mysql-nyc3-40366-do-user-14453107-0.e.db.ondigitalocean.com")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 25060))
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASS = os.environ.get("MYSQL_PASS")
MYSQL_DB   = os.environ.get("MYSQL_DB", "estrelabet")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def buscar_dados_ocean(ticket_ids: list) -> dict:
    if not ticket_ids:
        return {}
    placeholders = ",".join(["%s"] * len(ticket_ids))
    query = f"""
    SELECT
        t.sequentialId             AS ticket_id,
        c.contactIdentity          AS contact_identity,
        c.humanConversationComment AS comentario_cliente
    FROM estrelabet.ticketsInfo t
    JOIN estrelabet.conversationLogs c ON c.id = t.conversationId
    WHERE t.sequentialId IN ({placeholders})
    """
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB, ssl_disabled=False, connection_timeout=30,
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, ticket_ids)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {str(r["ticket_id"]): r for r in rows}

def backfill():
    print("=== Backfill contact_identity + comentario_cliente ===")

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Busca todos sem contact_identity
    todos = []
    offset = 0
    while True:
        res = (
            sb.table("ctlloop_analise")
            .select("id,ticket_id")
            .is_("contact_identity", "null")
            .range(offset, offset + 999)
            .execute()
        )
        if not res.data:
            break
        todos.extend(res.data)
        if len(res.data) < 1000:
            break
        offset += 1000

    print(f"Registros sem contact_identity: {len(todos)}")

    if not todos:
        print("Nada a atualizar.")
        return

    # Processa em lotes de 500 da DigitalOcean
    atualizados = 0
    lote_size = 500

    for i in range(0, len(todos), lote_size):
        lote = todos[i:i + lote_size]
        ticket_ids = [int(r["ticket_id"]) for r in lote if r["ticket_id"]]
        dados = buscar_dados_ocean(ticket_ids)

        # Monta lista para upsert em lote no Supabase
        updates = []
        for reg in lote:
            tid = str(reg["ticket_id"])
            d   = dados.get(tid, {})
            updates.append({
                "id":                 reg["id"],
                "ticket_id":          tid,
                "contact_identity":   d.get("contact_identity"),
                "comentario_cliente": d.get("comentario_cliente"),
            })

        # Upsert em lote — uma única chamada por lote de 500
        sb.table("ctlloop_analise").upsert(
            updates,
            on_conflict="id",
            ignore_duplicates=False
        ).execute()

        atualizados += len(updates)
        print(f"  {atualizados} atualizados...")

    print(f"=== Concluído: {atualizados} registros atualizados ===")

if __name__ == "__main__":
    backfill()
