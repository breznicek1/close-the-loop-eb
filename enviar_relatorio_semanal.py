"""
enviar_relatorio_semanal.py
Envia e-mail toda quinta-feira às 8h BRT com:
- Base CTL do mês em Excel (anexo)
- Principais insights de negócio no corpo do e-mail
Via SendGrid (gratuito até 100 e-mails/dia).
"""

import os
import io
import base64
import json
import urllib.request
import pandas as pd
from datetime import date
from supabase import create_client

# ── CONFIG ────────────────────────────────────────────────────────────────────
SUPABASE_URL   = os.environ.get("SUPABASE_URL")
SUPABASE_KEY   = os.environ.get("SUPABASE_KEY")
SENDGRID_KEY   = os.environ.get("SENDGRID_KEY")
EMAIL_FROM     = os.environ.get("EMAIL_FROM", "bruno.machado@i9xc.com")
EMAIL_TO       = os.environ.get("EMAIL_TO")

# ── BUSCA DADOS ───────────────────────────────────────────────────────────────
def buscar_dados():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    todos = []
    offset = 0
    while True:
        res = sb.table("ctlloop_analise").select("*").range(offset, offset + 999).execute()
        if not res.data:
            break
        todos.extend(res.data)
        if len(res.data) < 1000:
            break
        offset += 1000
    return pd.DataFrame(todos) if todos else pd.DataFrame()

def depara_fila(team, contact_identity) -> str:
    t = str(team             or "").upper()
    i = str(contact_identity or "").lower()
    if "VIP" in t:         return "VIP"
    if "suportevup" in i:  return "VUPI"
    if "suporteprd1" in i: return "Core"
    if "ura" in i:         return "URA"
    return "Outros"

def limpar_agente(raw) -> str:
    raw = str(raw or "")
    if not raw or raw in ("None", "nan"):
        return "—"
    if "%40" in raw:
        raw = raw.split("%40")[0]
    if "@" in raw:
        raw = raw.split("@")[0]
    return raw.replace(".", " ").title()

