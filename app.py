import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import date, timedelta
import io
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
ANTHROPIC_KEY = st.secrets.get("ANTHROPIC_KEY", "")

USUARIOS = {
    "gestao":             {"senha": "ctl2026",    "lider": "Geral"},
    "admin":              {"senha": "Henry@2026", "lider": "Admin"},
    "robert.borges":      {"senha": "Estrela123", "lider": "Robert Borges"},
    "mateus.santana":     {"senha": "Estrela123", "lider": "Mateus Santana"},
    "isabel.silva":       {"senha": "Estrela123", "lider": "Isabel Silva"},
    "fernanda.goncalves": {"senha": "Estrela123", "lider": "Fernanda Goncalves"},
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

def primeiro_dia_mes():
    hoje = date.today()
    return date(hoje.year, hoje.month, 1)

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
    if s in ("", "None", "nan", "NaT"):
        return "—"
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt):
            return s[:10]
        return dt.strftime("%d/%m/%Y")
    except:
        return s[:10]

def nota_str(val) -> str:
    try:
        return NOTAS_EMOJI.get(int(val), f"⭐ {val}") if pd.notna(val) and val else "—"
    except:
        return "—"

def categoria_oportunidade(oport) -> str:
    if not oport or pd.isna(oport):
        return "Sem classificação"
    o = str(oport)
    if o.startswith("EstrelaBet"):   return "EstrelaBet"
    if o.startswith("Inove"):        return "Inove"
    if o.startswith("Cliente"):      return "Cliente Discorda"
    return "Outros"

