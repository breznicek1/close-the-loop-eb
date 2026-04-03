"""
enviar_relatorio_semanal.py
Envia e-mail toda quinta-feira às 8h BRT com:
- Base CTL do mês em Excel (anexo)
- Principais insights de negócio no corpo do e-mail
Via Outlook SMTP corporativo.
"""

import os
import io
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from supabase import create_client
from datetime import date, datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
SUPABASE_URL  = os.environ.get("SUPABASE_URL")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY")
EMAIL_USER    = os.environ.get("EMAIL_USER")    # ex: bruno.machado@i9xc.com
EMAIL_PASS    = os.environ.get("EMAIL_PASS")    # senha ou app password
EMAIL_TO      = os.environ.get("EMAIL_TO")      # destinatários separados por vírgula
SMTP_HOST     = os.environ.get("SMTP_HOST", "smtp.office365.com")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", 587))

# ── BUSCA DADOS ───────────────────────────────────────────────────────────────
def buscar_dados():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    todos = []
    offset = 0
    while True:
        res = (
            sb.table("ctlloop_analise")
            .select("*")
            .range(offset, offset + 999)
            .execute()
        )
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

# ── GERA INSIGHTS ─────────────────────────────────────────────────────────────
def gerar_insights(df, df_mes):
    hoje       = date.today()
    ini_sem_a  = hoje - pd.Timedelta(days=hoje.weekday())
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

    t_a, f_a, p_a     = resumo(sem_a)
    t_ant, f_ant, p_ant = resumo(sem_ant)
    t_mes, f_mes, p_mes = resumo(df_mes)

    delta_t = t_a - t_ant
    delta_f = f_a - f_ant
    delta_p = round(p_a - p_ant, 1)

    # Top oportunidades do mês
    top_oport = (
        df_mes[df_mes["status_ctl"] == "Feito"]["oportunidade"]
        .value_counts().head(5)
    )

    # Ofensores (mín 3 DSATs, menor % CTL)
    op = df_mes.groupby("agente_nome").size().reset_index(name="DSATs")
    of = df_mes[df_mes["status_ctl"]=="Feito"].groupby("agente_nome").size().reset_index(name="Feitos")
    op = op.merge(of, on="agente_nome", how="left").fillna(0)
    op["Feitos"] = op["Feitos"].astype(int)
    op["pct"] = (op["Feitos"] / op["DSATs"] * 100).round(1)
    ofensores  = op[op["DSATs"] >= 3].sort_values("pct").head(3)
    destaques  = op[op["DSATs"] >= 3].sort_values("pct", ascending=False).head(3)

    # CSAT breakdown mês
    csat = df_mes[df_mes["status_ctl"]=="Feito"]["analise_csat"].value_counts()

    lines = []
    lines.append(f"<h2 style='color:#1F4E8C'>📊 Relatório CTL — Semana {hoje.strftime('%d/%m/%Y')}</h2>")
    lines.append(f"<p>Olá! Segue o resumo semanal do Close the Loop EstrelaBet.</p>")

    lines.append("<h3 style='color:#1F4E8C'>📅 Comparativo semanal</h3>")
    lines.append("<table style='border-collapse:collapse;width:100%'>")
    lines.append("<tr style='background:#D6E4F0'><th style='padding:8px;text-align:left'>Métrica</th><th>Semana atual</th><th>Semana anterior</th><th>Variação</th></tr>")
    lines.append(f"<tr><td style='padding:6px'>DSATs</td><td style='text-align:center'>{t_a}</td><td style='text-align:center'>{t_ant}</td><td style='text-align:center'>{'▲' if delta_t>0 else '▼'} {abs(delta_t)}</td></tr>")
    lines.append(f"<tr style='background:#F5F5F5'><td style='padding:6px'>CTL Feitos</td><td style='text-align:center'>{f_a}</td><td style='text-align:center'>{f_ant}</td><td style='text-align:center'>{'▲' if delta_f>0 else '▼'} {abs(delta_f)}</td></tr>")
    lines.append(f"<tr><td style='padding:6px'>% CTL</td><td style='text-align:center'>{p_a}%</td><td style='text-align:center'>{p_ant}%</td><td style='text-align:center'>{'▲' if delta_p>0 else '▼'} {abs(delta_p)}pp</td></tr>")
    lines.append("</table>")

    lines.append("<h3 style='color:#1F4E8C'>📆 Resumo do mês</h3>")
    lines.append(f"<p>Total DSATs: <b>{t_mes}</b> | CTL Feitos: <b>{f_mes}</b> | % CTL: <b>{p_mes}%</b></p>")
    lines.append("<table style='border-collapse:collapse;width:60%'>")
    lines.append("<tr style='background:#D6E4F0'><th style='padding:8px;text-align:left'>Análise CSAT</th><th>Qtd</th><th>%</th></tr>")
    for cat, qtd in csat.items():
        pct_c = round(qtd / f_mes * 100, 1) if f_mes > 0 else 0
        cor   = "#378ADD" if cat == "Cliente Discorda" else "#EF9F27" if cat == "EstrelaBet" else "#E24B4A"
        lines.append(f"<tr><td style='padding:6px;color:{cor}'><b>{cat}</b></td><td style='text-align:center'>{qtd}</td><td style='text-align:center'>{pct_c}%</td></tr>")
    lines.append("</table>")

    if not top_oport.empty:
        lines.append("<h3 style='color:#1F4E8C'>🎯 Top oportunidades do mês</h3><ol>")
        for o, q in top_oport.items():
            label = str(o).replace("EstrelaBet - ","").replace("Inove - ","").replace("Cliente Frustrado – ","")
            lines.append(f"<li>{label}: <b>{q}</b></li>")
        lines.append("</ol>")

    if not ofensores.empty:
        lines.append("<h3 style='color:#E24B4A'>🔴 Ofensores (menor % CTL — mín. 3 DSATs)</h3>")
        lines.append("<table style='border-collapse:collapse;width:80%'>")
        lines.append("<tr style='background:#FCE4E4'><th style='padding:8px;text-align:left'>Agente</th><th>DSATs</th><th>CTL Feito</th><th>% CTL</th></tr>")
        for _, r in ofensores.iterrows():
            lines.append(f"<tr><td style='padding:6px'>{r['agente_nome']}</td><td style='text-align:center'>{int(r['DSATs'])}</td><td style='text-align:center'>{int(r['Feitos'])}</td><td style='text-align:center'>{r['pct']}%</td></tr>")
        lines.append("</table>")

    if not destaques.empty:
        lines.append("<h3 style='color:#1D6E4A'>🟢 Destaques (maior % CTL — mín. 3 DSATs)</h3>")
        lines.append("<table style='border-collapse:collapse;width:80%'>")
        lines.append("<tr style='background:#E8F5EE'><th style='padding:8px;text-align:left'>Agente</th><th>DSATs</th><th>CTL Feito</th><th>% CTL</th></tr>")
        for _, r in destaques.iterrows():
            lines.append(f"<tr><td style='padding:6px'>{r['agente_nome']}</td><td style='text-align:center'>{int(r['DSATs'])}</td><td style='text-align:center'>{int(r['Feitos'])}</td><td style='text-align:center'>{r['pct']}%</td></tr>")
        lines.append("</table>")

    lines.append("<br><p style='color:#888;font-size:12px'>Relatório automático — Close the Loop EB | i9xc.com</p>")
    return "\n".join(lines)

