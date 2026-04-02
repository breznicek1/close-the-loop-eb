import streamlit as st
import pandas as pd
from supabase import create_client

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

# ── SUPABASE ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def carregar_fila():
    sb    = get_client()
    todos = []
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
    return pd.DataFrame(todos) if todos else pd.DataFrame()

def atualizar_analise(id_registro, analise_csat, oportunidade, observacao, status_ctl, lider):
    sb = get_client()
    sb.table("ctlloop_analise").update({
        "analise_csat": analise_csat,
        "oportunidade": oportunidade,
        "observacao":   observacao,
        "status_ctl":   status_ctl,
        "lider":        lider,
    }).eq("id", id_registro).execute()

# ── LOGIN ─────────────────────────────────────────────────────────────────────
def tela_login():
    st.title("Close the Loop — EstrelaBet")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Entrar")
        usuario = st.text_input("Usuário").strip().lower()
        senha   = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
                st.session_state["logado"]  = True
                st.session_state["usuario"] = usuario
                st.session_state["lider"]   = USUARIOS[usuario]["lider"]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# ── PÁGINA: FILA ──────────────────────────────────────────────────────────────
def pagina_fila():
    st.title("Fila de DSATs — Close the Loop")
    st.caption(f"Logado como: **{st.session_state['lider']}**")

    col_filtro1, col_filtro2, col_filtro3 = st.columns([2, 2, 2])
    with col_filtro1:
        filtro_status = st.selectbox("Status", ["Pendente", "Feito", "Todos"])
    with col_filtro2:
        filtro_agente = st.text_input("Filtrar por agente", "")
    with col_filtro3:
        filtro_assunto = st.text_input("Filtrar por assunto", "")

    df = carregar_fila()

    if df.empty:
        st.info("Nenhum registro encontrado.")
        return

    if filtro_status != "Todos":
        df = df[df["status_ctl"] == filtro_status]
    if filtro_agente:
        df = df[df["agente"].str.contains(filtro_agente, case=False, na=False)]
    if filtro_assunto:
        df = df[df["assunto"].str.contains(filtro_assunto, case=False, na=False)]

    total     = len(df)
    pendentes = int((df["status_ctl"] == "Pendente").sum())
    feitos    = int((df["status_ctl"] == "Feito").sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Total", total)
    c2.metric("🔴 Pendentes", pendentes)
    c3.metric("🟢 Feitos", feitos)
    st.markdown("---")

    for _, row in df.iterrows():
        cor      = "🟢" if row["status_ctl"] == "Feito" else "🔴"
        nota_val = row.get("nota")
        nota_str = NOTAS_EMOJI.get(int(nota_val), f"⭐ {nota_val}") if nota_val else "—"
        assunto  = row.get("assunto") or "—"
        analise  = row.get("analise_csat") or "—"
        data     = str(row.get("data_ticket") or "")[:10]

        with st.expander(f"{cor} #{row['ticket_id']} — {assunto} — Nota {nota_str} — {data}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Dados do ticket**")
                st.markdown(f"- **Agente:** {row.get('agente') or '—'}")
                st.markdown(f"- **Fila:** {row.get('fila') or '—'}")
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
                st.session_state["pagina"]       = "editar"
                st.session_state["registro_id"]  = row["id"]
                st.session_state["registro_row"] = row.to_dict()
                st.rerun()

# ── PÁGINA: EDITAR ────────────────────────────────────────────────────────────
def pagina_editar():
    st.title("Preencher análise — Close the Loop")
    st.markdown("---")

    row         = st.session_state.get("registro_row", {})
    id_registro = st.session_state.get("registro_id")

    nota_val = row.get("nota")
    nota_str = NOTAS_EMOJI.get(int(nota_val), f"⭐ {nota_val}") if nota_val else "—"
    data     = str(row.get("data_ticket") or "")[:10]

    with st.container():
        st.markdown("**Dados do ticket**")
        col1, col2, col3 = st.columns(3)
        col1.metric("Ticket", f"#{row.get('ticket_id', '—')}")
        col2.metric("Nota", nota_str)
        col3.metric("Data", data or "—")
        col4, col5, col6 = st.columns(3)
        col4.metric("Agente", row.get("agente") or "—")
        col5.metric("Fila", row.get("fila") or "—")
        col6.metric("Canal", row.get("canal") or "—")
        st.markdown(f"**Assunto:** {row.get('assunto') or '—'}")
        st.markdown(f"**Cliente:** {row.get('nome_cliente') or '—'}")

    st.markdown("---")
    st.markdown("**Análise close the loop**")

    analise_csat = st.selectbox(
        "Análise CSAT", OPCOES_CSAT,
        index=OPCOES_CSAT.index(row["analise_csat"]) if row.get("analise_csat") in OPCOES_CSAT else 0
    )
    oportunidade = st.text_area("Oportunidade", value=row.get("oportunidade") or "", height=80)
    observacao   = st.text_area("Observação",   value=row.get("observacao")   or "", height=80)
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