# ── GERA EXCEL ────────────────────────────────────────────────────────────────
def gerar_excel(df):
    cols_map = {
        "ticket_id":   "Ticket",
        "data_ticket": "Data",
        "depara_fila": "Fila",
        "agente_nome": "Agente",
        "assunto":     "Assunto",
        "nota":        "Nota",
        "status_ctl":  "Status",
        "analise_csat":"Análise CSAT",
        "oportunidade":"Oportunidade",
        "observacao":  "Observação",
        "lider":       "Analisado por",
        "updated_at":  "Data/Hora Análise",
    }
    cols = [c for c in cols_map if c in df.columns]
    out  = df[cols].copy()
    out["data_ticket"] = pd.to_datetime(out["data_ticket"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "updated_at" in out.columns:
        out["updated_at"] = pd.to_datetime(out["updated_at"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    out.columns = [cols_map[c] for c in cols]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        out.to_excel(w, index=False, sheet_name="CTL do Mês")
    return buf.getvalue()

# ── GERA INSIGHTS HTML ────────────────────────────────────────────────────────
def gerar_insights(df, df_mes):
    hoje        = date.today()
    ini_sem_a   = hoje - pd.Timedelta(days=hoje.weekday())
    ini_sem_ant = ini_sem_a - pd.Timedelta(weeks=1)
    fim_sem_ant = ini_sem_a - pd.Timedelta(days=1)

    df["data_dt"] = pd.to_datetime(df["data_ticket"], errors="coerce").dt.date

    sem_a   = df[df["data_dt"] >= ini_sem_a]
    sem_ant = df[(df["data_dt"] >= ini_sem_ant) & (df["data_dt"] <= fim_sem_ant)]

    def resumo(d):
        total = len(d)
        feito = len(d[d["status_ctl"] == "Feito"])
        pct   = round(feito / total * 100, 1) if total > 0 else 0
        return total, feito, pct

    t_a,   f_a,   p_a   = resumo(sem_a)
    t_ant, f_ant, p_ant = resumo(sem_ant)
    t_mes, f_mes, p_mes = resumo(df_mes)

    delta_t = t_a - t_ant
    delta_f = f_a - f_ant
    delta_p = round(p_a - p_ant, 1)

    top_oport = df_mes[df_mes["status_ctl"] == "Feito"]["oportunidade"].value_counts().head(5)

    op  = df_mes.groupby("agente_nome").size().reset_index(name="DSATs")
    ofe = df_mes[df_mes["status_ctl"]=="Feito"].groupby("agente_nome").size().reset_index(name="Feitos")
    op  = op.merge(ofe, on="agente_nome", how="left").fillna(0)
    op["Feitos"] = op["Feitos"].astype(int)
    op["pct"]    = (op["Feitos"] / op["DSATs"] * 100).round(1)
    ofensores  = op[op["DSATs"] >= 3].sort_values("pct").head(3)
    destaques  = op[op["DSATs"] >= 3].sort_values("pct", ascending=False).head(3)

    csat = df_mes[df_mes["status_ctl"]=="Feito"]["analise_csat"].value_counts()

    seta = lambda v: "▲" if v > 0 else ("▼" if v < 0 else "—")

    html = f"""
<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:auto;color:#333">

<div style="background:#1F4E8C;padding:20px;border-radius:8px 8px 0 0">
  <h1 style="color:white;margin:0;font-size:20px">🔁 Close the Loop — EstrelaBet</h1>
  <p style="color:#B5D4F4;margin:4px 0 0">Relatório Semanal — {hoje.strftime('%d/%m/%Y')}</p>
</div>

<div style="background:#F5F5F5;padding:16px;border-radius:0 0 8px 8px">

  <h2 style="color:#1F4E8C;border-bottom:2px solid #1F4E8C;padding-bottom:6px">📆 Resumo do mês</h2>
  <table style="width:100%;border-collapse:collapse">
    <tr style="background:#D6E4F0">
      <th style="padding:10px;text-align:left">Métrica</th>
      <th style="padding:10px;text-align:center">Valor</th>
    </tr>
    <tr><td style="padding:8px">Total DSATs</td><td style="text-align:center"><b>{t_mes}</b></td></tr>
    <tr style="background:#EEF4FB"><td style="padding:8px">CTL Feitos</td><td style="text-align:center"><b>{f_mes}</b></td></tr>
    <tr><td style="padding:8px">% CTL</td><td style="text-align:center"><b>{p_mes}%</b></td></tr>
  </table>

  <h2 style="color:#1F4E8C;border-bottom:2px solid #1F4E8C;padding-bottom:6px;margin-top:24px">📅 Comparativo semanal</h2>
  <table style="width:100%;border-collapse:collapse">
    <tr style="background:#D6E4F0">
      <th style="padding:10px;text-align:left">Métrica</th>
      <th style="padding:10px;text-align:center">Semana atual</th>
      <th style="padding:10px;text-align:center">Semana anterior</th>
      <th style="padding:10px;text-align:center">Variação</th>
    </tr>
    <tr>
      <td style="padding:8px">DSATs</td>
      <td style="text-align:center">{t_a}</td>
      <td style="text-align:center">{t_ant}</td>
      <td style="text-align:center">{seta(delta_t)} {abs(delta_t)}</td>
    </tr>
    <tr style="background:#EEF4FB">
      <td style="padding:8px">CTL Feitos</td>
      <td style="text-align:center">{f_a}</td>
      <td style="text-align:center">{f_ant}</td>
      <td style="text-align:center">{seta(delta_f)} {abs(delta_f)}</td>
    </tr>
    <tr>
      <td style="padding:8px">% CTL</td>
      <td style="text-align:center">{p_a}%</td>
      <td style="text-align:center">{p_ant}%</td>
      <td style="text-align:center">{seta(delta_p)} {abs(delta_p)}pp</td>
    </tr>
  </table>

  <h2 style="color:#1F4E8C;border-bottom:2px solid #1F4E8C;padding-bottom:6px;margin-top:24px">📊 Análise CSAT do mês</h2>
  <table style="width:60%;border-collapse:collapse">
    <tr style="background:#D6E4F0">
      <th style="padding:10px;text-align:left">Categoria</th>
      <th style="padding:10px;text-align:center">Qtd</th>
      <th style="padding:10px;text-align:center">%</th>
    </tr>"""

    cores = {"Cliente Discorda": "#378ADD", "EstrelaBet": "#EF9F27", "Inove": "#E24B4A"}
    for i, (cat, qtd) in enumerate(csat.items()):
        pct_c = round(qtd / f_mes * 100, 1) if f_mes > 0 else 0
        cor   = cores.get(cat, "#333")
        bg    = "#EEF4FB" if i % 2 else "white"
        html += f"""
    <tr style="background:{bg}">
      <td style="padding:8px;color:{cor}"><b>{cat}</b></td>
      <td style="text-align:center">{qtd}</td>
      <td style="text-align:center">{pct_c}%</td>
    </tr>"""

    html += "</table>"

    if not top_oport.empty:
        html += """
  <h2 style="color:#1F4E8C;border-bottom:2px solid #1F4E8C;padding-bottom:6px;margin-top:24px">🎯 Top oportunidades do mês</h2>
  <ol>"""
        for o, q in top_oport.items():
            label = str(o).replace("EstrelaBet - ","").replace("Inove - ","").replace("Cliente Frustrado – ","")
            html += f"<li>{label}: <b>{q}</b></li>"
        html += "</ol>"

    if not ofensores.empty:
        html += """
  <h2 style="color:#A32D2D;border-bottom:2px solid #E24B4A;padding-bottom:6px;margin-top:24px">🔴 Ofensores (menor % CTL — mín. 3 DSATs)</h2>
  <table style="width:80%;border-collapse:collapse">
    <tr style="background:#FCE4E4">
      <th style="padding:10px;text-align:left">Agente</th>
      <th style="padding:10px;text-align:center">DSATs</th>
      <th style="padding:10px;text-align:center">CTL Feito</th>
      <th style="padding:10px;text-align:center">% CTL</th>
    </tr>"""
        for i, (_, r) in enumerate(ofensores.iterrows()):
            bg = "#FFF0F0" if i % 2 else "white"
            html += f"""
    <tr style="background:{bg}">
      <td style="padding:8px">{r['agente_nome']}</td>
      <td style="text-align:center">{int(r['DSATs'])}</td>
      <td style="text-align:center">{int(r['Feitos'])}</td>
      <td style="text-align:center"><b>{r['pct']}%</b></td>
    </tr>"""
        html += "</table>"

    if not destaques.empty:
        html += """
  <h2 style="color:#1D6E4A;border-bottom:2px solid #1D9E75;padding-bottom:6px;margin-top:24px">🟢 Destaques (maior % CTL — mín. 3 DSATs)</h2>
  <table style="width:80%;border-collapse:collapse">
    <tr style="background:#E8F5EE">
      <th style="padding:10px;text-align:left">Agente</th>
      <th style="padding:10px;text-align:center">DSATs</th>
      <th style="padding:10px;text-align:center">CTL Feito</th>
      <th style="padding:10px;text-align:center">% CTL</th>
    </tr>"""
        for i, (_, r) in enumerate(destaques.iterrows()):
            bg = "#F0FAF5" if i % 2 else "white"
            html += f"""
    <tr style="background:{bg}">
      <td style="padding:8px">{r['agente_nome']}</td>
      <td style="text-align:center">{int(r['DSATs'])}</td>
      <td style="text-align:center">{int(r['Feitos'])}</td>
      <td style="text-align:center"><b>{r['pct']}%</b></td>
    </tr>"""
        html += "</table>"

    html += f"""
  <br>
  <p style="color:#888;font-size:12px;border-top:1px solid #ddd;padding-top:12px">
    Relatório automático gerado toda quinta-feira às 8h BRT<br>
    Close the Loop EB — i9xc.com
  </p>
</div>
</body></html>"""

    return html

# ── ENVIA VIA SENDGRID ────────────────────────────────────────────────────────
def enviar_sendgrid(destinatarios, assunto, html_body, excel_bytes, nome_anexo):
    anexo_b64 = base64.b64encode(excel_bytes).decode()

    payload = {
        "personalizations": [{"to": [{"email": e.strip()} for e in destinatarios]}],
        "from": {"email": EMAIL_FROM, "name": "Close the Loop EB"},
        "subject": assunto,
        "content": [{"type": "text/html", "value": html_body}],
        "attachments": [{
            "content":     anexo_b64,
            "type":        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "filename":    nome_anexo,
            "disposition": "attachment"
        }]
    }

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=data,
        headers={
            "Authorization": f"Bearer {SENDGRID_KEY}",
            "Content-Type":  "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        print(f"SendGrid status: {resp.status}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def enviar():
    print("=== Relatório Semanal CTL ===")

    df = buscar_dados()
    if df.empty:
        print("Sem dados.")
        return

    df["agente_nome"] = df["agente"].apply(limpar_agente)
    df["depara_fila"] = df.apply(lambda r: depara_fila(r.get("fila"), r.get("contact_identity")), axis=1)
    df["data_ticket"] = pd.to_datetime(df["data_ticket"], errors="coerce")

    hoje    = date.today()
    ini_mes = date(hoje.year, hoje.month, 1)
    df_mes  = df[df["data_ticket"].dt.date >= ini_mes].copy()
    print(f"Registros do mês: {len(df_mes)}")

    excel_bytes = gerar_excel(df_mes[df_mes["status_ctl"] == "Feito"].copy())
    html_body   = gerar_insights(df, df_mes)
    nome_anexo  = f"ctl_mes_{hoje.strftime('%Y_%m')}.xlsx"
    assunto     = f"Close the Loop EB — Relatório Semanal {hoje.strftime('%d/%m/%Y')}"
    destinatarios = [e.strip() for e in EMAIL_TO.split(",")]

    enviar_sendgrid(destinatarios, assunto, html_body, excel_bytes, nome_anexo)
    print(f"E-mail enviado para: {EMAIL_TO}")
    print("=== Concluído ===")

if __name__ == "__main__":
    enviar()