# ── ENVIA E-MAIL ──────────────────────────────────────────────────────────────
def enviar():
    print("=== Relatório Semanal CTL ===")

    df = buscar_dados()
    if df.empty:
        print("Sem dados.")
        return

    df["agente_nome"] = df["agente"].apply(limpar_agente)
    df["depara_fila"] = df.apply(lambda r: depara_fila(r.get("fila"), r.get("contact_identity")), axis=1)
    df["data_ticket"] = pd.to_datetime(df["data_ticket"], errors="coerce")

    # Filtra mês atual
    hoje = date.today()
    ini_mes = date(hoje.year, hoje.month, 1)
    df_mes  = df[df["data_ticket"].dt.date >= ini_mes].copy()
    print(f"Registros do mês: {len(df_mes)}")

    excel_bytes = gerar_excel(df_mes[df_mes["status_ctl"] == "Feito"].copy())
    html_body   = gerar_insights(df, df_mes)

    # Monta e-mail
    msg = MIMEMultipart("mixed")
    msg["From"]    = EMAIL_USER
    msg["To"]      = EMAIL_TO
    msg["Subject"] = f"Close the Loop EB — Relatório Semanal {hoje.strftime('%d/%m/%Y')}"

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Anexo Excel
    part = MIMEBase("application", "octet-stream")
    part.set_payload(excel_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="ctl_mes_{hoje.strftime("%Y_%m")}.xlsx"')
    msg.attach(part)

    # Envia via SMTP Outlook
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        destinatarios = [e.strip() for e in EMAIL_TO.split(",")]
        server.sendmail(EMAIL_USER, destinatarios, msg.as_string())

    print(f"E-mail enviado para: {EMAIL_TO}")
    print("=== Concluído ===")

if __name__ == "__main__":
    enviar()
