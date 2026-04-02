import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date, timedelta

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
    t = str(team or "").upper()
    i = str(contact_identity or "").lower()
    if "VIP" in t:          return "VIP"
    if "suportevup" in i:   return "VUPI"
    if "suporteprd1" in i:  return "Core"
    if "ura" in i:          return "URA"
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
    return s[:10]

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
        lambda r: depara_fila(r.get("fila"), r.get("agente")), axis=1
    )

    df["data_ticket"] = pd.to_datetime(df["data_ticket"], errors="coerce")

    return df

def atualizar_analise(id_registro, analise_csat, oportunidade, observacao, status_ctl, lider):
    sb = get_client()
    sb.table("ctlloop_analise").update({
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

# ── PÁGINA: FILA ──────────────────────────────────────────────────────────────
def pagina_fila():
    st.title("Fila de DSATs — Close the Loop")
    st.caption(f"Logado como: **{st.session_state['lider']}**")

    # Filtros
    c1, c2 = st.columns(2)
    with c1:
        data_ini = st.date_input("Data início", value=date.today() - timedelta(days=30))
    with c2:
        data_fim = st.date_input("Data fim", value=date.today())

    c3, c4, c5 = st.columns(3)
    with c3:
        filtro_status = st.selectbox("Status", ["Pendente", "Feito", "Todos"])
    with c4:
        filtro_agente = st.text_input("Filtrar por agente", "")
    with c5:
        filtro_assunto = st.text_input("Filtrar por assunto", "")

    df = carregar_fila()
    if df.empty:
        st.info("Nenhum registro encontrado.")
        return

    # Aplica filtros
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
    m1.metric("Total", len(df))
    m2.metric("🔴 Pendentes", int((df["status_ctl"] == "Pendente").sum()))
    m3.metric("🟢 Feitos",    int((df["status_ctl"] == "Feito").sum()))
    st.markdown("---")

    for _, row in df.iterrows():
        cor      = "🟢" if row["status_ctl"] == "Feito" else "🔴"
        nota_val = row.get("nota")
        nota_str = NOTAS_EMOJI.get(int(nota_val), f"⭐ {nota_val}") if pd.notna(nota_val) and nota_val else "—"
        assunto  = row.get("assunto") or "—"
        analise  = row.get("analise_csat") or "—"
        data     = limpar_data(row.get("data_ticket"))
        agente   = limpar_agente(row.get("agente"))
        fila     = row.get("depara_fila") or "—"

        with st.expander(f"{cor} #{row['ticket_id']} — {assunto} — Nota {nota_str} — {data}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Dados do ticket**")
                st.markdown(f"- **Agente:** {agente}")
                st.markdown(f"- **Fila:** {fila}")
                st.markdown(f"- **Canal:** {row.get('canal') or '—'}")
                st.markdown(f"- **Cliente:** {row.get('nome_cliente') or '—'}")
                st.markdown(f"- **Nota:** {nota_str}")
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

    nota_val = row.get("nota")
    try:
        nota_str = NOTAS_EMOJI.get(int(nota_val), f"⭐ {nota_val}") if nota_val and str(nota_val) not in ("None","nan") else "—"
    except:
        nota_str = "—"

    data   = limpar_data(row.get("data_ticket"))
    agente = limpar_agente(row.get("agente"))
    fila   = row.get("depara_fila") or row.get("fila") or "—"

    st.markdown("**Dados do ticket**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ticket", f"#{row.get('ticket_id', '—')}")
    c2.metric("Nota",   nota_str)
    c3.metric("Data",   data)
    c4, c5, c6 = st.columns(3)
    c4.metric("Agente", agente)
    c5.metric("Fila",   fila)
    c6.metric("Canal",  row.get("canal") or "—")
    st.markdown(f"**Assunto:** {row.get('assunto') or '—'}")
    st.markdown(f"**Cliente:** {row.get('nome_cliente') or '—'}")

    st.markdown("---")
    st.markdown("**Análise close the loop**")

    analise_csat = st.selectbox(
        "Análise CSAT", OPCOES_CSAT,
        index=OPCOES_CSAT.index(row["analise_csat"]) if row.get("analise_csat") in OPCOES_CSAT else 0
    )

    oport_atual  = row.get("oportunidade") or ""
    oport_idx    = OPCOES_OPORTUNIDADE.index(oport_atual) if oport_atual in OPCOES_OPORTUNIDADE else 0
    oportunidade = st.selectbox("Oportunidade", OPCOES_OPORTUNIDADE, index=oport_idx)

    observacao = st.text_area("Observação", value=row.get("observacao") or "", height=80)

    status_ctl = st.selectbox(
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
        if st.button("📋 Fila de DSATs"):
            st.session_state["pagina"] = "fila"
            st.rerun()
        st.markdown("---")
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

    pagina = st.session_state["pagina"]
    if pagina == "fila":
        pagina_fila()
    elif pagina == "editar":
        pagina_editar()

if __name__ == "__main__":
    main()
