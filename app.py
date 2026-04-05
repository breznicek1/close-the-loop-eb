"""
app.py — Chat Dashboard EB v4
Dashboard de atendimento chat EstrelaBet — i9xc.com
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
import io, os

from db import run_query, fmt_time, default_dates
from queries import SQL_BASE_GERAL, SQL_RECHAMADA, SQL_N1, SQL_CLIENTE, SQL_CLIENTES_RECORRENTES
from diario import get_diario

st.set_page_config(page_title="Chat Dashboard EB", page_icon="⭐", layout="wide", initial_sidebar_state="expanded")

META_CSAT = 0.90
META_TMA  = 15 * 60

USUARIOS = {
    "gestao":             {"senha": "chat2026",  "perfil": "admin"},
    "admin":              {"senha": "Henry@2026", "perfil": "admin"},
    "danny":              {"senha": "Estrela123", "perfil": "ControlDesk"},
    "isabel.silva":       {"senha": "Estrela123", "perfil": "lider"},
    "fernanda.goncalves": {"senha": "Estrela123", "perfil": "lider"},
    "mateus.santana":     {"senha": "Estrela123", "perfil": "lider"},
    "robert.borges":      {"senha": "Estrela123", "perfil": "lider"},
}

def login():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"]{
        background:linear-gradient(160deg,#020d1f 0%,#071228 55%,#0a1a35 100%)!important;}
    [data-testid="stHeader"]{background:transparent!important;}
    .lg-wrap{display:flex;flex-direction:column;align-items:center;padding-top:60px;}
    .lg-logo{display:flex;align-items:center;gap:14px;margin-bottom:36px;}
    .lg-inove{font-size:2rem;font-weight:900;letter-spacing:3px;
        background:linear-gradient(90deg,#4fc3f7 0%,#9775fa 50%,#ff7043 100%);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
    .lg-sep{color:#1e3a70;font-size:1.6rem;font-weight:200;-webkit-text-fill-color:#1e3a70;}
    .lg-eb{font-size:1.3rem;font-weight:800;color:#f5c518;letter-spacing:2px;-webkit-text-fill-color:#f5c518;}
    .lg-box{background:rgba(13,27,62,0.97);border:1px solid #1e3a70;border-radius:18px;
        padding:36px 40px 28px;width:100%;max-width:400px;
        box-shadow:0 20px 60px rgba(0,0,0,.5),inset 0 1px 0 rgba(79,195,247,.08);}
    .lg-title{text-align:center;color:#fff;font-size:1.2rem;font-weight:700;margin-bottom:4px;}
    .lg-sub{text-align:center;color:#7fa8d4;font-size:.82rem;margin-bottom:22px;}
    .lg-div{border:none;border-top:1px solid #1a3a70;margin:0 0 20px;}
    </style>
    <div class="lg-wrap">
        <div class="lg-logo">
            <span class="lg-inove">●INOVE</span>
            <span class="lg-sep">|</span>
            <span class="lg-eb">★ ESTRELABET</span>
        </div>
        <div class="lg-box">
            <div class="lg-title">Chat Dashboard EB</div>
            <div class="lg-sub">Central de Atendimento · i9xc.com</div>
            <hr class="lg-div">
        </div>
    </div>
    """, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        with st.form("login_form"):
            u = st.text_input("👤 Usuário", placeholder="seu.usuario")
            s = st.text_input("🔒 Senha", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("Entrar →", use_container_width=True):
                usr = USUARIOS.get(u)
                if usr and usr["senha"] == s:
                    st.session_state.update({"logado":True,"usuario":u,"perfil":usr["perfil"]})
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

if not st.session_state.get("logado"):
    login(); st.stop()

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{font-family:'Inter',sans-serif!important;}
section[data-testid="stSidebar"]{background:#071228!important;border-right:1px solid #1a2f52;}
section[data-testid="stSidebar"] *{color:#e0ecff!important;}
section[data-testid="stSidebar"] label{font-size:.82rem!important;font-weight:500!important;}
section[data-testid="stSidebar"] input{color:#ffffff!important;background:#0d1b3e!important;
    border:1px solid #1e3a70!important;border-radius:6px!important;}
section[data-testid="stSidebar"] .stDateInput input{color:#ffffff!important;}
section[data-testid="stSidebar"] [data-testid="stDateInput"] *{color:#e0ecff!important;}
.ph{background:linear-gradient(135deg,#071228,#0d2250);padding:14px 22px;border-radius:10px;
    margin-bottom:16px;border:1px solid #1a3a70;display:flex;align-items:center;justify-content:space-between;}
.pt{color:#fff;font-size:1.25rem;font-weight:700;}.pl{color:#f5c518;font-size:1rem;font-weight:800;letter-spacing:2px;}
.kr{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;}
.kc{flex:1;min-width:110px;background:#0d1b3e;border:1px solid #1e3a70;border-radius:10px;padding:12px 14px;text-align:center;}
.kl{color:#a8c4e8;font-size:.67rem;font-weight:600;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;}
.kv{color:#ffffff;font-size:1.5rem;font-weight:700;line-height:1.1;}
.kp{color:#4fc3f7;font-size:.88rem;font-weight:600;margin-top:2px;}
.kr-red .kv,.kr-red .kp{color:#ff6b6b!important;}
.kr-green .kv,.kr-green .kp{color:#69db7c!important;}
.kr-yellow .kv,.kr-yellow .kp{color:#ffd43b!important;}
.stTabs [data-baseweb="tab-list"]{gap:3px;background:#071228;border-radius:8px;padding:4px;}
[data-baseweb="tag"] svg{display:none!important;}
[data-baseweb="tag"]{background:#1a3a70!important;border:none!important;}
[data-baseweb="tag"] span{color:#e0ecff!important;}
.stTabs [data-baseweb="tab"]{background:transparent;color:#a8c4e8!important;border-radius:6px;padding:5px 11px;font-size:.78rem;font-weight:500;}
.stTabs [aria-selected="true"]{background:#1a3a70!important;color:#ffffff!important;font-weight:600!important;}
.tli{border-left:3px solid #1e3a70;padding:5px 0 5px 13px;margin-bottom:5px;position:relative;}
.tli::before{content:'';position:absolute;left:-7px;top:9px;width:10px;height:10px;
    background:#4fc3f7;border-radius:50%;border:2px solid #071228;}
.td{color:#7fa8d4;font-size:.72rem;font-weight:500;}
.tt{color:#ffffff;font-weight:600;font-size:.88rem;}
.tm{color:#c8d8f0;font-size:.75rem;margin-top:1px;}
.ac{padding:12px 16px;border-radius:8px;margin-bottom:7px;border-left:4px solid;
    font-size:.86rem;font-weight:400;line-height:1.5;}
.ac b{color:#ffffff!important;font-weight:700;}
.ac span{color:#e0ecff!important;}
.ac-red{background:rgba(220,38,38,.18);border-color:#ef4444;color:#fca5a5;}
.ac-red span{color:#fecaca!important;}
.ac-yellow{background:rgba(234,179,8,.15);border-color:#eab308;color:#fde68a;}
.ac-yellow span{color:#fef08a!important;}
.ac-green{background:rgba(34,197,94,.15);border-color:#22c55e;color:#a7f3d0;}
.ac-green span{color:#bbf7d0!important;}
.ac-blue{background:rgba(59,130,246,.15);border-color:#3b82f6;color:#bfdbfe;}
.ac-blue span{color:#dbeafe!important;}
.rb{background:#0a1628;border:1px solid #1e3a70;border-radius:10px;padding:18px;
    font-family:'Courier New',monospace;font-size:.82rem;color:#e0ecff;white-space:pre-wrap;line-height:1.6;}
div[data-testid="stDataFrame"] *{font-size:.81rem!important;color:#e0ecff!important;}
div[data-testid="stDataFrame"] th{background:#0d2250!important;color:#a8c4e8!important;font-weight:600!important;}
.drill-tag{background:#0d2250;border-radius:6px;padding:8px 12px;margin-bottom:4px;
    border-left:3px solid #4fc3f7;color:#ffffff;font-weight:600;font-size:.88rem;}
.drill-sub{padding:3px 0 3px 22px;color:#a8c4e8;font-size:.79rem;}
</style>""", unsafe_allow_html=True)

# ── DEPARA ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_depara():
    try:
        return pd.read_excel("https://raw.githubusercontent.com/breznicek1/close-the-loop-eb/main/depara_lideranca.xlsx")
    except:
        return pd.DataFrame(columns=["AgentIdentity","Depara Nome","Depara Lider"])

df_dep = load_depara()
def nome_ag(e): r=df_dep[df_dep["AgentIdentity"]==e]; return r["Depara Nome"].iloc[0] if len(r)>0 else str(e).split("@")[0].replace("%40","_").split("_")[0].replace("."," ").title()
def lider_ag(e): r=df_dep[df_dep["AgentIdentity"]==e]; return r["Depara Lider"].iloc[0] if len(r)>0 else "—"

# ── SUPABASE CTL ──
@st.cache_data(ttl=300, show_spinner=False)
def load_ctl(di, df_):
    try:
        from supabase import create_client
        sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
        res = sb.table("ctlloop_analise")\
            .select("ticket_id,agente,data_ticket,analise_csat,oportunidade,status_ctl,lider,observacao")\
            .gte("data_ticket", str(di)).lte("data_ticket", str(df_)+"T23:59:59").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

# ── HELPERS ──
CORES = {"Core":"#4fc3f7","VIP":"#9775fa","VUPI":"#ff7043","URA":"#69db7c","Outros":"#adb5bd"}

def kpi(lbl,val,pct=None,cls=""):
    p=f'<div class="kp">{pct}</div>' if pct else ""
    return f'<div class="kc {cls}"><div class="kl">{lbl}</div><div class="kv">{val}</div>{p}</div>'

def to_xl(d):
    b=io.BytesIO()
    with pd.ExcelWriter(b,engine="openpyxl") as w: d.to_excel(w,index=False)
    return b.getvalue()

def hm_fig(piv, key=""):
    fig = go.Figure(go.Heatmap(
        z=piv.values, x=[str(c) for c in piv.columns], y=piv.index.tolist(),
        colorscale=[[0,"#071228"],[0.3,"#1a3a70"],[0.65,"#e08080"],[1,"#c0392b"]],
        showscale=False, text=piv.values, texttemplate="%{text}",
        textfont={"size":9,"color":"white"},
        hovertemplate="%{y} | %{x}: %{z}<extra></extra>",
    ))
    fig.update_layout(height=max(300,len(piv)*23+80), margin=dict(l=200,r=20,t=40,b=60),
        paper_bgcolor="#071228", plot_bgcolor="#071228",
        font=dict(color="#e0ecff",size=10),
        xaxis=dict(side="top",tickangle=-45,tickfont=dict(size=9,color="#a8c4e8")),
        yaxis=dict(tickfont=dict(size=10,color="#e0ecff")))
    return fig

def render_hm(piv_raw, key_dl="dl", show_chart=False):
    piv = piv_raw.copy()
    piv["Total"] = piv.sum(axis=1)
    piv = piv.sort_values("Total", ascending=False)
    piv = piv[["Total"]+[c for c in piv.columns if c!="Total"]]
    st.dataframe(piv, use_container_width=True)
    st.download_button("⬇️ Download Excel", to_xl(piv.reset_index()), f"{key_dl}.xlsx", key=key_dl)
    if show_chart:
        st.plotly_chart(hm_fig(piv.drop(columns=["Total"])), use_container_width=True, key=f"hm_{key_dl}")

def pf(x): return f"{x:.1%}" if pd.notna(x) and x is not None else "—"

def drill_tag_subtag(df_g, key_prefix="drill"):
    """Tabela TAG1 → SubTag como linhas indentadas numa única tabela."""
    if df_g.empty:
        st.info("Sem dados.")
        return
    tags = df_g.groupby("Depara_TAG1").agg(
        Qtd=("sequentialId","count"),
        CSAT=("humanConversationEvaluation",lambda x:x.isin(["4","5"]).sum()),
        Aval=("humanConversationEvaluation",lambda x:x.isin(["1","2","3","4","5"]).sum()),
        TME=("TME_segundos","mean"), TMA=("TMA_segundos","mean"),
    ).reset_index().sort_values("Qtd",ascending=False)
    tot = tags["Qtd"].sum()
    rows = []
    for _, rt in tags.iterrows():
        pct = rt["Qtd"]/tot*100 if tot>0 else 0
        cs  = rt["CSAT"]/rt["Aval"] if rt["Aval"]>0 else None
        rows.append({
            "Nível": f"▶ {rt['Depara_TAG1']}",
            "Qtd": int(rt["Qtd"]), "%": f"{pct:.1f}%",
            "% CSAT": pf(cs), "TME": fmt_time(rt["TME"]), "TMA": fmt_time(rt["TMA"])
        })
        subs = df_g[df_g["Depara_TAG1"]==rt["Depara_TAG1"]].groupby("Depara_SubTag").agg(
            Qtd=("sequentialId","count"),
            CSAT=("humanConversationEvaluation",lambda x:x.isin(["4","5"]).sum()),
            Aval=("humanConversationEvaluation",lambda x:x.isin(["1","2","3","4","5"]).sum()),
            TME=("TME_segundos","mean"), TMA=("TMA_segundos","mean"),
        ).reset_index().sort_values("Qtd",ascending=False)
        for _, rs in subs.iterrows():
            pct_s = rs["Qtd"]/rt["Qtd"]*100 if rt["Qtd"]>0 else 0
            cs_s  = rs["CSAT"]/rs["Aval"] if rs["Aval"]>0 else None
            rows.append({
                "Nível": f"    ↳ {rs['Depara_SubTag']}",
                "Qtd": int(rs["Qtd"]), "%": f"{pct_s:.1f}%",
                "% CSAT": pf(cs_s), "TME": fmt_time(rs["TME"]), "TMA": fmt_time(rs["TMA"])
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("### 📅 Período")
    ini_def,fim_def = default_dates()
    data_inicio = st.date_input("De",  value=ini_def, key="dt_i")
    data_fim    = st.date_input("Até", value=fim_def, key="dt_f")
    st.markdown("---")
    st.markdown("### 📡 Canal / Fila")
    canais_sel = st.multiselect("Selecione",["Core","VIP","VUPI","URA","Outros"],default=["Core","VIP","VUPI"])
    st.markdown("---")
    lideres_disp = sorted(df_dep["Depara Lider"].dropna().unique().tolist()) if len(df_dep)>0 else []
    lider_global = st.multiselect("👤 Liderança",["Todos"]+lideres_disp,default=["Todos"])
    lider_ativo  = None if ("Todos" in lider_global or not lider_global) else lider_global
    st.markdown("---")
    filtro_tag   = st.text_input("🏷️ Filtro TAG", placeholder="ex: Saque Recusado")
    st.markdown("---")
    filtro_cpf   = st.text_input("🔍 CPF")
    filtro_email = st.text_input("✉️ E-mail")
    st.markdown("---")
    st.caption(f"👤 {st.session_state.get('usuario','')} · {st.session_state.get('perfil','')}")
    if st.button("Sair"):
        for k in ["logado","usuario","perfil"]: st.session_state.pop(k,None)
        st.rerun()

params = {"data_inicio":str(data_inicio),"data_fim":str(data_fim)+" 23:59:59"}

# ── CARGA ──
@st.cache_data(ttl=300, show_spinner="Carregando dados...")
def load_base(di,df_): return run_query(SQL_BASE_GERAL,{"data_inicio":str(di),"data_fim":str(df_)+" 23:59:59"})
@st.cache_data(ttl=300, show_spinner=False)
def load_rec(di,df_):  return run_query(SQL_RECHAMADA, {"data_inicio":str(di),"data_fim":str(df_)+" 23:59:59"})
@st.cache_data(ttl=300, show_spinner=False)
def load_n1_(di,df_):  return run_query(SQL_N1,        {"data_inicio":str(di),"data_fim":str(df_)+" 23:59:59"})

with st.spinner("Carregando dados..."):
    df_raw = load_base(data_inicio,data_fim)
    df_rec = load_rec(data_inicio,data_fim)
    df_n1  = load_n1_(data_inicio,data_fim)
    df_ctl = load_ctl(data_inicio,data_fim)

# ── FILTROS ──
def aplica(d):
    if canais_sel: d=d[d["Depara_Fila"].isin(canais_sel)]
    if filtro_tag: d=d[d["Depara_TAG1"].str.contains(filtro_tag,case=False,na=False)|d["Depara_SubTag"].str.contains(filtro_tag,case=False,na=False)]
    if lider_ativo:
        ags=df_dep[df_dep["Depara Lider"].isin(lider_ativo)]["AgentIdentity"].tolist()
        d=d[d["humanAgent"].isin(ags)]
    return d

df      = aplica(df_raw.copy())
df_rec_f= df_rec[df_rec["Depara_Fila"].isin(canais_sel)].copy() if canais_sel else df_rec.copy()
# N1 URA: não filtrar por canal (URA pode não estar selecionado)
df_n1_f = df_n1.copy()

if not df.empty:
    df["Nome_Ag"] = df["humanAgent"].apply(nome_ag)
    df["Lider"]   = df["humanAgent"].apply(lider_ag)
    df["Hora_int"]= pd.to_numeric(df["Inicio_Hora"].str[:2],errors="coerce")

# ── CTL MAPS ──
inove_map={}; ctl_feitos=ctl_cliente=ctl_inove=ctl_estrela=ctl_total=0
ctl_ticket_map = {}  # ticket_id -> {analise_csat, observacao, lider}
if not df_ctl.empty and "agente" in df_ctl.columns:
    ctl_total=len(df_ctl)
    ctl_feitos=(df_ctl["status_ctl"]=="Feito").sum()
    ctl_cliente=(df_ctl["analise_csat"]=="Cliente Discorda").sum()
    ctl_inove=(df_ctl["analise_csat"]=="Inove").sum()
    ctl_estrela=(df_ctl["analise_csat"]=="EstrelaBet").sum()
    ig=df_ctl[df_ctl["analise_csat"]=="Inove"].groupby("agente").size().reset_index(name="I")
    tg2=df_ctl.groupby("agente").size().reset_index(name="T")
    ct=ig.merge(tg2,on="agente",how="outer").fillna(0)
    ct["pct"]=ct["I"]/ct["T"].replace(0,np.nan)
    inove_map=dict(zip(ct["agente"],ct["pct"]))
    # mapa ticket -> avaliação CTL
    for _,r in df_ctl.iterrows():
        ctl_ticket_map[str(r.get("ticket_id",""))] = {
            "analise_csat": r.get("analise_csat",""),
            "observacao":   r.get("observacao",""),
            "lider":        r.get("lider",""),
        }

# ── MÉTRICAS ──
def calc_m(dg):
    t=len(dg)
    if t==0: return {}
    inat=(dg["Deparas_Tickets"]=="Inatividade").sum()
    perd=(dg["Deparas_Tickets"]=="Perdido").sum()
    aval=dg["humanConversationEvaluation"].isin(["1","2","3","4","5"]).sum()
    csat=dg["humanConversationEvaluation"].isin(["4","5"]).sum()
    dsat=dg["humanConversationEvaluation"].isin(["1","2"]).sum()
    ns=(dg["TME_segundos"]<60).sum()
    tme=dg["TME_segundos"].mean(); tmpr=dg["TMPR_segundos"].mean(); tma=dg["TMA_segundos"].mean()
    # Filtra rechamada pelos sequentialId do grupo — garante cálculo correto por dia/semana/fila
    if "sequentialId" in dg.columns and not df_rec_f.empty and "sequentialId" in df_rec_f.columns:
        ids = dg["sequentialId"].astype(str).tolist()
        dr = df_rec_f[df_rec_f["sequentialId"].astype(str).isin(ids)]
    elif "Depara_Fila" in dg.columns:
        filas=dg["Depara_Fila"].unique().tolist()
        dr=df_rec_f[df_rec_f["Depara_Fila"].isin(filas)]
    else: dr=df_rec_f
    rec=int(dr["Eh_Rechamada"].sum()) if len(dr)>0 else 0
    fcr=int(dr["Eh_FCR"].sum()) if len(dr)>0 else 0
    rb=len(dr) if len(dr)>0 else 1
    return dict(T=t,Inat=inat,Perd=perd,Aval=aval,CSAT=csat,DSAT=dsat,NS=ns,
                pFCR=fcr/rb,pRec=rec/rb,pNS=ns/t,pInat=inat/t,pPerd=perd/t,
                pCSAT=csat/aval if aval>0 else None,pRR=aval/t,TME=tme,TMPR=tmpr,TMA=tma)

# ════════════════════════════════════════
tabs = st.tabs(["📊 Weekly","⏰ Abertura Dia","🔥 Intra-Hora","😊 CSAT",
                "👤 Operadores","🎯 Estratégica","💬 DSATs & CTL",
                "🔍 Consulta Cliente","⚡ Insights","📋 Report VIP","📓 Diário + IA"])

# ── ABA 1: WEEKLY ──
with tabs[0]:
    st.markdown('<div class="ph"><span class="pt">ABERTURA DIA — Weekly</span><span class="pl">W●INOVE</span></div>',unsafe_allow_html=True)
    if df.empty: st.warning("Sem dados.")
    else:
        rows=[]
        for fila in sorted(df["Depara_Fila"].unique()):
            df_f=df[df["Depara_Fila"]==fila]; m=calc_m(df_f)
            rows.append({"Fila":f"▶ {fila}",**m})
            for sem in sorted(df_f["Semana"].unique()):
                df_s=df_f[df_f["Semana"]==sem]; ms=calc_m(df_s)
                rows.append({"Fila":f"  {sem}",**ms})
                # dias dentro da semana
                for dia in sorted(df_s["Depara_Data"].unique()):
                    df_d=df_s[df_s["Depara_Data"]==dia]; md=calc_m(df_d)
                    dia_fmt=str(dia)[-5:] if len(str(dia))>=5 else str(dia)
                    rows.append({"Fila":f"    {dia_fmt}",**md})
        mg=calc_m(df); rows.append({"Fila":"Total",**mg})
        d=pd.DataFrame(rows); out=pd.DataFrame()
        out["Fila"]=d["Fila"]; out["Tickets"]=d["T"]
        out["% FCR"]=d["pFCR"].apply(pf); out["% Rechamada"]=d["pRec"].apply(pf)
        out["% NS"]=d["pNS"].apply(pf); out["% Inat"]=d["pInat"].apply(pf); out["% Perd"]=d["pPerd"].apply(pf)
        out["Qtd Aval"]=d["Aval"]; out["Qtd CSAT"]=d["CSAT"]; out["Qtd DSAT"]=d["DSAT"]
        out["% CSAT"]=d["pCSAT"].apply(pf); out["% RR"]=d["pRR"].apply(pf)
        out["TME"]=d["TME"].apply(fmt_time); out["TMPR"]=d["TMPR"].apply(fmt_time); out["TMA"]=d["TMA"].apply(fmt_time)
        st.dataframe(out,use_container_width=True,hide_index=True,height=460)
        st.download_button("⬇️ Download Excel",to_xl(out),"weekly.xlsx",key="dl_weekly")
        st.markdown("#### Drill-down por TAG")
        drill_tag_subtag(df, key_prefix="weekly_drill")

# ── ABA 2: ABERTURA DIA ──
with tabs[1]:
    st.markdown('<div class="ph"><span class="pt">ABERTURA DIA — Tempos & Volume</span><span class="pl">W●INOVE</span></div>',unsafe_allow_html=True)
    if df.empty: st.warning("Sem dados.")
    else:
        met=st.radio("Métrica",["TME","TMPR","TMA"],horizontal=True,key="met_ab")
        col_m={"TME":"TME_segundos","TMPR":"TMPR_segundos","TMA":"TMA_segundos"}[met]
        grp=df.groupby(["Hora_int","Depara_Fila"])[col_m].mean().reset_index(); grp["min"]=grp[col_m]/60
        fig=go.Figure()
        for fila in grp["Depara_Fila"].unique():
            sub=grp[grp["Depara_Fila"]==fila]
            fig.add_trace(go.Scatter(x=sub["Hora_int"],y=sub["min"],mode="lines+markers",name=fila,
                line=dict(color=CORES.get(fila,"#aaa"),width=2.5),marker=dict(size=7),
                hovertemplate=f"<b>{fila}</b><br>Hora: %{{x}}h<br>{met}: %{{y:.1f}} min<extra></extra>"))
        fig.update_layout(title=f"{met} médio por hora",paper_bgcolor="#071228",plot_bgcolor="#071228",
            font=dict(color="#e0ecff",size=12),height=320,
            xaxis=dict(tickmode="linear",dtick=1,title="Hora",tickfont=dict(size=11,color="#c8d8f0"),gridcolor="#1a2f52"),
            yaxis=dict(title=f"{met} (min)",tickfont=dict(size=11,color="#c8d8f0"),gridcolor="#1a2f52"),
            legend=dict(bgcolor="#0d1b3e",bordercolor="#1e3a70",borderwidth=1,font=dict(color="#e0ecff",size=12)),
            margin=dict(l=60,r=20,t=50,b=40))
        st.plotly_chart(fig,use_container_width=True,key="chart_tme")

        st.markdown(f"#### {met} por Fila × Hora")
        pv=df.groupby(["Depara_Fila","Hora_int"])[col_m].mean().reset_index()
        pv["fmt"]=pv[col_m].apply(fmt_time)
        tbl=pv.pivot(index="Depara_Fila",columns="Hora_int",values="fmt").fillna("—")
        tbl.columns=[f"{int(c):02d}:00" for c in tbl.columns]
        st.dataframe(tbl,use_container_width=True)

        st.markdown("#### Volume por TAG × Hora")
        vol=df.groupby(["Depara_TAG1","Hora_int"]).size().reset_index(name="Qtd")
        piv=vol.pivot(index="Depara_TAG1",columns="Hora_int",values="Qtd").fillna(0).astype(int)
        piv.columns=[f"{int(c):02d}:00" for c in piv.columns]
        render_hm(piv,key_dl="dl_vol_hora")

# ── ABA 3: INTRA-HORA ──
with tabs[2]:
    st.markdown('<div class="ph"><span class="pt">ANÁLISE INTRA-HORA</span><span class="pl">●INOVE</span></div>',unsafe_allow_html=True)
    visao=st.radio("Visão",["TAG × Hora","TAG × Dia","URA (N1)","N1 — Novo Motivo"],horizontal=True)

    if visao=="TAG × Hora":
        if df.empty: st.warning("Sem dados.")
        else:
            vol=df.groupby(["Depara_TAG1","Hora_int"]).size().reset_index(name="Qtd")
            piv=vol.pivot(index="Depara_TAG1",columns="Hora_int",values="Qtd").fillna(0).astype(int)
            piv.columns=[f"{int(c):02d}:00" for c in piv.columns]
            render_hm(piv,key_dl="dl_ih_hora")
    elif visao=="TAG × Dia":
        if df.empty: st.warning("Sem dados.")
        else:
            vol=df.groupby(["Depara_TAG1","Depara_Data"]).size().reset_index(name="Qtd")
            piv=vol.pivot(index="Depara_TAG1",columns="Depara_Data",values="Qtd").fillna(0).astype(int)
            piv.columns=[str(c) for c in piv.columns]
            render_hm(piv,key_dl="dl_ih_dia")
    elif visao=="URA (N1)":
        # URA: usa df_n1 SEM filtro de canal
        df_ura=df_n1[df_n1["Depara_Fila"]=="URA"] if not df_n1.empty else pd.DataFrame()
        if df_ura.empty: st.warning("Sem dados URA no período. Verifique se a tabela n1 tem registros com fila URA.")
        else:
            res=df_ura.groupby("Novo_Motivo").size().reset_index(name="QTD")
            res["%"]=(res["QTD"]/res["QTD"].sum()*100).round(2).astype(str)+"%"
            res=res.sort_values("QTD",ascending=False)
            st.dataframe(res,use_container_width=True,hide_index=True)
            vol=df_ura.groupby(["Novo_Motivo","Hora"]).size().reset_index(name="Qtd")
            piv=vol.pivot(index="Novo_Motivo",columns="Hora",values="Qtd").fillna(0).astype(int)
            piv.columns=[f"{int(c):02d}:00" for c in piv.columns]
            render_hm(piv,key_dl="dl_ura")
    else:
        if df_n1_f.empty: st.warning("Sem dados N1.")
        else:
            vol=df_n1_f.groupby(["Novo_Motivo","Hora"]).size().reset_index(name="Qtd")
            piv=vol.pivot(index="Novo_Motivo",columns="Hora",values="Qtd").fillna(0).astype(int)
            piv.columns=[f"{int(c):02d}:00" for c in piv.columns]
            render_hm(piv,key_dl="dl_n1")

# ── ABA 4: CSAT ──
with tabs[3]:
    st.markdown('<div class="ph"><span class="pt">CSAT — EstrelaBet</span><span class="pl">ESTRELA★BET</span></div>',unsafe_allow_html=True)
    if df.empty: st.warning("Sem dados.")
    else:
        t_at=len(df); t_av=df["humanConversationEvaluation"].isin(["1","2","3","4","5"]).sum()
        t_cs=df["humanConversationEvaluation"].isin(["4","5"]).sum()
        t_ds=df["humanConversationEvaluation"].isin(["1","2"]).sum()
        t_ne=(df["humanConversationEvaluation"]=="3").sum()
        rr=t_av/t_at if t_at>0 else 0; cs_p=t_cs/t_av if t_av>0 else 0
        cs_cls="kr-green" if cs_p>=META_CSAT else ("kr-yellow" if cs_p>=0.80 else "kr-red")
        st.markdown(f"""<div class="kr">
            {kpi("Atendido",f"{t_at:,}")}{kpi("Avaliado",f"{t_av:,}")}
            {kpi("CSAT",f"{t_cs:,}",f"{cs_p:.1%}",cs_cls)}
            {kpi("Neutro",f"{t_ne:,}",f"{t_ne/t_av:.1%}" if t_av>0 else "—")}
            {kpi("DSAT",f"{t_ds:,}",f"{t_ds/t_av:.1%}" if t_av>0 else "—","kr-red" if t_av>0 and t_ds/t_av>0.15 else "")}
            {kpi("Response Rate",f"{rr:.1%}")}
        </div>""",unsafe_allow_html=True)

        lid_csat=st.multiselect("Liderança",["Todos"]+sorted(df["Lider"].dropna().unique().tolist()),default=["Todos"],key="lid_csat")
        df_c=df if "Todos" in lid_csat or not lid_csat else df[df["Lider"].isin(lid_csat)]

        c1,c2=st.columns(2)
        with c1:
            st.markdown("#### Resumo por Dia")
            dg=df_c.groupby("Depara_Data").agg(
                Qtd=("sequentialId","count"),
                Aval=("humanConversationEvaluation",lambda x:x.isin(["1","2","3","4","5"]).sum()),
                CSAT=("humanConversationEvaluation",lambda x:x.isin(["4","5"]).sum()),
            ).reset_index()
            dg["Mês"]=pd.to_datetime(dg["Depara_Data"]).dt.strftime("%b"); dg["Dia"]=pd.to_datetime(dg["Depara_Data"]).dt.day
            dg["% CSAT"]=(dg["CSAT"]/dg["Aval"].replace(0,np.nan)*100).round(1).astype(str)+"%"
            dg["% RR"]=(dg["Aval"]/dg["Qtd"].replace(0,np.nan)*100).round(1).astype(str)+"%"
            out_dia=dg[["Mês","Dia","Qtd","Aval","% CSAT","% RR"]]
            st.dataframe(out_dia,use_container_width=True,hide_index=True,height=340)
            st.download_button("⬇️ Download Dia",to_xl(out_dia),"csat_dia.xlsx",key="dl_csat_dia")
        with c2:
            st.markdown("#### Abertura por Operador")
            og=df_c.groupby("humanAgent").agg(
                Qtd=("sequentialId","count"),
                Aval=("humanConversationEvaluation",lambda x:x.isin(["1","2","3","4","5"]).sum()),
                CSAT=("humanConversationEvaluation",lambda x:x.isin(["4","5"]).sum()),
                TME_a=("TME_segundos","mean"),TMPR_a=("TMPR_segundos","mean"),TMA_a=("TMA_segundos","mean"),
            ).reset_index()
            og["Nome"]=og["humanAgent"].apply(nome_ag); og["Líder"]=og["humanAgent"].apply(lider_ag)
            og["% CSAT"]=(og["CSAT"]/og["Aval"].replace(0,np.nan)*100).round(1).astype(str)+"%"
            og["% RR"]=(og["Aval"]/og["Qtd"].replace(0,np.nan)*100).round(1).astype(str)+"%"
            og["% Inove"]=og["humanAgent"].map(inove_map).apply(lambda x:f"{x:.1%}" if pd.notna(x) else "—")
            og["TME"]=og["TME_a"].apply(fmt_time); og["TMPR"]=og["TMPR_a"].apply(fmt_time); og["TMA"]=og["TMA_a"].apply(fmt_time)
            og=og.sort_values("Qtd",ascending=False)
            out_op=og[["Nome","Líder","Qtd","Aval","% CSAT","% Inove","% RR","TME","TMPR","TMA"]]
            st.dataframe(out_op,use_container_width=True,hide_index=True,height=340)
            st.download_button("⬇️ Download Operadores",to_xl(out_op),"csat_op.xlsx",key="dl_csat_op")

        st.markdown("#### Drill-down por TAG → SubTag")
        drill_tag_subtag(df_c, key_prefix="csat_drill")

# ── ABA 5: OPERADORES ──
with tabs[4]:
    st.markdown('<div class="ph"><span class="pt">VISÃO POR OPERADOR — Feedback</span><span class="pl">●INOVE</span></div>',unsafe_allow_html=True)
    if df.empty: st.warning("Sem dados.")
    else:
        lid_op=st.multiselect("Liderança",["Todos"]+sorted(df["Lider"].dropna().unique().tolist()),default=["Todos"],key="lid_op")
        df_op_f=df if "Todos" in lid_op or not lid_op else df[df["Lider"].isin(lid_op)]
        op_sel=st.selectbox("Selecione o operador",["Todos"]+sorted(df_op_f["Nome_Ag"].dropna().unique().tolist()),key="op_sel")
        df_op=df_op_f if op_sel=="Todos" else df_op_f[df_op_f["Nome_Ag"]==op_sel]

        t_op=len(df_op); av_op=df_op["humanConversationEvaluation"].isin(["1","2","3","4","5"]).sum()
        cs_op=df_op["humanConversationEvaluation"].isin(["4","5"]).sum()
        ds_op=df_op["humanConversationEvaluation"].isin(["1","2"]).sum()
        tme_op=df_op["TME_segundos"].mean(); tma_op=df_op["TMA_segundos"].mean()
        ns_op=(df_op["TME_segundos"]<60).sum()
        cs_pct=cs_op/av_op if av_op>0 else 0
        tma_cls="kr-green" if pd.notna(tma_op) and tma_op<=META_TMA else ("kr-yellow" if pd.notna(tma_op) and tma_op<=META_TMA*1.2 else "kr-red")
        cs_cls2="kr-green" if cs_pct>=META_CSAT else ("kr-yellow" if cs_pct>=0.80 else "kr-red")

        # Inove do operador - busca pelo email mais frequente do agente selecionado
        if op_sel != "Todos" and len(df_op) > 0:
            # pega o email original (humanAgent) do operador selecionado
            agent_emails = df_op["humanAgent"].value_counts()
            agent_email = agent_emails.index[0] if len(agent_emails) > 0 else None
            inove_op = inove_map.get(agent_email, np.nan) if agent_email else np.nan
        else:
            agent_email = None
            # para "Todos": mostra média geral do inove_map para os agentes no grupo
            if inove_map and len(df_op) > 0:
                emails_grupo = df_op["humanAgent"].unique().tolist()
                vals = [inove_map[e] for e in emails_grupo if e in inove_map and pd.notna(inove_map[e])]
                inove_op = np.mean(vals) if vals else np.nan
            else:
                inove_op = np.nan
        inove_cls = "kr-red" if pd.notna(inove_op) and inove_op>0.15 else ("kr-yellow" if pd.notna(inove_op) and inove_op>0.05 else "kr-green")

        # linha 1
        st.markdown(f"""<div class="kr">
            {kpi("Tickets",f"{t_op:,}")}
            {kpi("Avaliações",f"{av_op:,}")}
            {kpi("CSAT",f"{cs_op:,}",f"{cs_pct:.1%}",cs_cls2)}
            {kpi("DSAT",f"{ds_op:,}",f"{ds_op/av_op:.1%}" if av_op>0 else "—")}
            {kpi("% NS",f"{ns_op/t_op:.1%}" if t_op>0 else "—")}
        </div>""",unsafe_allow_html=True)
        # linha 2
        st.markdown(f"""<div class="kr">
            {kpi("TME",fmt_time(tme_op))}
            {kpi("TMA",fmt_time(tma_op),"Meta: 15:00",tma_cls)}
            {kpi("% Inove CTL",f"{inove_op:.1%}" if pd.notna(inove_op) else "—","Condução atend.",inove_cls)}
        </div>""",unsafe_allow_html=True)

        c1,c2=st.columns(2)
        with c1:
            st.markdown("#### Evolução diária — CSAT")
            ev=df_op.groupby("Depara_Data").agg(
                Qtd=("sequentialId","count"),
                CSAT=("humanConversationEvaluation",lambda x:x.isin(["4","5"]).sum()),
                Aval=("humanConversationEvaluation",lambda x:x.isin(["1","2","3","4","5"]).sum()),
            ).reset_index()
            ev["pct"]=ev["CSAT"]/ev["Aval"].replace(0,np.nan)*100
            fig_ev=go.Figure()
            fig_ev.add_trace(go.Bar(x=ev["Depara_Data"],y=ev["Qtd"],name="Tickets",marker_color="#1e3a70",yaxis="y2",opacity=0.6))
            fig_ev.add_trace(go.Scatter(x=ev["Depara_Data"],y=ev["pct"],name="% CSAT",
                line=dict(color="#4fc3f7",width=2.5),mode="lines+markers",marker=dict(size=7)))
            fig_ev.add_hline(y=90,line_dash="dash",line_color="#69db7c",
                annotation_text="Meta 90%",annotation_font_color="#69db7c",annotation_font_size=11)
            fig_ev.update_layout(paper_bgcolor="#071228",plot_bgcolor="#071228",font=dict(color="#e0ecff"),height=280,
                yaxis=dict(title="% CSAT",tickfont=dict(color="#a8c4e8"),gridcolor="#1a2f52"),
                yaxis2=dict(title="Tickets",overlaying="y",side="right",tickfont=dict(color="#a8c4e8")),
                legend=dict(bgcolor="#0d1b3e",font=dict(color="#e0ecff")),margin=dict(l=50,r=50,t=30,b=40))
            st.plotly_chart(fig_ev,use_container_width=True,key="chart_ev")

        with c2:
            st.markdown("#### Produtividade")
            if op_sel=="Todos":
                prod=df_op.groupby("Nome_Ag").agg(
                    Prod=("Deparas_Tickets",lambda x:(x=="Produtivo").sum()),
                    Inat=("Deparas_Tickets",lambda x:(x=="Inatividade").sum()),
                    Perd=("Deparas_Tickets",lambda x:(x=="Perdido").sum()),
                    Tot=("sequentialId","count"),
                ).reset_index()
                for k in ["Prod","Inat","Perd"]: prod[f"p{k}"]=prod[k]/prod["Tot"]
                prod=prod.sort_values("pProd",ascending=True).tail(20)
                fig_pr=go.Figure()
                for k,cor,lbl in [("pProd","#4fc3f7","Produtivo"),("pInat","#ffa726","Inatividade"),("pPerd","#ef5350","Perdido")]:
                    fig_pr.add_trace(go.Bar(y=prod["Nome_Ag"],x=prod[k],name=lbl,orientation="h",
                        marker_color=cor,text=(prod[k]*100).round(1).astype(str)+"%",
                        textposition="inside",textfont=dict(color="white",size=9)))
                fig_pr.update_layout(barmode="stack",height=max(280,len(prod)*20+60),
                    paper_bgcolor="#071228",plot_bgcolor="#071228",font=dict(color="#e0ecff"),
                    xaxis=dict(tickformat=".0%",autorange="reversed",tickfont=dict(color="#a8c4e8")),
                    yaxis=dict(tickfont=dict(color="#e0ecff",size=10)),
                    legend=dict(orientation="h",y=1.05,bgcolor="#0d1b3e",font=dict(color="#e0ecff")),
                    margin=dict(l=140,r=20,t=40,b=20))
                st.plotly_chart(fig_pr,use_container_width=True,key="chart_prod_op")
            else:
                prod_row=df_op["Deparas_Tickets"].value_counts()
                st.metric("Produtivo",f"{prod_row.get('Produtivo',0)} ({prod_row.get('Produtivo',0)/t_op:.1%})")
                st.metric("Inatividade",f"{prod_row.get('Inatividade',0)} ({prod_row.get('Inatividade',0)/t_op:.1%})")
                st.metric("Perdido",f"{prod_row.get('Perdido',0)} ({prod_row.get('Perdido',0)/t_op:.1%})")

        st.markdown("#### Drill-down por TAG → SubTag")
        drill_tag_subtag(df_op, key_prefix="op_drill")

# ── ABA 6: ESTRATÉGICA ──
with tabs[5]:
    st.markdown('<div class="ph"><span class="pt">ANÁLISE ESTRATÉGICA POR TEMA</span><span class="pl">●INOVE</span></div>',unsafe_allow_html=True)
    if df.empty: st.warning("Sem dados.")
    else:
        fc1,fc2=st.columns(2)
        with fc1:
            lid_est=st.multiselect("Liderança",["Todos"]+sorted(df["Lider"].dropna().unique().tolist()),default=["Todos"],key="lid_est")
        df_e=df if "Todos" in lid_est or not lid_est else df[df["Lider"].isin(lid_est)]
        with fc2:
            op_est=st.multiselect("Operador",["Todos"]+sorted(df_e["Nome_Ag"].dropna().unique().tolist()),default=["Todos"],key="op_est")
        if "Todos" not in op_est and op_est: df_e=df_e[df_e["Nome_Ag"].isin(op_est)]

        c1,c2=st.columns([1,1.5])
        with c1:
            prod=df_e.groupby("Nome_Ag").agg(
                Prod=("Deparas_Tickets",lambda x:(x=="Produtivo").sum()),
                Inat=("Deparas_Tickets",lambda x:(x=="Inatividade").sum()),
                Perd=("Deparas_Tickets",lambda x:(x=="Perdido").sum()),
                Tot=("sequentialId","count"),
            ).reset_index()
            for k in ["Prod","Inat","Perd"]: prod[f"p{k}"]=prod[k]/prod["Tot"]
            prod=prod.sort_values("pProd",ascending=True).tail(25)
            fig_p=go.Figure()
            for k,cor,lbl in [("pProd","#4fc3f7","Produtivo"),("pInat","#ffa726","Inatividade"),("pPerd","#ef5350","Perdido")]:
                fig_p.add_trace(go.Bar(y=prod["Nome_Ag"],x=prod[k],name=lbl,orientation="h",
                    marker_color=cor,text=(prod[k]*100).round(1).astype(str)+"%",
                    textposition="inside",textfont=dict(color="white",size=9)))
            fig_p.update_layout(barmode="stack",title="Produtividade",
                height=max(380,len(prod)*21+70),paper_bgcolor="#071228",plot_bgcolor="#071228",
                font=dict(color="#e0ecff"),xaxis=dict(tickformat=".0%",autorange="reversed",tickfont=dict(color="#a8c4e8")),
                yaxis=dict(tickfont=dict(color="#e0ecff",size=10)),
                legend=dict(orientation="h",y=1.05,bgcolor="#0d1b3e",font=dict(color="#e0ecff")),
                margin=dict(l=150,r=20,t=50,b=20))
            st.plotly_chart(fig_p,use_container_width=True,key="chart_prod")
            st.download_button("⬇️ Download",to_xl(prod),"prod.xlsx",key="dl_prod")

        with c2:
            tg=df_e.groupby("Depara_TAG1").agg(
                Qtd=("sequentialId","count"),
                CSAT=("humanConversationEvaluation",lambda x:x.isin(["4","5"]).sum()),
                Aval=("humanConversationEvaluation",lambda x:x.isin(["1","2","3","4","5"]).sum()),
                TME_a=("TME_segundos","mean"),TMPR_a=("TMPR_segundos","mean"),TMA_a=("TMA_segundos","mean"),
            ).reset_index()
            if not df_rec_f.empty and "Depara_TAG1" in df_rec_f.columns:
                rt=df_rec_f.groupby("Depara_TAG1").agg(FCR=("Eh_FCR","sum"),Rec=("Eh_Rechamada","sum"),B=("sequentialId","count")).reset_index()
                tg=tg.merge(rt,on="Depara_TAG1",how="left")
                tg["pFCR"]=tg["FCR"]/tg["B"].replace(0,np.nan); tg["pRec"]=tg["Rec"]/tg["B"].replace(0,np.nan)
            else: tg["pFCR"]=tg["pRec"]=np.nan
            tot=tg["Qtd"].sum()
            tg["%"]=(tg["Qtd"]/tot*100).round(2).astype(str)+"%"
            tg["% CSAT"]=(tg["CSAT"]/tg["Aval"].replace(0,np.nan)*100).round(1).astype(str)+"%"
            tg["% RR"]=(tg["Aval"]/tg["Qtd"].replace(0,np.nan)*100).round(1).astype(str)+"%"
            tg["% FCR"]=tg["pFCR"].apply(pf); tg["% Rec"]=tg["pRec"].apply(pf)
            tg["TME"]=tg["TME_a"].apply(fmt_time); tg["TMPR"]=tg["TMPR_a"].apply(fmt_time); tg["TMA"]=tg["TMA_a"].apply(fmt_time)
            tg=tg.sort_values("Qtd",ascending=False)
            out_tg=tg[["Depara_TAG1","Qtd","%","TME","TMPR","TMA","% CSAT","% RR","% FCR","% Rec"]].rename(columns={"Depara_TAG1":"TAG"})
            st.markdown("#### Resumo por Tema")
            st.dataframe(out_tg,use_container_width=True,hide_index=True,height=460)
            st.download_button("⬇️ Download TAG",to_xl(out_tg),"tag.xlsx",key="dl_tag")

        st.markdown("#### Drill-down TAG → SubTag")
        drill_tag_subtag(df_e, key_prefix="est_drill")

# ── ABA 7: DSATs & CTL ──
with tabs[6]:
    st.markdown('<div class="ph"><span class="pt">DSATs & CLOSE THE LOOP</span><span class="pl">ESTRELA★BET</span></div>',unsafe_allow_html=True)
    df_ds=df[df["humanConversationEvaluation"].isin(["1","2","3"])]
    base_p=max(ctl_total,1)
    st.markdown(f"""<div class="kr">
        {kpi("Qtd DSAT",f"{len(df_ds):,}")}
        {kpi("CTL Feitos",f"{ctl_feitos:,}",f"{ctl_feitos/base_p:.1%}")}
        {kpi("Oport. Cliente",f"{ctl_cliente:,}",f"{ctl_cliente/base_p:.1%}")}
        {kpi("Oport. Inove",f"{ctl_inove:,}",f"{ctl_inove/base_p:.1%}")}
        {kpi("Oport. Estrela",f"{ctl_estrela:,}",f"{ctl_estrela/base_p:.1%}")}
    </div>""",unsafe_allow_html=True)

    if not df_ds.empty:
        vol_ds=df_ds.groupby(["Depara_TAG1","Hora_int"]).size().reset_index(name="Qtd")
        piv_ds=vol_ds.pivot(index="Depara_TAG1",columns="Hora_int",values="Qtd").fillna(0).astype(int)
        piv_ds.columns=[f"{int(c):02d}:00" for c in piv_ds.columns]
        render_hm(piv_ds,key_dl="dl_dsat_hm")
        st.markdown("#### Drill-down TAG → SubTag (DSATs)")
        drill_tag_subtag(df_ds, key_prefix="dsat_drill")
    else: st.info("Nenhum DSAT no período.")

# ── ABA 8: CONSULTA CLIENTE ──
with tabs[7]:
    st.markdown('<div class="ph"><span class="pt">CONSULTA CLIENTE</span><span class="pl">●INOVE</span></div>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1: cpf_in=st.text_input("🔍 CPF",value=filtro_cpf,key="cpf_tab")
    with c2: eml_in=st.text_input("✉️ E-mail",value=filtro_email,key="email_tab")

    if st.button("Buscar histórico",type="primary"):
        if cpf_in or eml_in:
            with st.spinner("Buscando..."):
                df_cli=run_query(SQL_CLIENTE,{
                    "cpf":  f"%{cpf_in}%"  if cpf_in  else None,
                    "email":f"%{eml_in}%" if eml_in else None,
                })
            if df_cli.empty: st.warning("Nenhum registro encontrado.")
            else:
                r=df_cli.iloc[0]
                st.success(f"**{r.get('Nome','—')}** · CPF: `{r.get('CPF','—')}` · Fone: `{r.get('Fone','—')}` · E-mail: `{r.get('Email','—')}`")
                cm1,cm2,cm3=st.columns(3)
                cm1.metric("Total atendimentos",len(df_cli))
                cm2.metric("DSATs",int(df_cli["Avaliacao"].isin(["1","2","3"]).sum()))
                cm3.metric("Positivas",int(df_cli["Avaliacao"].isin(["4","5"]).sum()))

                st.markdown("#### 🗺️ Jornada do Cliente")
                df_j=df_cli.sort_values("Data")
                emoji_m={"1":"😡","2":"😠","3":"😐","4":"😊","5":"😄"}
                html='<div style="padding:8px">'
                for _,rw in df_j.iterrows():
                    nota=str(rw.get("Avaliacao","")) if pd.notna(rw.get("Avaliacao")) else "—"
                    em=emoji_m.get(nota,"⬜")
                    sub=str(rw.get("SubTag","")) if pd.notna(rw.get("SubTag")) else "—"
                    fila=str(rw.get("Fila","")) if pd.notna(rw.get("Fila")) else "—"
                    seq=str(rw.get("sequentialId","")) if pd.notna(rw.get("sequentialId")) else "—"
                    n2v=str(rw.get("N2_Zendesk","")) if pd.notna(rw.get("N2_Zendesk")) else None
                    n2=f" · N2: <code>{n2v}</code>" if n2v else ""
                    tme_f=fmt_time(rw.get("TME_seg")) if pd.notna(rw.get("TME_seg")) else "—"
                    tma_f=fmt_time(rw.get("TMA_seg")) if pd.notna(rw.get("TMA_seg")) else "—"
                    # CTL do ticket
                    ctl_info = ctl_ticket_map.get(seq,{})
                    ctl_html=""
                    if ctl_info and ctl_info.get("analise_csat"):
                        ctl_cls={"Inove":"#ffd43b","EstrelaBet":"#4fc3f7","Cliente Discorda":"#ff6b6b"}.get(ctl_info["analise_csat"],"#a8c4e8")
                        ctl_html=f' · <span style="color:{ctl_cls};font-weight:600">CTL: {ctl_info["analise_csat"]}</span>'
                        if ctl_info.get("observacao"): ctl_html+=f' <span style="color:#a8c4e8;font-size:.73rem">"{ctl_info["observacao"][:60]}..."</span>'
                    html+=f"""<div class="tli">
                        <div class="td">{rw.get('Data','—')} · Ticket: <b>#{seq}</b></div>
                        <div class="tt">{sub} <span style="color:#7fa8d4;font-weight:400">({fila})</span></div>
                        <div class="tm">TME: {tme_f} · TMA: {tma_f} · Avaliação: {em} {nota}{n2}{ctl_html}</div>
                    </div>"""
                html+="</div>"
                st.markdown(html,unsafe_allow_html=True)
                st.download_button("⬇️ Download histórico",to_xl(df_cli),"historico.xlsx",key="dl_cli")

    st.markdown("---")
    st.markdown("#### Clientes com mais atendimentos no período")
    df_rank=run_query(SQL_CLIENTES_RECORRENTES,params)
    if not df_rank.empty:
        st.dataframe(df_rank,use_container_width=True,hide_index=True,height=300)

# ── ABA 9: INSIGHTS ──
with tabs[8]:
    st.markdown('<div class="ph"><span class="pt">⚡ INSIGHTS & ALERTAS</span><span class="pl">●INOVE</span></div>',unsafe_allow_html=True)
    if df.empty: st.warning("Sem dados.")
    else:
        med_tme=df["TME_segundos"].mean(); std_tme=df["TME_segundos"].std()
        med_tma=df["TMA_segundos"].mean(); std_tma=df["TMA_segundos"].std()

        # ── LINHA 1: Destaques e Ofensores TMA ──
        c1,c2=st.columns(2)
        with c1:
            st.markdown('<h3 style="color:#a7f3d0;font-size:1.1rem;margin-bottom:12px">🏆 Destaques TMA <span style="color:#86efac;font-size:.78rem">(abaixo de 15:00)</span></h3>',unsafe_allow_html=True)
            ota=df.groupby("Nome_Ag")["TMA_segundos"].agg(["mean","count"]).reset_index()
            ota.columns=["Nome","med","Qtd"]; ota=ota[ota["Qtd"]>=10]
            dest_tma=ota[ota["med"]<=META_TMA].sort_values("med")
            if dest_tma.empty: st.markdown('<div class="ac ac-yellow">⚠️ Nenhum operador dentro da meta TMA</div>',unsafe_allow_html=True)
            else:
                for _,r in dest_tma.head(8).iterrows():
                    exc=((META_TMA-r["med"])/META_TMA*100)
                    st.markdown(f'<div class="ac ac-green"><b style="color:#ffffff">{r["Nome"]}</b><br><span style="color:#a7f3d0">TMA: {fmt_time(r["med"])} &nbsp;·&nbsp; {exc:.0f}% abaixo da meta &nbsp;·&nbsp; {int(r["Qtd"])} tickets</span></div>',unsafe_allow_html=True)

        with c2:
            st.markdown('<h3 style="color:#fca5a5;font-size:1.1rem;margin-bottom:12px">⚠️ Ofensores TMA <span style="color:#fde68a;font-size:.78rem">(Meta: 15:00)</span></h3>',unsafe_allow_html=True)
            off2=ota[ota["med"]>META_TMA].sort_values("med",ascending=False)
            if off2.empty: st.markdown('<div class="ac ac-green">✅ Todos dentro da meta TMA (15:00)</div>',unsafe_allow_html=True)
            else:
                for _,r in off2.head(8).iterrows():
                    exc=((r["med"]-META_TMA)/META_TMA*100)
                    cls="ac-red" if r["med"]>META_TMA*1.3 else "ac-yellow"
                    ic="🔴" if r["med"]>META_TMA*1.3 else "🟡"
                    st.markdown(f'<div class="ac {cls}">{ic} <b style="color:#ffffff">{r["Nome"]}</b><br><span>TMA: {fmt_time(r["med"])} &nbsp;·&nbsp; +{exc:.0f}% da meta &nbsp;·&nbsp; {int(r["Qtd"])} tickets</span></div>',unsafe_allow_html=True)

        st.markdown("---")
        # ── LINHA 2: Destaques e Ofensores CSAT ──
        c1,c2=st.columns(2)
        with c1:
            st.markdown('<h3 style="color:#a7f3d0;font-size:1.1rem;margin-bottom:12px">🏆 Destaques CSAT <span style="color:#86efac;font-size:.78rem">(Meta: 90%)</span></h3>',unsafe_allow_html=True)
            oc=df.groupby("Nome_Ag").agg(Aval=("humanConversationEvaluation",lambda x:x.isin(["1","2","3","4","5"]).sum()),
                CSAT=("humanConversationEvaluation",lambda x:x.isin(["4","5"]).sum())).reset_index()
            oc=oc[oc["Aval"]>=10]; oc["pct"]=oc["CSAT"]/oc["Aval"]
            dest=oc[oc["pct"]>=META_CSAT].sort_values("pct",ascending=False)
            if dest.empty: st.markdown('<div class="ac ac-yellow">⚠️ Nenhum operador atingiu 90% no período</div>',unsafe_allow_html=True)
            else:
                for _,r in dest.head(8).iterrows():
                    st.markdown(f'<div class="ac ac-green"><b style="color:#ffffff">{r["Nome_Ag"]}</b><br><span style="color:#a7f3d0">CSAT: {r["pct"]:.1%} &nbsp;·&nbsp; {int(r["Aval"])} avaliações</span></div>',unsafe_allow_html=True)

        with c2:
            st.markdown('<h3 style="color:#fca5a5;font-size:1.1rem;margin-bottom:12px">😟 Ofensores CSAT <span style="color:#fca5a5;font-size:.78rem">(abaixo de 70%)</span></h3>',unsafe_allow_html=True)
            off_c=oc[oc["pct"]<0.70].sort_values("pct")
            if off_c.empty: st.markdown('<div class="ac ac-green">✅ Todos com CSAT ≥ 70%</div>',unsafe_allow_html=True)
            else:
                for _,r in off_c.head(8).iterrows():
                    cls="ac-red" if r["pct"]<0.60 else "ac-yellow"; ic="🔴" if r["pct"]<0.60 else "🟡"
                    st.markdown(f'<div class="ac {cls}">{ic} <b style="color:#ffffff">{r["Nome_Ag"]}</b><br><span>CSAT: {r["pct"]:.1%} &nbsp;·&nbsp; {int(r["Aval"])} avaliações</span></div>',unsafe_allow_html=True)

        st.markdown("---")
        # ── LINHA 3: CTL Ofensores e Destaques ──
        c1,c2=st.columns(2)
        with c1:
            st.markdown('<h3 style="color:#fca5a5;font-size:1.1rem;margin-bottom:12px">🔴 Ofensores CTL <span style="color:#fde68a;font-size:.78rem">(maior % Inove = pior condução)</span></h3>',unsafe_allow_html=True)
            if inove_map:
                ctl_df=pd.DataFrame([(k,v) for k,v in inove_map.items() if pd.notna(v)],columns=["email","pct_inove"])
                ctl_df["Nome"]=ctl_df["email"].apply(nome_ag)
                ctl_df=ctl_df.sort_values("pct_inove",ascending=False)
                off_ctl=ctl_df[ctl_df["pct_inove"]>0.10]
                if off_ctl.empty: st.markdown('<div class="ac ac-green">✅ Nenhum operador com % Inove acima de 10%</div>',unsafe_allow_html=True)
                else:
                    for _,r in off_ctl.head(8).iterrows():
                        st.markdown(f'<div class="ac ac-red">🔴 <b style="color:#ffffff">{r["Nome"]}</b><br><span>% Inove: {r["pct_inove"]:.1%} — falha na condução do atendimento</span></div>',unsafe_allow_html=True)
            else:
                st.markdown('<div class="ac ac-yellow">⚠️ Dados CTL não disponíveis no período</div>',unsafe_allow_html=True)

        with c2:
            st.markdown('<h3 style="color:#a7f3d0;font-size:1.1rem;margin-bottom:12px">🏆 Destaques CTL <span style="color:#86efac;font-size:.78rem">(menor % Inove = melhor condução)</span></h3>',unsafe_allow_html=True)
            if inove_map:
                dest_ctl=ctl_df[ctl_df["pct_inove"]<=0.05].sort_values("pct_inove")
                if dest_ctl.empty: st.markdown('<div class="ac ac-yellow">⚠️ Nenhum operador com % Inove ≤ 5%</div>',unsafe_allow_html=True)
                else:
                    for _,r in dest_ctl.head(8).iterrows():
                        st.markdown(f'<div class="ac ac-green"><b style="color:#ffffff">{r["Nome"]}</b><br><span style="color:#a7f3d0">% Inove: {r["pct_inove"]:.1%} — boa condução de atendimento</span></div>',unsafe_allow_html=True)
            else:
                st.markdown('<div class="ac ac-yellow">⚠️ Dados CTL não disponíveis no período</div>',unsafe_allow_html=True)

        st.markdown("---")
        # ── LINHA 4: Rechamada + Picos ──
        c1,c2=st.columns(2)
        with c1:
            st.markdown('<h3 style="color:#bfdbfe;font-size:1.1rem;margin-bottom:12px">🔁 Rechamada por TAG (outliers)</h3>',unsafe_allow_html=True)
            if not df_rec_f.empty and "Depara_TAG1" in df_rec_f.columns:
                rt2=df_rec_f.groupby("Depara_TAG1").agg(Rec=("Eh_Rechamada","sum"),B=("sequentialId","count")).reset_index()
                rt2=rt2[rt2["B"]>=20]; rt2["pct"]=rt2["Rec"]/rt2["B"]
                mr=rt2["pct"].mean(); sr=rt2["pct"].std()
                outr=rt2[rt2["pct"]>(mr+sr)].sort_values("pct",ascending=False)
                if outr.empty: st.markdown('<div class="ac ac-green">✅ Nenhuma TAG com rechamada anômala</div>',unsafe_allow_html=True)
                else:
                    for _,r in outr.head(8).iterrows():
                        st.markdown(f'<div class="ac ac-yellow">🟡 <b style="color:#ffffff">{r["Depara_TAG1"]}</b><br><span>{r["pct"]:.1%} rechamada &nbsp;·&nbsp; média: {mr:.1%} &nbsp;·&nbsp; {int(r["B"])} tickets</span></div>',unsafe_allow_html=True)

        with c2:
            st.markdown('<h3 style="color:#bfdbfe;font-size:1.1rem;margin-bottom:12px">📈 Picos de Volume (outliers diários)</h3>',unsafe_allow_html=True)
            vdt=df.groupby(["Depara_TAG1","Depara_Data"]).size().reset_index(name="Qtd")
            st2=vdt.groupby("Depara_TAG1")["Qtd"].agg(["mean","std"]).reset_index()
            st2.columns=["TAG","med","std"]
            mx=vdt.groupby("Depara_TAG1")["Qtd"].max().reset_index(name="max"); mx.columns=["TAG","max"]
            st2=st2.merge(mx,on="TAG"); st2["lim"]=st2["med"]+2*st2["std"]
            picos=st2[st2["max"]>st2["lim"]].sort_values("max",ascending=False)
            if picos.empty: st.markdown('<div class="ac ac-green">✅ Nenhum pico de volume</div>',unsafe_allow_html=True)
            else:
                for _,r in picos.head(8).iterrows():
                    d=((r["max"]-r["med"])/max(r["med"],1)*100)
                    st.markdown(f'<div class="ac ac-yellow">🟡 <b style="color:#ffffff">{r["TAG"]}</b><br><span>Pico: {int(r["max"])}/dia &nbsp;·&nbsp; +{d:.0f}% da média ({r["med"]:.0f}/dia)</span></div>',unsafe_allow_html=True)

        st.markdown("---")
        # ── COMPARATIVO: período filtrado vs período anterior equivalente ──
        st.markdown('<h3 style="color:#e0ecff;font-size:1.1rem;margin-bottom:12px">📅 Comparativo — Período Filtrado vs Anterior Equivalente</h3>',unsafe_allow_html=True)
        # calcula período anterior com mesmo número de dias
        n_dias = (data_fim - data_inicio).days + 1
        ini_ant = data_inicio - timedelta(days=n_dias)
        fim_ant = data_inicio - timedelta(days=1)

        def fperi(di, df_):
            if df_raw.empty: return pd.DataFrame()
            return df_raw[
                (pd.to_datetime(df_raw["Depara_Data"]) >= pd.Timestamp(di)) &
                (pd.to_datetime(df_raw["Depara_Data"]) <= pd.Timestamp(df_))
            ]

        df_at = df.copy()  # período atual já filtrado
        df_ant = aplica(fperi(ini_ant, fim_ant))  # período anterior com mesmos filtros

        def skpi2(lbl, va, vp, maior_melhor=True, fmt_fn=None):
            if fmt_fn:
                fa = fmt_fn(va); fp = fmt_fn(vp)
            elif isinstance(va, float) and va < 2:
                fa = f"{va:.1%}"; fp = f"{vp:.1%}"
            else:
                fa = f"{int(va):,}"; fp = f"{int(vp):,}"
            delta = va - vp
            positivo = delta >= 0
            bom = positivo if maior_melhor else not positivo
            cor = "#69db7c" if bom else "#ff6b6b"
            if fmt_fn:
                ds = f"+{fmt_fn(abs(delta))}" if positivo else f"-{fmt_fn(abs(delta))}"
            elif isinstance(va, float) and va < 2:
                ds = (f"+{delta:.1%}" if positivo else f"{delta:.1%}")
            else:
                ds = (f"+{int(delta):,}" if positivo else f"{int(delta):,}")
            return f'<div class="kc"><div class="kl">{lbl}</div><div class="kv">{fa}</div><div class="kp" style="color:{cor}">{ds} vs período ant.</div><div style="color:#7fa8d4;font-size:.68rem">ant: {fp}</div></div>'

        t_at2=len(df_at); t_ant=len(df_ant)
        av_at=df_at["humanConversationEvaluation"].isin(["1","2","3","4","5"]).sum() if not df_at.empty else 0
        av_ant2=df_ant["humanConversationEvaluation"].isin(["1","2","3","4","5"]).sum() if not df_ant.empty else 0
        cs_at=df_at["humanConversationEvaluation"].isin(["4","5"]).sum()/max(av_at,1) if not df_at.empty else 0
        cs_ant=df_ant["humanConversationEvaluation"].isin(["4","5"]).sum()/max(av_ant2,1) if not df_ant.empty else 0
        tme_at=df_at["TME_segundos"].mean() if not df_at.empty else 0
        tme_ant=df_ant["TME_segundos"].mean() if not df_ant.empty else 0
        tma_at=df_at["TMA_segundos"].mean() if not df_at.empty else 0
        tma_ant=df_ant["TMA_segundos"].mean() if not df_ant.empty else 0

        st.markdown(f"""<div class="kr">
            {skpi2("Tickets",t_at2,t_ant,maior_melhor=True)}
            {skpi2("% CSAT",cs_at,cs_ant,maior_melhor=True)}
            {skpi2("TME",tme_at,tme_ant,maior_melhor=False,fmt_fn=fmt_time)}
            {skpi2("TMA",tma_at,tma_ant,maior_melhor=False,fmt_fn=fmt_time)}
        </div>""",unsafe_allow_html=True)
        st.caption(f"📅 Período atual: {data_inicio} → {data_fim} &nbsp;|&nbsp; Período anterior: {ini_ant} → {fim_ant}")

        st.markdown('<h3 style="color:#bfdbfe;font-size:1.1rem;margin-top:16px;margin-bottom:12px">🏆 Top 10 TAGs — Período Atual (com submotivos)</h3>',unsafe_allow_html=True)
        if not df_at.empty:
            top10=df_at.groupby("Depara_TAG1").size().reset_index(name="Qtd").sort_values("Qtd",ascending=False).head(10)
            for _,rt in top10.iterrows():
                pct_t=rt["Qtd"]/len(df_at)*100
                st.markdown(f'<div class="ac ac-blue"><b style="color:#ffffff">📌 {rt["Depara_TAG1"]}</b> &nbsp;·&nbsp; <span style="color:#bfdbfe">{int(rt["Qtd"])} tickets ({pct_t:.1f}%)</span></div>',unsafe_allow_html=True)
                subs=df_at[df_at["Depara_TAG1"]==rt["Depara_TAG1"]].groupby("Depara_SubTag").size().reset_index(name="n").sort_values("n",ascending=False).head(5)
                for _,rs in subs.iterrows():
                    st.markdown(f'<div style="padding:2px 0 2px 28px;color:#93c5fd;font-size:.82rem">↳ {rs["Depara_SubTag"]} — {int(rs["n"])} ({rs["n"]/rt["Qtd"]*100:.1f}%)</div>',unsafe_allow_html=True)

# ── ABA 10: REPORT VIP ──
with tabs[9]:
    st.markdown('<div class="ph"><span class="pt">📋 REPORT VIP DIÁRIO</span><span class="pl">W●INOVE</span></div>',unsafe_allow_html=True)
    data_rep=st.date_input("Data do report",value=date.today()-timedelta(days=1),key="dt_rep")
    df_vip=df_raw[df_raw["Depara_Fila"]=="VIP"].copy() if not df_raw.empty else pd.DataFrame()
    df_vd=df_vip[pd.to_datetime(df_vip["Depara_Data"])==pd.Timestamp(data_rep)] if not df_vip.empty else pd.DataFrame()

    if df_vd.empty: st.warning(f"Sem dados VIP para {data_rep}.")
    else:
        t_v=len(df_vd)
        av_v=df_vd["humanConversationEvaluation"].isin(["1","2","3","4","5"]).sum()
        cs_v=df_vd["humanConversationEvaluation"].isin(["4","5"]).sum()
        tme_v=df_vd["TME_segundos"].mean(); tma_v=df_vd["TMA_segundos"].mean()
        cs_pv=cs_v/av_v if av_v>0 else 0
        dr_vip=df_rec[(df_rec["Depara_Fila"]=="VIP")&(pd.to_datetime(df_rec["Depara_Data"])==pd.Timestamp(data_rep))] if not df_rec.empty else pd.DataFrame()
        fcr_v=dr_vip["Eh_FCR"].sum()/len(dr_vip) if len(dr_vip)>0 else 0
        top_m=df_vd.groupby("Depara_SubTag").size().reset_index(name="n")
        top_m["%"]=top_m["n"]/t_v*100
        top_m=top_m.sort_values("n",ascending=False).head(5)
        motivos="\n".join([f"{r['Depara_SubTag']} - {r['%']:.2f}% ({int(r['n'])})" for _,r in top_m.iterrows()])
        cs_ico="✅" if cs_pv>=META_CSAT else "🚨"
        tma_ico="✅" if tma_v<=META_TMA else "⚠️"
        fcr_ico="✅" if fcr_v>=0.70 else "⚠️"
        report=f"""📊 Report Diário VIP – Visão Geral | {data_rep.strftime('%d/%b')}

📋 Demanda {t_v}
{fcr_ico} FCR - {fcr_v:.0%}
{cs_ico} CSAT {cs_pv:.0%}
⏱️ TME {fmt_time(tme_v)}
{tma_ico} TMA {fmt_time(tma_v)}

📌 Principais Motivos
{motivos}"""

        st.markdown("#### Preview")
        st.markdown(f'<div class="rb">{report}</div>',unsafe_allow_html=True)
        st.text_area("📋 Copiar:",value=report,height=250,key="rep_txt")
        st.download_button("⬇️ Download .txt",report.encode(),f"report_vip_{data_rep}.txt",key="dl_rep")

        st.markdown("---")
        c1,c2,c3=st.columns(3)
        c1.metric("Tickets VIP",t_v); c2.metric("CSAT",f"{cs_pv:.1%}"); c3.metric("TMA",fmt_time(tma_v))
        st.markdown("#### Top Motivos detalhados (TAG → SubTag)")
        drill_tag_subtag(df_vd, key_prefix="rep_drill")


# ── ABA 11: DIÁRIO DE BORDO + IA ──
with tabs[10]:
    st.markdown('<div class="ph"><span class="pt">📓 DIÁRIO DE BORDO + IA</span><span class="pl">●INOVE</span></div>',unsafe_allow_html=True)

    # Carregar diário
    with st.spinner("Carregando diário de bordo..."):
        df_diario, err_diario = get_diario()

    if err_diario:
        st.error(f"Erro ao carregar diário: {err_diario}")
        st.info("Verifique se os secrets GOOGLE_CREDENTIALS e GOOGLE_SHEETS_ID estão configurados no Streamlit.")
    elif df_diario.empty:
        st.warning("Nenhum registro encontrado no diário de bordo.")
    else:
        # ── FILTROS ──
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            di_diario = st.date_input("De", value=data_inicio, key="di_diario")
        with fc2:
            df_diario_fim = st.date_input("Até", value=data_fim, key="df_diario")
        with fc3:
            lideres_diario = ["Todos"] + sorted(df_diario["lider"].dropna().unique().tolist())
            lider_diario = st.multiselect("Líder", lideres_diario, default=["Todos"], key="lider_diario")

        # Filtrar
        mask = (df_diario["data"] >= di_diario) & (df_diario["data"] <= df_diario_fim)
        df_d = df_diario[mask].copy()
        if "Todos" not in lider_diario and lider_diario:
            df_d = df_d[df_d["lider"].isin(lider_diario)]

        if df_d.empty:
            st.warning("Sem registros no período/filtro selecionado.")
        else:
            st.caption(f"📝 {len(df_d)} registros encontrados | {df_d['data'].nunique()} dias | {df_d['lider'].nunique()} líderes")

            # ── TABELA DE OCORRÊNCIAS ──
            with st.expander("📋 Ver todas as ocorrências do período", expanded=False):
                df_show = df_d[["data","dia_semana","lider","ocorrencia"]].rename(columns={
                    "data":"Data","dia_semana":"Dia","lider":"Líder","ocorrencia":"Ocorrência"
                })
                st.dataframe(df_show, use_container_width=True, hide_index=True, height=350)
                st.download_button("⬇️ Download Excel", to_xl(df_show), "diario.xlsx", key="dl_diario")

            # ── ANÁLISE COM IA ──
            st.markdown("---")
            st.markdown('<h3 style="color:#e0ecff;font-size:1.1rem;margin-bottom:12px">🤖 Análise com IA — Cruzamento Diário + Indicadores</h3>',unsafe_allow_html=True)

            # Indicadores do período para cruzar
            df_ind = aplica(df_raw.copy()) if not df_raw.empty else pd.DataFrame()
            if not df_ind.empty:
                mask_ind = (pd.to_datetime(df_ind["Depara_Data"]) >= pd.Timestamp(di_diario)) &                            (pd.to_datetime(df_ind["Depara_Data"]) <= pd.Timestamp(df_diario_fim))
                df_ind = df_ind[mask_ind]

            col_btn, col_info = st.columns([1, 3])
            with col_info:
                st.markdown(f'<div class="ac ac-blue">📊 A IA vai analisar <b>{len(df_d)}</b> ocorrências do diário + indicadores de <b>{len(df_ind)}</b> atendimentos do mesmo período</div>',unsafe_allow_html=True)

            with col_btn:
                gerar_ia = st.button("🤖 Gerar análise", type="primary", key="btn_ia_diario")

            if gerar_ia:
                if not df_d.empty:
                    with st.spinner("Analisando com IA... (pode levar ~15 segundos)"):
                        try:
                            import anthropic

                            # Preparar contexto do diário (máx 60 ocorrências)
                            ocorrencias_sample = df_d.head(60)
                            diario_txt = ""
                            for _, r in ocorrencias_sample.iterrows():
                                d=str(r["data"]); l=str(r["lider"]); o=str(r["ocorrencia"])[:300]
                                diario_txt += f"[{d} - {l}]: {o}\n\n"

                            # Preparar indicadores resumidos por dia
                            if not df_ind.empty:
                                ind_dia = df_ind.groupby("Depara_Data").agg(
                                    Tickets=("sequentialId","count"),
                                    CSAT=("humanConversationEvaluation", lambda x: x.isin(["4","5"]).sum()),
                                    Aval=("humanConversationEvaluation", lambda x: x.isin(["1","2","3","4","5"]).sum()),
                                    TME=("TME_segundos","mean"),
                                    TMA=("TMA_segundos","mean"),
                                ).reset_index()
                                ind_dia["pct_csat"] = ind_dia["CSAT"] / ind_dia["Aval"].replace(0, float("nan"))
                                ind_txt = ""
                                for _, r in ind_dia.iterrows():
                                    dd=str(r["Depara_Data"]); tk=int(r["Tickets"]); pc=r["pct_csat"]; tm=fmt_time(r["TME"]); ta=fmt_time(r["TMA"])
                                    ind_txt += f"[{dd}] Tickets: {tk} | CSAT: {pc:.1%} | TME: {tm} | TMA: {ta}\n"
                            else:
                                ind_txt = "Dados de indicadores não disponíveis para o período."

                            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_KEY",""))
                            msg = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=1500,
                                messages=[{
                                    "role": "user",
                                    "content": f"""Você é um analista especialista em operações de atendimento ao cliente.
Analise as ocorrências do diário de bordo dos líderes e os indicadores operacionais do mesmo período.

=== DIÁRIO DE BORDO (ocorrências registradas pelos líderes) ===
{diario_txt}

=== INDICADORES OPERACIONAIS POR DIA ===
{ind_txt}

Por favor, forneça uma análise executiva estruturada com:

1. **PRINCIPAIS TEMAS RECORRENTES** (máx 5): quais assuntos aparecem com mais frequência nas ocorrências dos líderes?

2. **CORRELAÇÕES IDENTIFICADAS**: existe relação entre o que os líderes reportaram e os indicadores? (ex: dias com ocorrências de "fraude" coincidem com queda de CSAT? Picos de fila aparecem em dias específicos?)

3. **PADRÕES HISTÓRICOS**: há recorrências em dias da semana, períodos do mês ou situações que se repetem?

4. **IMPACTOS NOS INDICADORES**: quais ocorrências tiveram maior impacto visível nos números?

5. **RECOMENDAÇÕES** (máx 3 ações prioritárias): baseado nos padrões identificados, o que deveria ser monitorado ou ajustado?

Seja objetivo e direto. Use dados específicos quando possível."""
                                }]
                            )

                            resultado = msg.content[0].text

                            st.markdown('<div style="background:#0a1628;border:1px solid #1e3a70;border-radius:12px;padding:24px;margin-top:12px">', unsafe_allow_html=True)
                            st.markdown(resultado)
                            st.markdown('</div>', unsafe_allow_html=True)

                            # Download do relatório
                            st.download_button(
                                "⬇️ Download análise (.txt)",
                                resultado.encode(),
                                f"analise_diario_{di_diario}_{df_diario_fim}.txt",
                                key="dl_ia_diario"
                            )

                        except Exception as e:
                            st.error(f"Erro na análise IA: {str(e)}")
                else:
                    st.warning("Sem ocorrências para analisar no período selecionado.")

            # ── LINHA DO TEMPO DAS OCORRÊNCIAS ──
            st.markdown("---")
            st.markdown('<h3 style="color:#e0ecff;font-size:1.1rem;margin-bottom:12px">📅 Linha do Tempo das Ocorrências</h3>',unsafe_allow_html=True)

            # Cruzar com indicadores por dia
            if not df_ind.empty and not df_d.empty:
                dias_unicos = sorted(df_d["data"].unique(), reverse=True)
                for dia in dias_unicos[:14]:  # últimos 14 dias com registro
                    ocorr_dia = df_d[df_d["data"] == dia]
                    ind_dia2 = df_ind[pd.to_datetime(df_ind["Depara_Data"]) == pd.Timestamp(dia)]

                    # Indicadores do dia
                    if not ind_dia2.empty:
                        t = len(ind_dia2)
                        av = ind_dia2["humanConversationEvaluation"].isin(["1","2","3","4","5"]).sum()
                        cs = ind_dia2["humanConversationEvaluation"].isin(["4","5"]).sum()
                        cs_p = cs/av if av > 0 else 0
                        tme_d = ind_dia2["TME_segundos"].mean()
                        tma_d = ind_dia2["TMA_segundos"].mean()
                        ind_badge = f'<span style="color:#4fc3f7">📊 {t} tickets | CSAT: {cs_p:.1%} | TME: {fmt_time(tme_d)} | TMA: {fmt_time(tma_d)}</span>'
                        # Alertas automáticos
                        alertas = []
                        if cs_p < 0.80 and av >= 5: alertas.append("⚠️ CSAT baixo")
                        if pd.notna(tma_d) and tma_d > 20*60: alertas.append("⚠️ TMA alto")
                        alerta_str = " ".join(alertas)
                    else:
                        ind_badge = '<span style="color:#7fa8d4">📊 Sem dados de indicadores</span>'
                        alerta_str = ""

                    dia_fmt = dia.strftime("%d/%m/%Y (%a)")
                    st.markdown(f'<div style="background:#0d1b3e;border:1px solid #1e3a70;border-radius:8px;padding:12px;margin-bottom:8px">' +
                        f'<div style="color:#a8c4e8;font-size:.78rem;font-weight:600">{dia_fmt} {alerta_str}</div>' +
                        f'<div style="margin:4px 0 8px 0">{ind_badge}</div>',
                        unsafe_allow_html=True)

                    for _, oc in ocorr_dia.iterrows():
                        st.markdown(
                            f'<div style="border-left:3px solid #1e3a70;padding:4px 0 4px 12px;margin-bottom:4px">' +
                            f'<span style="color:#7fa8d4;font-size:.73rem">{oc["lider"]}</span><br>' +
                            f'<span style="color:#c8d8f0;font-size:.82rem">{oc["ocorrencia"][:400]}</span>' +
                            '</div>',
                            unsafe_allow_html=True)

                    st.markdown('</div>', unsafe_allow_html=True)
