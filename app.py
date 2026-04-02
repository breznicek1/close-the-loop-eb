import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import date, timedelta
import io

# ── CONFIG ────────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

USUARIOS = {
    "gestao": {"senha": "ctl2026",    "lider": "Geral"},
    "admin":  {"senha": "Henry@2026", "lider": "Admin"},
}

OPCOES_CSAT   = ["Cliente Discorda", "EstrelaBet", "Inove"]
OPCOES_STATUS = ["Pendente", "Feito"]
NOTAS_EMOJI   = {1: "⭐ 1", 2: "⭐ 2", 3: "⭐ 3", 4: "⭐ 4", 5: "⭐ 5"}

CORES_CSAT = {
    "Cliente Discorda": "#378ADD",
    "EstrelaBet":       "#EF9F27",
    "Inove":            "#E24B4A",
}

OPCOES_OPORTUNIDADE = [
    "",
    "EstrelaBet - Bônus - Não Creditado",
    "EstrelaBet - Bônus - Ganho Maximo",
    "EstrelaBet - Bônus - App Dentro do prazo",
    "EstrelaBet - Bônus - App Fora do prazo",
    "EstrelaBet - Bônus - Cashout",
    "EstrelaBet - Bônus - Vencido",
    "EstrelaBet - Bônus - Aposta Devolvida/Adiada",
    "EstrelaBet - Bônus - Roleta Gratis",
    "EstrelaBet - Bônus - Roleta Gratis (FRAUDE)",
    "EstrelaBet - N2 - Fora do prazo",
    "EstrelaBet - N2 - Resposta não resolutiva",
    "EstrelaBet - N2 - Não concorda com o prazo",
    "EstrelaBet - SB - Recalculo de odd",
    "EstrelaBet - SB - Aposta Devolvida",
    "EstrelaBet - SB - Limitação Alternar",
    "EstrelaBet - SB - Rollback",
    "EstrelaBet - VIP - Quero bônus",
    "EstrelaBet - Site - Cadastro de endereço",
    "EstrelaBet - Site - Jogos fora do ar",
    "EstrelaBet - Site - Instabilidade de Login",
    "EstrelaBet - APP - Jogos fora do ar",
    "EstrelaBet - APP - Instabilidade de Login",
    "EstrelaBet - KYC - Erro KYC",
    "EstrelaBet - Saque - Co_post_start",
    "EstrelaBet - Saque - Chave Pix banco lista restritiva",
    "EstrelaBet - Saque - Excedeu Limite Diario",
    "EstrelaBet - Saque - Alteração chave PIX",
    "EstrelaBet - Closed - Ludopatia",
    "EstrelaBet - Closed - Abuso de Bonus",
    "EstrelaBet - Encerramento - Desrespeito",
    "EstrelaBet - BLIP - Avaliação indevida - Blip Registrou Nota Errada",
    "EstrelaBet - BLIP - Avaliação indevida - Cliente Clicou Errado",
    "EstrelaBet - Site - Sistema Estrela Fora do Ar",
    "EstrelaBet - Site - Bloqueio de Saque Nacional",
    "Inove - Postura",
    "Inove - Condução",
    "Inove - Encerramento",
    "Inove - Dominio Fluxo",
    "Cliente Frustrado – Resistência a Prazos Operacionais",
    "Cliente Frustrado – Discordância da Análise (Sem Fundamentação Clara)",
    "Cliente Frustrado – Negativa de Bônus",
    "Cliente Frustrado – Negativa de Reembolso por Perda",
    "Cliente Frustrado – Discordância das Regras de Aposta",
    "Cliente Frustrado – Avaliação Negativa por Tempo de Retorno no Chat",
    "Cliente Frustrado – Cliente Recorrente / Contumaz",
    "Cliente Frustrado BLIP - Avaliação dada para retorno ao chat após inatividade",
    "Cliente Frustrado – Discordancia do processos operacionais",
]

# ── HELPERS ───────────────────────────────────────────────────────────────────
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

def limpar_data(val) -> str:
    s = str(val or "")
    return "—" if s in ("", "None", "nan", "NaT") else s[:10]

