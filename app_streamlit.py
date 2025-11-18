# ============================================================
# SmartLog Blockchain — Simulador de Consenso e Fraude (PoA)
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import uuid
import requests
import json

# ------------------------------------------------------------
# Importações internas (com fallback)
# ------------------------------------------------------------
try:
    import smartlog_blockchain as sb
    from audit_logger import registrar_auditoria
    from web3_demo_simulado import mostrar_demo_web3
    from firebase_utils import (
        salvar_blockchain_firestore,
        carregar_blockchain_firestore,
        limpar_blockchain_firestore
    )
    from smartlog_blockchain import (
        criar_blockchain_inicial,
        criar_nos,
        validar_consenso,
        simular_chaves_privadas,
        propor_bloco,
        votar_proposta,
        aplicar_consenso,
        detectar_no_corrompido,
        recuperar_no,
        gerar_hash
    )
except ImportError as e:
    st.error(f"Erro de importação: {e}")
    def gerar_hash(content, prev_hash): return hashlib.sha256((content + prev_hash).encode()).hexdigest()
    def criar_blockchain_inicial(df): return pd.DataFrame()
    def criar_nos(df): return {"Node_A": df}
    def simular_chaves_privadas(nos): return {}
    def validar_consenso(nos): return True
    def detectar_no_corrompido(nos): return []
    def recuperar_no(nos, hash_ok): return nos
    def registrar_auditoria(*args): pass
    def salvar_blockchain_firestore(*args): pass
    def carregar_blockchain_firestore(): return None
    def limpar_blockchain_firestore(): pass
    def mostrar_demo_web3(event, hash): st.markdown("Módulo Web3 Simulado — detalhes aqui.")