# ── DEPARA LIDERANÇA ──────────────────────────────────────────────────────────
@st.cache_data
def carregar_depara_lideranca():
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "depara_lideranca.xlsx")
    if not os.path.exists(caminho):
        return pd.DataFrame()
    df = pd.read_excel(caminho)
    df = df[["AgentIdentity", "Depara Nome", "Depara Lider"]].dropna(subset=["AgentIdentity"])
    df.columns = ["contact_identity", "nome_agente", "lider_depara"]
    df["contact_identity"] = df["contact_identity"].str.strip().str.lower()
    return df

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
    df["depara_fila"]  = df.apply(lambda r: depara_fila(r.get("fila"), r.get("contact_identity")), axis=1)
    df["data_ticket"]  = pd.to_datetime(df["data_ticket"], errors="coerce").dt.tz_convert("America/Sao_Paulo")
    df["agente_nome"]  = df["agente"].apply(limpar_agente)
    df["cat_oport"]    = df["oportunidade"].apply(categoria_oportunidade)

    depara = carregar_depara_lideranca()
    if not depara.empty:
        df["agente_key"] = df["agente"].str.strip().str.lower()
        df = df.merge(depara, left_on="agente_key", right_on="contact_identity", how="left", suffixes=("", "_dep"))
        df["lider_final"]       = df["lider_depara"].fillna("Não mapeado")
        df["nome_agente_final"] = df["nome_agente"].fillna(df["agente_nome"])
    else:
        df["lider_final"]       = "Não mapeado"
        df["nome_agente_final"] = df["agente_nome"]

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
                st.session_state.update({"logado": True, "usuario": usuario, "lider": USUARIOS[usuario]["lider"]})
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# ── PÁGINA: DASHBOARD ─────────────────────────────────────────────────────────
def pagina_dashboard():
    st.title("Dashboard — Close the Loop EB")

    st.sidebar.markdown("### Filtros")
    data_ini  = st.sidebar.date_input("Data início", value=primeiro_dia_mes(), key="dash_ini")
    data_fim  = st.sidebar.date_input("Data fim",    value=date.today(),       key="dash_fim")

    df_full = carregar_fila()
    if df_full.empty:
        st.info("Nenhum dado disponível.")
        return

    filtro_fila  = st.sidebar.multiselect("Fila",       ["Core", "VIP", "VUPI", "URA", "Outros"], default=[])
    lideres_disp = sorted(df_full["lider_final"].dropna().unique().tolist())
    filtro_lider = st.sidebar.multiselect("Liderança",  lideres_disp, default=[])
    filtro_cat   = st.sidebar.multiselect("Categoria Oportunidade", ["EstrelaBet", "Inove", "Cliente Discorda"], default=[])

    df = df_full[
        (df_full["data_ticket"].dt.date >= data_ini) &
        (df_full["data_ticket"].dt.date <= data_fim)
    ].copy()

    if filtro_fila:  df = df[df["depara_fila"].isin(filtro_fila)]
    if filtro_lider: df = df[df["lider_final"].isin(filtro_lider)]

    df_feito       = df[df["status_ctl"] == "Feito"].copy()
    df_feito_oport = df_feito[df_feito["cat_oport"].isin(filtro_cat)] if filtro_cat else df_feito

    total     = len(df)
    feitos    = len(df_feito)
    pendentes = total - feitos
    pct_feito = round(feitos / total * 100, 1) if total > 0 else 0
    qtd_eb    = len(df_feito[df_feito["analise_csat"] == "EstrelaBet"])
    qtd_inv   = len(df_feito[df_feito["analise_csat"] == "Inove"])
    qtd_cd    = len(df_feito[df_feito["analise_csat"] == "Cliente Discorda"])
    pct_eb    = round(qtd_eb  / feitos * 100, 1) if feitos > 0 else 0
    pct_inv   = round(qtd_inv / feitos * 100, 1) if feitos > 0 else 0
    pct_cd    = round(qtd_cd  / feitos * 100, 1) if feitos > 0 else 0

    # ── MÉTRICAS ───────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Total DSATs",      total)
    c2.metric("CTL Feitos",       feitos)
    c3.metric("% Feito",          f"{pct_feito}%")
    c4.metric("Pendentes",        pendentes)
    c5.metric("Oport. EB",        f"{qtd_eb} ({pct_eb}%)")
    c6.metric("Oport. Inove",     f"{qtd_inv} ({pct_inv}%)")
    c7.metric("Cli. Frustrado",   f"{qtd_cd} ({pct_cd}%)")
    st.markdown("---")

    # ── LINHA 1 ────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Resumo Geral — Análise CSAT")
        csat_c = df_feito["analise_csat"].value_counts().reset_index()
        csat_c.columns = ["Análise", "Qtd"]
        if not csat_c.empty:
            fig = px.pie(csat_c, values="Qtd", names="Análise", hole=0.55,
                         color="Análise", color_discrete_map=CORES_CSAT)
            fig.update_traces(textposition="outside", textinfo="label+percent+value")
            fig.update_layout(showlegend=True, margin=dict(t=20,b=20), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados no período.")

    with col2:
        st.subheader("DSATs e CTL por Fila")
        ft = df.groupby("depara_fila").size().reset_index(name="Total DSATs")
        ff = df_feito.groupby("depara_fila").size().reset_index(name="CTL Feitos")
        fm = ft.merge(ff, on="depara_fila", how="left").fillna(0)
        fm["CTL Feitos"] = fm["CTL Feitos"].astype(int)
        fm = fm.sort_values("Total DSATs", ascending=False)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="Total DSATs", x=fm["depara_fila"], y=fm["Total DSATs"], marker_color="#B5D4F4"))
        fig2.add_trace(go.Bar(name="CTL Feitos",  x=fm["depara_fila"], y=fm["CTL Feitos"],  marker_color="#1D9E75"))
        fig2.update_layout(barmode="group", height=320, margin=dict(t=20,b=20), legend=dict(orientation="h"))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── LINHA 2 ────────────────────────────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Evolução Semanal — CTL Feitos")
        dev = df_feito.copy()
        dev["semana"] = dev["data_ticket"].dt.to_period("W").dt.start_time
        evo = dev.groupby(["semana","analise_csat"]).size().reset_index(name="Qtd")
        evo["semana"] = evo["semana"].dt.strftime("%d/%m")
        if not evo.empty:
            fig3 = px.bar(evo, x="semana", y="Qtd", color="analise_csat",
                          color_discrete_map=CORES_CSAT,
                          labels={"semana":"Semana","Qtd":"Qtd","analise_csat":"Análise"})
            fig3.update_layout(height=320, margin=dict(t=20,b=20), legend=dict(orientation="h"))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sem dados no período.")

    with col4:
        st.subheader("Abertura por Liderança")
        ld = df_feito[df_feito["lider_final"] != "Não mapeado"]
        if not ld.empty:
            lc = ld.groupby(["lider_final","analise_csat"]).size().reset_index(name="Qtd")
            lt = lc.groupby("lider_final")["Qtd"].sum().reset_index(name="Total")
            lc = lc.merge(lt, on="lider_final")
            lc["pct"] = (lc["Qtd"] / lc["Total"] * 100).round(1)
            lc = lc.sort_values("Total", ascending=True)
            fig4 = px.bar(lc, x="pct", y="lider_final", color="analise_csat",
                          orientation="h", color_discrete_map=CORES_CSAT, text="Qtd",
                          labels={"pct":"%","lider_final":"Líder","analise_csat":"Análise"})
            fig4.update_layout(height=320, margin=dict(t=20,b=20), legend=dict(orientation="h"), barmode="stack")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Arquivo depara_lideranca.xlsx não encontrado no repositório." if not os.path.exists("depara_lideranca.xlsx") else "Sem dados de liderança mapeados no período.")

    st.markdown("---")

    # ── LINHA 3 ────────────────────────────────────────────────────────────
    col5, col6 = st.columns(2)
    with col5:
        cat_label = " / ".join(filtro_cat) if filtro_cat else "Todas"
        st.subheader(f"Top Oportunidades — {cat_label}")
        oport = df_feito_oport[df_feito_oport["oportunidade"].notna() & (df_feito_oport["oportunidade"] != "")]
        oc = oport["oportunidade"].value_counts().head(15).reset_index()
        oc.columns = ["Oportunidade","Qtd"]
        oc["Label"] = oc["Oportunidade"].str.replace(r"^(EstrelaBet|Inove|Cliente Frustrado)\s*[-–]\s*", "", regex=True)
        if not oc.empty:
            fig5 = px.bar(oc.sort_values("Qtd"), x="Qtd", y="Label", orientation="h",
                          color_discrete_sequence=["#7F77DD"], labels={"Qtd":"Qtd","Label":""})
            fig5.update_layout(height=420, margin=dict(t=20,b=20,l=10))
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Sem oportunidades no período/filtro.")

    with col6:
        st.subheader("DSATs por Nota")
        nc = df["nota"].value_counts().sort_index().reset_index()
        nc.columns = ["Nota","Qtd"]
        nc = nc[nc["Nota"].notna()]
        nc["Nota"] = nc["Nota"].apply(lambda x: f"Nota {int(x)}")
        fig6 = px.bar(nc, x="Nota", y="Qtd", color_discrete_sequence=["#D85A30"], labels={"Qtd":"Quantidade"})
        fig6.update_layout(height=200, margin=dict(t=20,b=20))
        st.plotly_chart(fig6, use_container_width=True)

        st.subheader("CTL por Assunto (Top 10)")
        ac = df_feito["assunto"].value_counts().head(10).reset_index()
        ac.columns = ["Assunto","Qtd"]
        fig7 = px.bar(ac.sort_values("Qtd"), x="Qtd", y="Assunto", orientation="h",
                      color_discrete_sequence=["#1D9E75"], labels={"Qtd":"Qtd","Assunto":""})
        fig7.update_layout(height=260, margin=dict(t=10,b=10,l=10))
        st.plotly_chart(fig7, use_container_width=True)


    st.markdown("---")

    # ── INSIGHTS ───────────────────────────────────────────────────────────
    st.subheader("💡 Insights do período")

    col_i1, col_i2, col_i3 = st.columns(3)
    min_dsats = 3

    # --- OFENSORES: agentes com ocorrências Inove (falha do consultor) ---
    with col_i1:
        st.markdown("#### 🔴 Ofensores")
        st.caption("Agentes com ocorrências Inove — falha no processo do consultor")
        df_inove = df_feito[df_feito["analise_csat"] == "Inove"]
        if df_inove.empty:
            st.info("Nenhuma ocorrência Inove no período.")
        else:
            inove_ag = df_inove.groupby("nome_agente_final").size().reset_index(name="Ocorr. Inove")
            total_ag = df.groupby("nome_agente_final").size().reset_index(name="DSATs")
            inove_ag = inove_ag.merge(total_ag, on="nome_agente_final", how="left")
            inove_ag["% Inove"] = (inove_ag["Ocorr. Inove"] / inove_ag["DSATs"] * 100).round(1)
            inove_ag = inove_ag.sort_values("Ocorr. Inove", ascending=False).head(5)
            for _, r in inove_ag.iterrows():
                cor = "🔴" if r["% Inove"] >= 20 else "🟡"
                st.markdown(f"{cor} **{r['nome_agente_final']}**")
                st.caption(f"{int(r['DSATs'])} DSATs — {int(r['Ocorr. Inove'])} ocorr. Inove — {r['% Inove']}% do total")

    # --- DESTAQUES: agentes com alto CTL e zero Inove ---
    with col_i2:
        st.markdown("#### 🟢 Destaques")
        st.caption("Agentes com melhor CTL e sem ocorrências Inove")
        op_dest = df.groupby("nome_agente_final").size().reset_index(name="DSATs")
        op_feito_d = df_feito.groupby("nome_agente_final").size().reset_index(name="Feitos")
        op_inove_d = df_feito[df_feito["analise_csat"]=="Inove"].groupby("nome_agente_final").size().reset_index(name="Inove")
        op_dest = op_dest.merge(op_feito_d, on="nome_agente_final", how="left").fillna(0)
        op_dest = op_dest.merge(op_inove_d, on="nome_agente_final", how="left").fillna(0)
        op_dest["Feitos"] = op_dest["Feitos"].astype(int)
        op_dest["Inove"]  = op_dest["Inove"].astype(int)
        op_dest["% CTL"]  = (op_dest["Feitos"] / op_dest["DSATs"] * 100).round(1)
        op_dest = op_dest[(op_dest["DSATs"] >= min_dsats) & (op_dest["Inove"] == 0)].sort_values("% CTL", ascending=False).head(5)
        if op_dest.empty:
            st.info("Sem dados suficientes.")
        else:
            for _, r in op_dest.iterrows():
                cor = "🟢" if r["% CTL"] >= 80 else "🟡"
                st.markdown(f"{cor} **{r['nome_agente_final']}**")
                st.caption(f"{int(r['DSATs'])} DSATs — {int(r['Feitos'])} feitos — {r['% CTL']}% CTL — 0 Inove")

    # --- COMPARATIVO SEMANAL ---
    with col_i3:
        st.markdown("#### 📊 Comparativo semanal")
        hoje = pd.Timestamp.now(tz="America/Sao_Paulo")
        ini_sem_atual  = (hoje - pd.Timedelta(days=hoje.weekday())).normalize()
        ini_sem_ant    = ini_sem_atual - pd.Timedelta(weeks=1)
        fim_sem_ant    = ini_sem_atual - pd.Timedelta(days=1)

        sem_atual = df_full[df_full["data_ticket"] >= ini_sem_atual]
        sem_ant   = df_full[(df_full["data_ticket"] >= ini_sem_ant) & (df_full["data_ticket"] <= fim_sem_ant)]

        def resumo(d):
            total = len(d)
            feito = len(d[d["status_ctl"] == "Feito"])
            pct   = round(feito / total * 100, 1) if total > 0 else 0
            return total, feito, pct

        t_a, f_a, p_a     = resumo(sem_atual)
        t_ant, f_ant, p_ant = resumo(sem_ant)
        delta_t = t_a - t_ant
        delta_f = f_a - f_ant
        delta_p = round(p_a - p_ant, 1)

        st.metric("DSATs semana atual", t_a,  delta=f"{delta_t:+d} vs semana ant.")
        st.metric("CTL feitos",         f_a,  delta=f"{delta_f:+d} vs semana ant.")
        st.metric("% CTL",              f"{p_a}%", delta=f"{delta_p:+.1f}pp vs semana ant.")

        inove_sem = len(sem_atual[sem_atual["analise_csat"]=="Inove"])
        inove_ant = len(sem_ant[sem_ant["analise_csat"]=="Inove"])
        st.metric("Ocorr. Inove",       inove_sem, delta=f"{inove_sem-inove_ant:+d} vs semana ant.", delta_color="inverse")

        top_oport = sem_atual[sem_atual["status_ctl"]=="Feito"]["oportunidade"].value_counts().head(3)
        if not top_oport.empty:
            st.markdown("**Top oportunidades esta semana:**")
            for o, q in top_oport.items():
                label = str(o).replace("EstrelaBet - ","").replace("Inove - ","").replace("Cliente Frustrado – ","")
                st.caption(f"• {label}: {q}")

    st.markdown("---")

    # ── ANÁLISE VOZ DO CLIENTE ─────────────────────────────────────────────
    st.subheader("🗣️ Análise de Voz do Cliente")

    df_voz = df_feito[
        df_feito["comentario_cliente"].notna() &
        (df_feito["comentario_cliente"] != "") &
        (df_feito["comentario_cliente"] != "—")
    ].copy()

    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        st.metric("Tickets com voz do cliente", len(df_voz))
        st.metric("Sem comentário", feitos - len(df_voz))

        usuario_atual = st.session_state.get("usuario", "")
        pode_usar_ia = usuario_atual in ("gestao", "admin") and ANTHROPIC_KEY
        if not df_voz.empty and pode_usar_ia:
            if st.button("🤖 Gerar análise com IA", use_container_width=True):
                with st.spinner("Analisando observações e comentários..."):
                    amostra_obs  = df_voz["observacao"].dropna().head(50).tolist()
                    amostra_voz  = df_voz["comentario_cliente"].dropna().head(50).tolist()
                    amostra_oport = df_voz["oportunidade"].dropna().head(50).tolist()

                    prompt = f"""Você é um analista de CX especialista em operações de atendimento.
Analise os dados abaixo de {len(df_voz)} tickets DSAT tratados no Close the Loop da EstrelaBet.

OBSERVAÇÕES DOS LÍDERES (amostra):
{chr(10).join(f'- {o}' for o in amostra_obs if o)}

VOZ DO CLIENTE (comentários das avaliações negativas):
{chr(10).join(f'- {v}' for v in amostra_voz if v)}

OPORTUNIDADES IDENTIFICADAS:
{chr(10).join(f'- {p}' for p in amostra_oport if p)}

Gere um relatório executivo em português com:
1. **Principais temas recorrentes** na voz do cliente (máx 5 tópicos)
2. **Padrões identificados** nas observações dos líderes
3. **Correlações** entre o que o cliente reclama e a oportunidade identificada
4. **Recomendações de negócio** (máx 3 ações prioritárias)

Seja direto, use linguagem executiva. Máximo 400 palavras."""

                    resp = requests.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": ANTHROPIC_KEY,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={
                            "model": "claude-sonnet-4-20250514",
                            "max_tokens": 1000,
                            "messages": [{"role": "user", "content": prompt}]
                        },
                        timeout=30
                    )
                    if resp.status_code == 200:
                        analise = resp.json()["content"][0]["text"]
                        st.session_state["analise_voz"] = analise
                    else:
                        st.error(f"Erro na API: {resp.status_code}")
        elif not ANTHROPIC_KEY:
            st.warning("Configure ANTHROPIC_KEY nos secrets do Streamlit para habilitar análise com IA.")
        elif not df_voz.empty and not pode_usar_ia:
            st.info("Análise com IA disponível apenas para gestão e admin.")

    with col_v2:
        if "analise_voz" in st.session_state:
            st.markdown(st.session_state["analise_voz"])
        elif not df_voz.empty:
            # Análise simples sem IA
            st.markdown("**Palavras mais frequentes nos comentários:**")
            import re
            from collections import Counter
            stopwords = {"de","da","do","que","o","a","e","em","um","uma","com","para","por","não","no","na","se","os","as","ao","ou","mais","me","meu","minha","foi","pois","mas","já","ele","ela","seu","sua","isso","este","esta","esse","essa","tem","são","está"}
            todos_comentarios = " ".join(df_voz["comentario_cliente"].dropna().tolist()).lower()
            palavras = re.findall(r"[a-záéíóúâêîôûãõç]{4,}", todos_comentarios)
            freq = Counter(w for w in palavras if w not in stopwords).most_common(15)
            if freq:
                freq_df = pd.DataFrame(freq, columns=["Palavra","Frequência"])
                fig_voz = px.bar(freq_df.sort_values("Frequência"), x="Frequência", y="Palavra",
                                 orientation="h", color_discrete_sequence=["#7F77DD"])
                fig_voz.update_layout(height=350, margin=dict(t=10,b=10,l=10))
                st.plotly_chart(fig_voz, use_container_width=True)
        else:
            st.info("Sem comentários de clientes no período selecionado.")

    st.markdown("---")

    # ── TABELA OPERADORES ──────────────────────────────────────────────────
    st.subheader("Abertura por Operador")
    ot = df.groupby("nome_agente_final").size().reset_index(name="Qtd DSAT")
    of = df_feito.groupby("nome_agente_final").size().reset_index(name="CTL Feito")
    ol = df[["nome_agente_final","lider_final"]].drop_duplicates("nome_agente_final")
    om = ot.merge(of, on="nome_agente_final", how="left").fillna(0)
    om = om.merge(ol, on="nome_agente_final", how="left")
    om["CTL Feito"] = om["CTL Feito"].astype(int)
    om["% Feito"]   = (om["CTL Feito"] / om["Qtd DSAT"] * 100).round(1).astype(str) + "%"
    for cat in ["Cliente Discorda","EstrelaBet","Inove"]:
        sub = df_feito[df_feito["analise_csat"]==cat].groupby("nome_agente_final").size().reset_index(name=f"Qtd {cat}")
        om = om.merge(sub, on="nome_agente_final", how="left").fillna(0)
        om[f"Qtd {cat}"] = om[f"Qtd {cat}"].astype(int)
    om = om.sort_values("Qtd DSAT", ascending=False)
    om.columns = ["Agente","Qtd DSAT","CTL Feito","Líder","% Feito","Cli. Discorda","EstrelaBet","Inove"]
    om = om[["Agente","Líder","Qtd DSAT","CTL Feito","% Feito","Cli. Discorda","EstrelaBet","Inove"]]
    st.dataframe(om, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── EXTRAÇÃO ────────────────────────────────────────────────────────────
    st.subheader("Extrair dados")

    def gerar_excel(df_exp, sheet):
        cols_map = {
            "ticket_id":"Ticket","data_ticket":"Data","depara_fila":"Fila",
            "nome_agente_final":"Agente","lider_final":"Líder",
            "assunto":"Assunto","nota":"Nota","status_ctl":"Status",
            "analise_csat":"Análise CSAT","oportunidade":"Oportunidade",
            "observacao":"Observação","comentario_cliente":"Voz do Cliente",
            "lider":"Analisado por","updated_at":"Data/Hora Análise",
        }
        cols = [c for c in cols_map if c in df_exp.columns]
        out  = df_exp[cols].copy()
        out["data_ticket"] = pd.to_datetime(out["data_ticket"], errors="coerce").dt.strftime("%d/%m/%Y")
        if "updated_at" in out.columns:
            out["updated_at"] = pd.to_datetime(out["updated_at"], errors="coerce").dt.tz_convert("America/Sao_Paulo").dt.strftime("%d/%m/%Y %H:%M")
        out.columns = [cols_map[c] for c in cols]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            out.to_excel(w, index=False, sheet_name=sheet)
        return buf.getvalue()

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Exportar CTL Feitos (.xlsx)",
            data=gerar_excel(df_feito, "CTL Feitos"),
            file_name=f"ctl_feitos_{data_ini}_{data_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
    with c2:
        st.download_button("⬇️ Exportar Todos DSATs (.xlsx)",
            data=gerar_excel(df, "Todos DSATs"),
            file_name=f"todos_dsats_{data_ini}_{data_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

# ── PÁGINA: FILA ──────────────────────────────────────────────────────────────
def pagina_fila():
    st.title("Fila de DSATs — Close the Loop")
    st.caption(f"Logado como: **{st.session_state['lider']}**")

    c1, c2 = st.columns(2)
    with c1: data_ini = st.date_input("Data início", value=primeiro_dia_mes())
    with c2: data_fim = st.date_input("Data fim",    value=date.today())
    c3, c4, c5, c6 = st.columns(4)
    with c3: filtro_status  = st.selectbox("Status", ["Pendente","Feito","Todos"])
    with c4: filtro_agente  = st.text_input("Filtrar por agente", "")
    with c5: filtro_assunto = st.text_input("Filtrar por assunto", "")

    df = carregar_fila()
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return

    lideres_fila = sorted(df["lider_final"].dropna().unique().tolist())
    with c6: filtro_lider_fila = st.selectbox("Liderança", ["Todos"] + lideres_fila)

    mask = (df["data_ticket"].dt.date >= data_ini) & (df["data_ticket"].dt.date <= data_fim)
    df   = df[mask]
    if filtro_status != "Todos":
        df = df[df["status_ctl"] == filtro_status]
    if filtro_agente:
        df = df[df["agente"].astype(str).str.contains(filtro_agente, case=False, na=False)]
    if filtro_assunto:
        df = df[df["assunto"].astype(str).str.contains(filtro_assunto, case=False, na=False)]
    if filtro_lider_fila != "Todos":
        df = df[df["lider_final"] == filtro_lider_fila]

    m1, m2, m3 = st.columns(3)
    m1.metric("Total",        len(df))
    m2.metric("🔴 Pendentes", int((df["status_ctl"]=="Pendente").sum()))
    m3.metric("🟢 Feitos",    int((df["status_ctl"]=="Feito").sum()))
    st.markdown("---")

    for _, row in df.iterrows():
        cor        = "🟢" if row["status_ctl"] == "Feito" else "🔴"
        n_str      = nota_str(row.get("nota"))
        assunto    = row.get("assunto") or "—"
        analise    = row.get("analise_csat") or "—"
        data       = limpar_data(row.get("data_ticket"))
        agente     = row.get("nome_agente_final") or limpar_agente(row.get("agente"))
        fila       = row.get("depara_fila") or "—"
        lider      = row.get("lider_final") or "—"
        comentario = row.get("comentario_cliente") or "—"

        with st.expander(f"{cor} #{row['ticket_id']} — {assunto} — Nota {n_str} — {data}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Dados do ticket**")
                st.markdown(f"- **Agente:** {agente}")
                st.markdown(f"- **Líder:** {lider}")
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
            if st.button("✏️ Preencher análise", key=f"edit_{row['id']}"):
                row_dict = row.to_dict()
                row_dict["data_ticket"] = str(row.get("data_ticket"))
                st.session_state.update({"pagina":"editar","registro_id":row["id"],"registro_row":row_dict})
                st.rerun()

# ── PÁGINA: EDITAR ────────────────────────────────────────────────────────────
def pagina_editar():
    st.title("Preencher análise — Close the Loop")
    st.markdown("---")

    row         = st.session_state.get("registro_row", {})
    id_registro = st.session_state.get("registro_id")

    n_str      = nota_str(row.get("nota"))
    data       = limpar_data(row.get("data_ticket"))
    agente     = row.get("nome_agente_final") or limpar_agente(row.get("agente"))
    fila       = row.get("depara_fila") or "—"
    lider      = row.get("lider_final") or "—"
    comentario = row.get("comentario_cliente") or "—"

    st.markdown("**Dados do ticket**")
    c1,c2,c3 = st.columns(3)
    c1.metric("Ticket", f"#{row.get('ticket_id','—')}")
    c2.metric("Nota",   n_str)
    c3.metric("Data",   data)
    c4,c5,c6 = st.columns(3)
    c4.metric("Agente", agente)
    c5.metric("Fila",   fila)
    c6.metric("Líder",  lider)
    st.markdown(f"**Assunto:** {row.get('assunto') or '—'}")
    st.markdown(f"**Cliente:** {row.get('nome_cliente') or '—'}")

    if comentario and comentario != "—":
        st.info(f"💬 **Voz do cliente:** {comentario}")

    st.markdown("---")
    st.markdown("**Análise close the loop**")

    analise_csat = st.selectbox("Análise CSAT", OPCOES_CSAT,
        index=OPCOES_CSAT.index(row["analise_csat"]) if row.get("analise_csat") in OPCOES_CSAT else 0)
    oport_atual  = row.get("oportunidade") or ""
    oport_idx    = OPCOES_OPORTUNIDADE.index(oport_atual) if oport_atual in OPCOES_OPORTUNIDADE else 0
    oportunidade = st.selectbox("Oportunidade", OPCOES_OPORTUNIDADE, index=oport_idx)
    observacao   = st.text_area("Observação", value=row.get("observacao") or "", height=80)
    status_ctl   = st.selectbox("Status", OPCOES_STATUS,
        index=OPCOES_STATUS.index(row["status_ctl"]) if row.get("status_ctl") in OPCOES_STATUS else 0)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Salvar análise", use_container_width=True):
            atualizar_analise(id_registro, analise_csat, oportunidade, observacao, status_ctl, st.session_state["lider"])
            st.success("Análise salva!")
            st.session_state["pagina"] = "fila"
            st.rerun()
    with c2:
        if st.button("← Voltar", use_container_width=True):
            st.session_state["pagina"] = "fila"
            st.rerun()

# ── ROTEADOR ──────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Close the Loop — EB", page_icon="🔁", layout="wide")

    if "logado" not in st.session_state:
        st.session_state["logado"] = False
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "dashboard"

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
    if pagina == "dashboard":   pagina_dashboard()
    elif pagina == "fila":      pagina_fila()
    elif pagina == "editar":    pagina_editar()

if __name__ == "__main__":
    main()