def nota_str(val) -> str:
    try:
        return NOTAS_EMOJI.get(int(val), f"⭐ {val}") if pd.notna(val) and val else "—"
    except:
        return "—"

# ── SUPABASE ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=300)
def carregar_fila():
    sb     = get_client()
    todos  = []
    chunk  = 1000
    offset = 0
    while True:
        res = (
            sb.table("ctlloop_analise")
            .select("*")
            .order("data_ticket", desc=True)
            .range(offset, offset + chunk - 1)
            .execute()
        )
        if not res.data:
            break
        todos.extend(res.data)
        if len(res.data) < chunk:
            break
        offset += chunk

    if not todos:
        return pd.DataFrame()

    df = pd.DataFrame(todos)
    df["depara_fila"] = df.apply(
        lambda r: depara_fila(r.get("fila"), r.get("contact_identity")), axis=1
    )
    df["data_ticket"] = pd.to_datetime(df["data_ticket"], errors="coerce")
    df["agente_nome"] = df["agente"].apply(limpar_agente)
    return df

def atualizar_analise(id_registro, analise_csat, oportunidade, observacao, status_ctl, lider):
    get_client().table("ctlloop_analise").update({
        "analise_csat": analise_csat,
        "oportunidade": oportunidade,
        "observacao":   observacao,
        "status_ctl":   status_ctl,
        "lider":        lider,
    }).eq("id", id_registro).execute()
    st.cache_data.clear()

# ── LOGIN ─────────────────────────────────────────────────────────────────────
def tela_login():
    st.title("Close the Loop — EstrelaBet")
    st.markdown("---")
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.subheader("Entrar")
        usuario = st.text_input("Usuário").strip().lower()
        senha   = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
                st.session_state.update({
                    "logado":  True,
                    "usuario": usuario,
                    "lider":   USUARIOS[usuario]["lider"],
                })
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# ── FILTROS COMUNS ────────────────────────────────────────────────────────────
def filtros_data_sidebar(key_prefix=""):
    st.sidebar.markdown("### Filtros")
    data_ini = st.sidebar.date_input("Data início", value=date.today() - timedelta(days=30), key=f"{key_prefix}_ini")
    data_fim = st.sidebar.date_input("Data fim",    value=date.today(), key=f"{key_prefix}_fim")
    return data_ini, data_fim