# ============================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain", layout="wide")
st.title("SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("Simulador didático de consenso Proof-of-Authority (PoA) para redes privadas e logísticas.")


# ============================================================
# MODO DE OPERAÇÃO
# ============================================================
st.sidebar.header("Configurações da Simulação")

modo_operacao = st.sidebar.radio(
    "Modo de operação:",
    ["Simulado (local)", "Distribuído (rede)"],
    index=0
)

st.sidebar.info(
    "*Modo Simulado:* tudo roda localmente em um só Streamlit.\n\n"
    "*Modo Distribuído:* cada nó será um servidor real conectado via rede."
)

st.markdown(f"### Modo atual: **{modo_operacao}**")
if modo_operacao == "Simulado (local)":
    st.caption("Rodando localmente — ideal para demonstração didática.")
else:
    st.caption("Rodando em modo distribuído — conexão entre nós via rede.")


# ------------------------------------------------------------
# Configuração dos nós remotos (modo distribuído)
# ------------------------------------------------------------
NOS_REMOTOS = {
    "Node_A": "http://127.0.0.1:5000",
    "Node_B": "http://127.0.0.1:5001",
    "Node_C": "http://127.0.0.1:5002"
}


# ============================================================
# ESTADO INICIAL
# ============================================================
if "nos" not in st.session_state:
    dados = {
        "id_entrega": [1, 2, 3],
        "source_center": ["Depósito_SP", "Depósito_SP", "Depósito_RJ"],
        "destination_name": ["Centro_MG", "Centro_PR", "Centro_BA"],
        "etapa": ["Saiu do depósito", "Em rota", "Chegou ao destino"],
        "timestamp": [datetime.now()] * 3,
        "risco": ["Baixo", "Médio", "Baixo"]
    }
    eventos_df = pd.DataFrame(dados)

    if modo_operacao == "Simulado (local)":
        blockchain_df = criar_blockchain_inicial(eventos_df)
        nos = criar_nos(blockchain_df)
        chaves = simular_chaves_privadas(nos)
    else:
        blockchain_df = pd.DataFrame()
        nos = {"Node_A": pd.DataFrame(), "Node_B": pd.DataFrame(), "Node_C": pd.DataFrame()}
        chaves = {}

    st.session_state.blockchain_df = blockchain_df
    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state["consenso_sucesso"] = False
    st.session_state["mostrar_web3"] = False
    st.session_state["ultimo_lote"] = None
    st.session_state["ultimo_hash"] = None


nos = st.session_state.nos
chaves = st.session_state.chaves


# ============================================================
# FUNÇÃO PARA COMUNICAR COM NÓS REAIS
# ============================================================
def propor_bloco_remoto(evento_texto, hash_anterior):
    votos = {}
    for nome, url in NOS_REMOTOS.items():
        try:
            resposta = requests.post(
                f"{url}/proposta",
                json={"evento": evento_texto, "hash_anterior": hash_anterior},
                timeout=5
            )
            votos[nome] = resposta.json() if resposta.status_code == 200 else {"erro": f"HTTP {resposta.status_code}"}
        except Exception as e:
            votos[nome] = {"erro": str(e)}
    return votos


# ============================================================
# INTERFACE EM ABAS
# ============================================================
tab_main, tab_fraude = st.tabs(["Consenso Principal", "Simulador de Fraude"])


# ============================================================
# ABA PRINCIPAL — CONSENSO
# ============================================================
with tab_main:
    st.header("Fluxo de Consenso Proof-of-Authority (PoA)")

    consenso_ok = validar_consenso(nos)
    if consenso_ok:
        st.success("Sistema sincronizado e íntegro.")
    else:
        st.warning("❗ Divergência detectada entre os nós.")

    with st.expander("Status da Rede e Hashes Finais (Antes da Proposta)", expanded=False):
        cols = st.columns(len(nos))
        for i, (nome, df) in enumerate(nos.items()):
            if len(df) > 0:
                hash_display = df.iloc[-1]["hash_atual"]
                hash_fmt = f"{hash_display[:12]}...{hash_display[-6:]}"
            else:
                hash_fmt = "VAZIO"
            with cols[i]:
                st.metric(f"Nó {nome}", hash_fmt, f"Blocos: {len(df)}")

    st.divider()
    st.subheader("1. Proposta e Votação de Novo Bloco")

    col1, col2 = st.columns([2, 1])
    propositor = col1.selectbox("Nó propositor:", list(nos.keys()))
    quorum = col2.slider("Quorum mínimo:", 1, len(nos), 2)

    # ============================
    # FORMULÁRIO DE EVENTOS
    # ============================
    st.subheader("Cadastro de Lote de Entregas")
    num_eventos = st.number_input("Número de eventos:", 1, 10, 3)

    lote_eventos = []
    for i in range(num_eventos):
        with st.expander(f"Evento {i+1}"):
            lote_eventos.append({
                "id_entrega": st.text_input(f"ID {i+1}", f"{100+i}"),
                "origem": st.text_input(f"Origem {i+1}", "Depósito_SP"),
                "destino": st.text_input(f"Destino {i+1}", "Centro_MG"),
                "etapa": st.selectbox(f"Etapa {i+1}", ["Saiu do depósito", "Em rota", "Chegou ao destino"]),
                "risco": st.selectbox(f"Risco {i+1}", ["Baixo", "Médio", "Alto"]),
                "timestamp": datetime.now().isoformat()
            })

    # ============================
    # CONSENSO
    # ============================

    if st.button("🚀 Iniciar Simulação de Consenso", use_container_width=True):
        try:
            hash_anterior = nos[propositor].iloc[-1]["hash_atual"]
            proposta = sb.propor_bloco(propositor, lote_eventos, hash_anterior)
            proposta = sb.votar_proposta(proposta, nos, chaves)
            sucesso, tx_id = sb.aplicar_consenso(proposta, nos, quorum)

            if sucesso:
                st.success("✔️ Consenso alcançado!")
                st.session_state["consenso_sucesso"] = True
                st.session_state["ultimo_lote"] = lote_eventos
                st.session_state["ultimo_hash"] = proposta["hash_bloco"]
            else:
                st.warning("⚠️ Quorum insuficiente.")

        except Exception as e:
            st.error(f"Erro no consenso: {e}")
            st.stop()


    # ============================================================
    # AUDITORIA DE HASHES DEPOIS DO CONSENSO
    # ============================================================
    if st.session_state["consenso_sucesso"]:
        st.divider()
        st.subheader("Auditoria de Hashes — Antes x Depois")
        comp = []

        for nome, df in nos.items():
            if len(df) < 2:
                comp.append({
                    "Nó": nome,
                    "Hash Anterior": "-",
                    "Hash Atual": df.iloc[-1]["hash_atual"][:16],
                    "Mudou?": "Novo bloco"
                })
                continue

            h1 = df.iloc[-2]["hash_atual"]
            h2 = df.iloc[-1]["hash_atual"]
            comp.append({
                "Nó": nome,
                "Hash Anterior": h1[:12],
                "Hash Atual": h2[:12],
                "Mudou?": "Sim" if h1 != h2 else "Não"
            })

        st.dataframe(pd.DataFrame(comp))

    

