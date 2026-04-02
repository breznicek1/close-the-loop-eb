"""
sincronizar_dsats.py
Busca DSATs novos na DigitalOcean MySQL e insere na tabela
ctlloop_analise do Supabase como Pendente.
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

QUERY_DSATS = """
SELECT
    t.sequentialId                  AS ticket_id,
    c.ticketId                      AS ticket_ref,
    c.humanConversationEvaluation   AS nota,
    c.humanAgent                    AS agente,
    c.humanServiceChannel           AS canal,
    c.contactName                   AS nome_cliente,
    c.contactPhoneNumber            AS telefone,
    t.storageAt                     AS data_ticket,
    t.team                          AS fila,
    t.tags                          AS tags
FROM estrelabet.conversationLogs c
JOIN estrelabet.ticketsInfo t
    ON t.conversationId = c.id
WHERE
    c.createdAt >= '2025-01-01'
    AND c.hasHumanService = true
    AND c.humanConversationEvaluation IN (1, 2, 3)
    AND t.sequentialId IS NOT NULL
    AND t.tags IS NOT NULL
    AND TRIM(t.tags) != ''
ORDER BY t.storageAt DESC
"""

def depara_subtag(tags: str) -> str:
    if not tags:
        return "#verificar"
    tags_limpa = tags.replace("[", "").replace("]", "").replace('"', "")
    lista = [t.strip() for t in tags_limpa.split(",")]
    if "Perdido" in lista:
        return "Perdido"
    if "inatividade" in lista:
        return "inatividade"
    if lista:
        return lista[0].split("-")[0].strip()
    return "#verificar"

def sincronizar():
    print("=== Sincronização DSATs ===")

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    existentes_res = sb.table("ctlloop_analise").select("ticket_id").execute()
    existentes = {str(r["ticket_id"]) for r in (existentes_res.data or [])}
    print(f"Já existentes no Supabase: {len(existentes)}")

    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        ssl_disabled=False,
        connection_timeout=30,
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(QUERY_DSATS)
    dsats = cursor.fetchall()
    cursor.close()
    conn.close()
    print(f"DSATs na DigitalOcean: {len(dsats)}")

    novos = [d for d in dsats if str(d["ticket_id"]) not in existentes]
    print(f"Novos para inserir: {len(novos)}")

    if not novos:
        print("Nada a sincronizar.")
        return

    inseridos = 0
    lote = []
    for d in novos:
        data_ticket = d["data_ticket"].isoformat() if d["data_ticket"] else None
        lote.append({
            "ticket_id":    str(d["ticket_id"]),
            "ticket_ref":   str(d["ticket_ref"]) if d["ticket_ref"] else None,
            "nota":         int(d["nota"]) if d["nota"] else None,
            "agente":       d["agente"],
            "canal":        d["canal"],
            "nome_cliente": d["nome_cliente"],
            "telefone":     str(d["telefone"]) if d["telefone"] else None,
            "data_ticket":  data_ticket,
            "fila":         d["fila"],
            "assunto":      depara_subtag(d["tags"] or ""),
            "analise_csat": None,
            "oportunidade": None,
            "observacao":   None,
            "status_ctl":   "Pendente",
            "lider":        None,
        })
        if len(lote) >= 100:
            sb.table("ctlloop_analise").insert(lote).execute()
            inseridos += len(lote)
            print(f"  {inseridos} inseridos...")
            lote = []

    if lote:
        sb.table("ctlloop_analise").insert(lote).execute()
        inseridos += len(lote)

    print(f"=== Concluído: {inseridos} novos DSATs inseridos ===")

if __name__ == "__main__":
    sincronizar()