# ── PÁGINA: DASHBOARD ─────────────────────────────────────────────────────────
def pagina_dashboard():
    st.title("Dashboard — Close the Loop EB")

    # Filtros no sidebar
    st.sidebar.markdown("### Filtros")
    data_ini  = st.sidebar.date_input("Data início", value=date.today() - timedelta(days=30), key="dash_ini")
    data_fim  = st.sidebar.date_input("Data fim",    value=date.today(), key="dash_fim")
    filtro_fila = st.sidebar.multiselect("Fila", ["Core", "VIP", "VUPI", "URA", "Outros"], default=[])

    df_full = carregar_fila()
    if df_full.empty:
        st.info("Nenhum dado disponível.")
        return

    # Aplica filtros de data
    df = df_full[
        (df_full["data_ticket"].dt.date >= data_ini) &
        (df_full["data_ticket"].dt.date <= data_fim)
    ].copy()

    if filtro_fila:
        df = df[df["depara_fila"].isin(filtro_fila)]

    df_feito    = df[df["status_ctl"] == "Feito"]
    total       = len(df)
    feitos      = len(df_feito)
    pendentes   = total - feitos
    pct_feito   = round(feitos / total * 100, 1) if total > 0 else 0

    # ── MÉTRICAS TOPO ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total DSATs",   total)
    c2.metric("CTL Feitos",    feitos)
    c3.metric("% Feito",       f"{pct_feito}%")
    c4.metric("Pendentes",     pendentes)

    # Oportunidade EstrelaBet
    qtd_eb   = len(df_feito[df_feito["analise_csat"] == "EstrelaBet"])
    pct_eb   = round(qtd_eb / feitos * 100, 1) if feitos > 0 else 0
    c5.metric("Oport. EB",     f"{qtd_eb} ({pct_eb}%)")

    st.markdown("---")

    # ── LINHA 1: Donut CSAT + Barras por Fila ──────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Resumo Geral — Análise CSAT")
        csat_counts = df_feito["analise_csat"].value_counts().reset_index()
        csat_counts.columns = ["Análise", "Qtd"]
        if not csat_counts.empty:
            fig = px.pie(
                csat_counts, values="Qtd", names="Análise",
                hole=0.55,
                color="Análise",
                color_discrete_map=CORES_CSAT,
            )
            fig.update_traces(textposition="outside", textinfo="label+percent+value")
            fig.update_layout(showlegend=True, margin=dict(t=20, b=20), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de análise CSAT no período.")

    with col2:
        st.subheader("DSATs e CTL por Fila")
        fila_total = df.groupby("depara_fila").size().reset_index(name="Total DSATs")
        fila_feito = df_feito.groupby("depara_fila").size().reset_index(name="CTL Feitos")
        fila_merge = fila_total.merge(fila_feito, on="depara_fila", how="left").fillna(0)
        fila_merge["CTL Feitos"] = fila_merge["CTL Feitos"].astype(int)
        fila_merge["% Feito"] = (fila_merge["CTL Feitos"] / fila_merge["Total DSATs"] * 100).round(1)
        fila_merge = fila_merge.sort_values("Total DSATs", ascending=False)

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="Total DSATs", x=fila_merge["depara_fila"], y=fila_merge["Total DSATs"], marker_color="#B5D4F4"))
        fig2.add_trace(go.Bar(name="CTL Feitos",  x=fila_merge["depara_fila"], y=fila_merge["CTL Feitos"],  marker_color="#1D9E75"))
        fig2.update_layout(barmode="group", height=320, margin=dict(t=20, b=20), legend=dict(orientation="h"))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── LINHA 2: Evolução semanal + % por Líder ────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Evolução Semanal — CTL Feitos")
        df_feito_copy = df_feito.copy()
        df_feito_copy["semana"] = df_feito_copy["data_ticket"].dt.to_period("W").dt.start_time
        evolucao = df_feito_copy.groupby(["semana", "analise_csat"]).size().reset_index(name="Qtd")
        evolucao["semana"] = evolucao["semana"].dt.strftime("%d/%m")
        if not evolucao.empty:
            fig3 = px.bar(
                evolucao, x="semana", y="Qtd", color="analise_csat",
                color_discrete_map=CORES_CSAT,
                labels={"semana": "Semana", "Qtd": "Qtd", "analise_csat": "Análise"},
            )
            fig3.update_layout(height=320, margin=dict(t=20, b=20), legend=dict(orientation="h"))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sem dados no período.")

    with col4:
        st.subheader("Abertura por Líder")
        if "lider" in df_feito.columns:
            lider_csat = df_feito[df_feito["lider"].notna()].groupby(["lider", "analise_csat"]).size().reset_index(name="Qtd")
            lider_total = lider_csat.groupby("lider")["Qtd"].sum().reset_index(name="Total")
            lider_csat = lider_csat.merge(lider_total, on="lider")
            lider_csat["pct"] = (lider_csat["Qtd"] / lider_csat["Total"] * 100).round(1)
            lider_csat = lider_csat.sort_values("Total", ascending=True)
            if not lider_csat.empty:
                fig4 = px.bar(
                    lider_csat, x="pct", y="lider", color="analise_csat",
                    orientation="h",
                    color_discrete_map=CORES_CSAT,
                    labels={"pct": "%", "lider": "Líder", "analise_csat": "Análise"},
                )
                fig4.update_layout(height=320, margin=dict(t=20, b=20), legend=dict(orientation="h"), barmode="stack")
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("Sem dados de líder no período.")

    st.markdown("---")

    # ── LINHA 3: Top Oportunidades + Abertura por Nota ─────────────────────
    col5, col6 = st.columns(2)

    with col5:
        st.subheader("Top Oportunidades")
        oport = df_feito[df_feito["oportunidade"].notna() & (df_feito["oportunidade"] != "")]
        oport_counts = oport["oportunidade"].value_counts().head(15).reset_index()
        oport_counts.columns = ["Oportunidade", "Qtd"]
        oport_counts["Oportunidade_curta"] = oport_counts["Oportunidade"].str.replace(r"^(EstrelaBet|Inove|Cliente Frustrado)\s*[-–]\s*", "", regex=True)
        if not oport_counts.empty:
            fig5 = px.bar(
                oport_counts.sort_values("Qtd"), x="Qtd", y="Oportunidade_curta",
                orientation="h",
                color_discrete_sequence=["#7F77DD"],
                labels={"Qtd": "Qtd", "Oportunidade_curta": ""},
            )
            fig5.update_layout(height=420, margin=dict(t=20, b=20, l=10))
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Sem oportunidades registradas no período.")

    with col6:
        st.subheader("DSATs por Nota")
        nota_counts = df["nota"].value_counts().sort_index().reset_index()
        nota_counts.columns = ["Nota", "Qtd"]
        nota_counts["Nota"] = nota_counts["Nota"].apply(lambda x: f"Nota {int(x)}" if pd.notna(x) else "—")
        fig6 = px.bar(
            nota_counts, x="Nota", y="Qtd",
            color_discrete_sequence=["#D85A30"],
            labels={"Qtd": "Quantidade"},
        )
        fig6.update_layout(height=200, margin=dict(t=20, b=20))
        st.plotly_chart(fig6, use_container_width=True)

        st.subheader("CTL por Assunto (Top 10)")
        assunto_counts = df_feito["assunto"].value_counts().head(10).reset_index()
        assunto_counts.columns = ["Assunto", "Qtd"]
        fig7 = px.bar(
            assunto_counts.sort_values("Qtd"), x="Qtd", y="Assunto",
            orientation="h",
            color_discrete_sequence=["#1D9E75"],
            labels={"Qtd": "Qtd", "Assunto": ""},
        )
        fig7.update_layout(height=260, margin=dict(t=10, b=10, l=10))
        st.plotly_chart(fig7, use_container_width=True)

    st.markdown("---")

    # ── LINHA 4: Tabela de operadores + Extração ───────────────────────────
    st.subheader("Abertura por Operador")
    op_total = df.groupby("agente_nome").size().reset_index(name="Qtd DSAT")
    op_feito = df_feito.groupby("agente_nome").size().reset_index(name="Qtd CTL Feito")
    op_merge = op_total.merge(op_feito, on="agente_nome", how="left").fillna(0)
    op_merge["Qtd CTL Feito"] = op_merge["Qtd CTL Feito"].astype(int)
    op_merge["% Feito"] = (op_merge["Qtd CTL Feito"] / op_merge["Qtd DSAT"] * 100).round(1).astype(str) + "%"

    # CSAT breakdown
    for cat in ["Cliente Discorda", "EstrelaBet", "Inove"]:
        sub = df_feito[df_feito["analise_csat"] == cat].groupby("agente_nome").size().reset_index(name=f"Qtd {cat}")
        op_merge = op_merge.merge(sub, on="agente_nome", how="left").fillna(0)
        op_merge[f"Qtd {cat}"] = op_merge[f"Qtd {cat}"].astype(int)

    op_merge = op_merge.sort_values("Qtd DSAT", ascending=False)
    op_merge.columns = ["Agente", "Qtd DSAT", "Qtd CTL Feito", "% Feito", "Cliente Discorda", "EstrelaBet", "Inove"]
    st.dataframe(op_merge, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── EXTRAÇÃO ────────────────────────────────────────────────────────────
    st.subheader("Extrair dados")
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        # Export tabela filtrada
        df_export = df_feito[[
            "ticket_id", "data_ticket", "depara_fila", "agente_nome",
            "assunto", "nota", "analise_csat", "oportunidade",
            "observacao", "comentario_cliente", "lider"
        ]].copy()
        df_export["data_ticket"] = df_export["data_ticket"].dt.strftime("%Y-%m-%d")
        df_export.columns = [
            "Ticket", "Data", "Fila", "Agente", "Assunto", "Nota",
            "Análise CSAT", "Oportunidade", "Observação", "Voz do Cliente", "Líder"
        ]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="CTL Feitos")
        st.download_button(
            "⬇️ Exportar CTL Feitos (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"ctl_feitos_{data_ini}_{data_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col_exp2:
        # Export todos (incluindo pendentes)
        df_export_all = df[[
            "ticket_id", "data_ticket", "depara_fila", "agente_nome",
            "assunto", "nota", "status_ctl", "analise_csat", "oportunidade",
            "observacao", "comentario_cliente", "lider"
        ]].copy()
        df_export_all["data_ticket"] = df_export_all["data_ticket"].dt.strftime("%Y-%m-%d")
        df_export_all.columns = [
            "Ticket", "Data", "Fila", "Agente", "Assunto", "Nota", "Status",
            "Análise CSAT", "Oportunidade", "Observação", "Voz do Cliente", "Líder"
        ]
        buffer2 = io.BytesIO()
        with pd.ExcelWriter(buffer2, engine="openpyxl") as writer:
            df_export_all.to_excel(writer, index=False, sheet_name="Todos DSATs")
        st.download_button(
            "⬇️ Exportar Todos DSATs (.xlsx)",
            data=buffer2.getvalue(),
            file_name=f"todos_dsats_{data_ini}_{data_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

# ── PÁGINA: FILA ──────────────────────────────────────────────────────────────
def pagina_fila():
    st.title("Fila de DSATs — Close the Loop")
    st.caption(f"Logado como: **{st.session_state['lider']}**")

    c1, c2 = st.columns(2)
    with c1:
        data_ini = st.date_input("Data início", value=date.today() - timedelta(days=30))
    with c2:
        data_fim = st.date_input("Data fim", value=date.today())

    c3, c4, c5 = st.columns(3)
    with c3:
        filtro_status  = st.selectbox("Status", ["Pendente", "Feito", "Todos"])
    with c4:
        filtro_agente  = st.text_input("Filtrar por agente", "")
    with c5:
        filtro_assunto = st.text_input("Filtrar por assunto", "")

    df = carregar_fila()
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return

    mask = (
        (df["data_ticket"].dt.date >= data_ini) &
        (df["data_ticket"].dt.date <= data_fim)
    )
    df = df[mask]
    if filtro_status != "Todos":
        df = df[df["status_ctl"] == filtro_status]
    if filtro_agente:
        df = df[df["agente"].astype(str).str.contains(filtro_agente, case=False, na=False)]
    if filtro_assunto:
        df = df[df["assunto"].astype(str).str.contains(filtro_assunto, case=False, na=False)]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total",        len(df))
    m2.metric("🔴 Pendentes", int((df["status_ctl"] == "Pendente").sum()))
    m3.metric("🟢 Feitos",    int((df["status_ctl"] == "Feito").sum()))
    st.markdown("---")

    for _, row in df.iterrows():
        cor        = "🟢" if row["status_ctl"] == "Feito" else "🔴"
        n_str      = nota_str(row.get("nota"))
        assunto    = row.get("assunto") or "—"
        analise    = row.get("analise_csat") or "—"
        data       = limpar_data(row.get("data_ticket"))
        agente     = limpar_agente(row.get("agente"))
        fila       = row.get("depara_fila") or "—"
        comentario = row.get("comentario_cliente") or "—"

        with st.expander(f"{cor} #{row['ticket_id']} — {assunto} — Nota {n_str} — {data}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Dados do ticket**")
                st.markdown(f"- **Agente:** {agente}")
                st.markdown(f"- **Fila:** {fila}")
                st.markdown(f"- **Cliente:** {row.get('nome_cliente') or '—'}")
                st.markdown(f"- **Nota:** {n_str}")
                st.markdown(f"- **Voz do cliente:** {comentario}")
            with col2:
                st.markdown("**Análise close the loop**")
                st.markdown(f"- **Análise CSAT:** {analise}")
                st.markdown(f"- **Oportunidade:** {row.get('oportunidade') or '—'}")
                st.markdown(f"- **Observação:** {row.get('observacao') or '—'}")
                st.markdown(f"- **Status:** {row.get('status_ctl') or '—'}")
                st.markdown(f"- **Líder:** {row.get('lider') or '—'}")
            if st.button("✏️ Preencher análise", key=f"edit_{row['id']}"):
                row_dict = row.to_dict()
                row_dict["data_ticket"] = str(row.get("data_ticket"))
                st.session_state["pagina"]       = "editar"
                st.session_state["registro_id"]  = row["id"]
                st.session_state["registro_row"] = row_dict
                st.rerun()

# ── PÁGINA: EDITAR ────────────────────────────────────────────────────────────
def pagina_editar():
    st.title("Preencher análise — Close the Loop")
    st.markdown("---")

    row         = st.session_state.get("registro_row", {})
    id_registro = st.session_state.get("registro_id")

    n_str      = nota_str(row.get("nota"))
    data       = limpar_data(row.get("data_ticket"))
    agente     = limpar_agente(row.get("agente"))
    fila       = row.get("depara_fila") or "—"
    comentario = row.get("comentario_cliente") or "—"

    st.markdown("**Dados do ticket**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ticket",  f"#{row.get('ticket_id', '—')}")
    c2.metric("Nota",    n_str)
    c3.metric("Data",    data)
    c4, c5, c6 = st.columns(3)
    c4.metric("Agente",  agente)
    c5.metric("Fila",    fila)
    c6.metric("Cliente", row.get("nome_cliente") or "—")
    st.markdown(f"**Assunto:** {row.get('assunto') or '—'}")

    if comentario and comentario != "—":
        st.info(f"💬 **Voz do cliente:** {comentario}")

    st.markdown("---")
    st.markdown("**Análise close the loop**")

    analise_csat = st.selectbox(
        "Análise CSAT", OPCOES_CSAT,
        index=OPCOES_CSAT.index(row["analise_csat"]) if row.get("analise_csat") in OPCOES_CSAT else 0
    )
    oport_atual  = row.get("oportunidade") or ""
    oport_idx    = OPCOES_OPORTUNIDADE.index(oport_atual) if oport_atual in OPCOES_OPORTUNIDADE else 0
    oportunidade = st.selectbox("Oportunidade", OPCOES_OPORTUNIDADE, index=oport_idx)
    observacao   = st.text_area("Observação", value=row.get("observacao") or "", height=80)
    status_ctl   = st.selectbox(
        "Status", OPCOES_STATUS,
        index=OPCOES_STATUS.index(row["status_ctl"]) if row.get("status_ctl") in OPCOES_STATUS else 0
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Salvar análise", use_container_width=True):
            atualizar_analise(
                id_registro, analise_csat,
                oportunidade, observacao, status_ctl,
                st.session_state["lider"]
            )
            st.success("Análise salva!")
            st.session_state["pagina"] = "fila"
            st.rerun()
    with col2:
        if st.button("← Voltar", use_container_width=True):
            st.session_state["pagina"] = "fila"
            st.rerun()

# ── ROTEADOR ──────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="Close the Loop — EB",
        page_icon="🔁",
        layout="wide"
    )

    if "logado" not in st.session_state:
        st.session_state["logado"] = False
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "fila"

    if not st.session_state["logado"]:
        tela_login()
        return

    with st.sidebar:
        st.markdown("### 🔁 Close the Loop")
        st.markdown(f"👤 {st.session_state['lider']}")
        st.markdown("---")
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state["pagina"] = "dashboard"
            st.rerun()
        if st.button("📋 Fila de DSATs", use_container_width=True):
            st.session_state["pagina"] = "fila"
            st.rerun()
        st.markdown("---")
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

    pagina = st.session_state["pagina"]
    if pagina == "dashboard":
        pagina_dashboard()
    elif pagina == "fila":
        pagina_fila()
    elif pagina == "editar":
        pagina_editar()

if __name__ == "__main__":
    main()
