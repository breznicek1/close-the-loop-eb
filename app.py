import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

USUARIOS = {
    "gestor":    {"senha": "ctl2026", "lider": "geral"},
    "admin":     {"senha": "admin2026", "lider": "STAFF I9"},
}

OPCOES_CSAT = ["Cliente Discorda", "EstrelaBet", "Inove"]
OPCOES_STATUS = ["Pendente", "Feito"]

# ── SUPABASE ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def carregar_fila():
    sb = get_client()
    res = sb.table("ctlloop_analise").select("*").order("created_at", desc=False).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def salvar_analise(ticket_id, analise_csat, oportunidade, observacao, status_ctl, lider):
    sb = get_client()
    sb.table("ctlloop_analise").insert({
        "ticket_id":    ticket_id,
        "analise_csat": analise_csat,
        "oportunidade": oportunidade,
        "observacao":   observacao,
        "status_ctl":   status_ctl,
        "lider":        lider,
    }).execute()

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

    col_filtro1, col_filtro2, col_add = st.columns([2, 2, 1])
    with col_filtro1:
        filtro_status = st.selectbox("Filtrar por status", ["Todos", "Pendente", "Feito"])
    with col_filtro2:
        filtro_lider = st.text_input("Filtrar por líder", "")
    with col_add:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Novo registro", use_container_width=True):
            st.session_state["pagina"] = "novo"
            st.rerun()

    df = carregar_fila()

    if df.empty:
        st.info("Nenhum registro encontrado. Clique em '➕ Novo registro' para começar.")
        return

    if filtro_status != "Todos":
        df = df[df["status_ctl"] == filtro_status]
    if filtro_lider:
        df = df[df["lider"].str.contains(filtro_lider, case=False, na=False)]

    st.markdown(f"**{len(df)} registro(s)**")
    st.markdown("---")

    for _, row in df.iterrows():
        cor = "🟢" if row["status_ctl"] == "Feito" else "🔴"
        with st.expander(f"{cor} Ticket {row['ticket_id']} — {row['analise_csat']} — {row['status_ctl']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Líder:** {row.get('lider', '—')}")
                st.markdown(f"**Análise CSAT:** {row.get('analise_csat', '—')}")
                st.markdown(f"**Status:** {row.get('status_ctl', '—')}")
            with col2:
                st.markdown(f"**Oportunidade:** {row.get('oportunidade', '—') or '—'}")
                st.markdown(f"**Observação:** {row.get('observacao', '—') or '—'}")
            criado = row.get("created_at", "")
            if criado:
                st.caption(f"Criado em: {criado[:16].replace('T', ' ')}")
            if st.button("✏️ Editar", key=f"edit_{row['id']}"):
                st.session_state["pagina"]       = "editar"
                st.session_state["registro_id"]  = row["id"]
                st.session_state["registro_row"] = row.to_dict()
                st.rerun()

# ── PÁGINA: NOVO REGISTRO ─────────────────────────────────────────────────────
def pagina_novo():
    st.title("Novo registro — Close the Loop")
    st.markdown("---")

    ticket_id    = st.text_input("Ticket ID (sequentialId)")
    analise_csat = st.selectbox("Análise CSAT", OPCOES_CSAT)
    oportunidade = st.text_area("Oportunidade", height=80)
    observacao   = st.text_area("Observação", height=80)
    status_ctl   = st.selectbox("Status", OPCOES_STATUS)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Salvar", use_container_width=True):
            if not ticket_id.strip():
                st.error("Informe o Ticket ID.")
            else:
                salvar_analise(
                    ticket_id.strip(), analise_csat,
                    oportunidade, observacao, status_ctl,
                    st.session_state["lider"]
                )
                st.success("Registro salvo!")
                st.session_state["pagina"] = "fila"
                st.rerun()
    with col2:
        if st.button("← Voltar", use_container_width=True):
            st.session_state["pagina"] = "fila"
            st.rerun()

# ── PÁGINA: EDITAR ────────────────────────────────────────────────────────────
def pagina_editar():
    st.title("Editar registro — Close the Loop")
    st.markdown("---")

    row = st.session_state.get("registro_row", {})
    id_registro = st.session_state.get("registro_id")

    st.markdown(f"**Ticket:** {row.get('ticket_id', '—')}")

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
        if st.button("💾 Salvar alterações", use_container_width=True):
            atualizar_analise(
                id_registro, analise_csat,
                oportunidade, observacao, status_ctl,
                st.session_state["lider"]
            )
            st.success("Atualizado!")
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

    # Sidebar
    with st.sidebar:
        st.markdown("### 🔁 Close the Loop")
        st.markdown(f"👤 {st.session_state['lider']}")
        st.markdown("---")
        if st.button("📋 Fila de DSATs"):
            st.session_state["pagina"] = "fila"
            st.rerun()
        if st.button("➕ Novo registro"):
            st.session_state["pagina"] = "novo"
            st.rerun()
        st.markdown("---")
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

    pagina = st.session_state["pagina"]
    if pagina == "fila":
        pagina_fila()
    elif pagina == "novo":
        pagina_novo()
    elif pagina == "editar":
        pagina_editar()

if __name__ == "__main__":
    main()
