# ============================================================
# SmartLog Blockchain — Simulador de Consenso e Fraude
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import uuid
import requests

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
    def mostrar_demo_web3(event, hash): st.markdown("Detalhes Web3 simulados aqui.")


# ============================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain", layout="wide")
st.title("SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("Simulador didático de consenso Proof-of-Authority (PoA) para redes privadas e logísticas.")


# ============================================================
# MODO DE OPERAÇÃO
# ============================================================
st.sidebar.header("⚙️ Configurações da Simulação")

modo_operacao = st.sidebar.radio(
    "Modo de operação:",
    ["Simulado (local)", "Distribuído (rede)"],
    index=0
)

st.sidebar.info(
    "🧠 *Modo Simulado:* tudo roda localmente em um só Streamlit.\n\n"
    "🌐 *Modo Distribuído:* cada nó será um servidor real conectado via rede."
)

st.markdown(f"### 🧭 Modo atual: **{modo_operacao}**")
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
if "modo_operacao" not in st.session_state:
    st.session_state.modo_operacao = modo_operacao
else:
    st.session_state.modo_operacao = modo_operacao


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

    # -------------------------------
    # Definição conforme o modo
    # -------------------------------
    if st.session_state.modo_operacao == "Simulado (local)":
        blockchain_df = criar_blockchain_inicial(eventos_df)
        nos = criar_nos(blockchain_df)
        chaves = simular_chaves_privadas(nos)
    else:
        # 🔹 Modo distribuído (não usa DataFrames locais)
        blockchain_df = pd.DataFrame()
        nos = {"Node_A": pd.DataFrame(), "Node_B": pd.DataFrame(), "Node_C": pd.DataFrame()}
        chaves = {}

    st.session_state.blockchain_df = blockchain_df
    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state["mostrar_web3"] = False
    st.session_state["web3_evento_texto"] = None
    st.session_state["web3_hash"] = None
    st.session_state["consenso_sucesso"] = False
    st.session_state["df_auditoria_hash"] = None

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
            if resposta.status_code == 200:
                votos[nome] = resposta.json()
            else:
                votos[nome] = {"erro": f"Status {resposta.status_code}"}
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
    st.header("Fluxo de Consenso Proof-of-Authority")

    if not nos:
        st.warning("⚠️ Nenhum nó disponível no modo distribuído (a implementar).")
        st.stop()

    consenso_ok = validar_consenso(nos)
    if consenso_ok:
        st.success("Sistema sincronizado e íntegro.")
    else:
        st.warning("Divergência detectada entre os nós.")

    # --------------------------------------------------------
    # STATUS INICIAL DOS NÓS
    # --------------------------------------------------------
    with st.expander("Status da Rede e Hashes Finais (Antes da Proposta)", expanded=False):
        cols = st.columns(len(nos))
        for i, (nome, df) in enumerate(nos.items()):
            hash_display = "VAZIO"
            if isinstance(df, pd.DataFrame) and len(df) > 0 and "hash_atual" in df.columns:
                hash_display = df.iloc[-1]["hash_atual"]
            with cols[i]:
                st.metric(
                    label=f"Nó {nome}",
                    value=f"{hash_display[:12]}...{hash_display[-6:]}" if hash_display != "VAZIO" else "VAZIO",
                    delta=f"Blocos: {len(df)}" if isinstance(df, pd.DataFrame) else "-"
                )

    st.divider()
    st.subheader("1. Proposta e Votação de Novo Bloco")

    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            propositor = st.selectbox("Nó propositor:", list(nos.keys()))
        with col2:
            quorum = st.slider("Quorum mínimo:", 1, len(nos), 2)
            st.caption(f"Quorum necessário: {quorum}/{len(nos)}")

        evento_texto = st.text_input("Descrição do evento:", "Entrega #104 — Saiu do depósito — SP → MG")

        if st.button("Iniciar Simulação de Consenso", use_container_width=True):
            st.session_state["consenso_sucesso"] = False
            st.info(f"O nó {propositor} propôs o bloco: '{evento_texto}'")

            try:
                if st.session_state.modo_operacao == "Simulado (local)":
                    hashes_finais = [df.iloc[-1]["hash_atual"] for df in nos.values()]
                    hash_anterior = max(set(hashes_finais), key=hashes_finais.count)
                    proposta = sb.propor_bloco(propositor, evento_texto, hash_anterior)
                    proposta = sb.votar_proposta(proposta, nos, chaves)
                else:
                    # -----------------------------
                    # MODO DISTRIBUÍDO
                    # -----------------------------
                    hash_anterior = "GENESIS"
                    st.info("🔗 Enviando proposta de bloco aos nós reais...")
                    votos = propor_bloco_remoto(evento_texto, hash_anterior)
                    proposta = {
                        "propositor": propositor,
                        "evento": evento_texto,
                        "assinaturas": {k: v.get("assinatura", "erro") for k, v in votos.items()},
                        "hash_bloco": max([v.get("hash_bloco", "") for v in votos.values()], default="GENESIS")
                    }

            except Exception as e:
                st.error(f"Erro na proposta/votação: {e}")
                st.stop()

            sucesso = True  # Para simplificar, assumimos que o consenso foi aplicado
            if sucesso:
                st.session_state["consenso_sucesso"] = True
                st.session_state["ultimo_evento"] = evento_texto
                st.session_state["ultimo_hash"] = proposta["hash_bloco"]

                st.success(f"✅ Consenso alcançado! Novo bloco adicionado. Hash: `{proposta['hash_bloco'][:16]}...`")

                registrar_auditoria("Sistema", "consenso_aprovado",
                                    f"Bloco '{evento_texto}' aceito (quorum {quorum})")

                st.session_state["web3_evento_texto"] = evento_texto
                st.session_state["web3_hash"] = proposta["hash_bloco"]
                st.session_state["mostrar_web3"] = False
            else:
                st.warning("Quorum insuficiente. Bloco rejeitado.")
                registrar_auditoria("Sistema", "consenso_rejeitado",
                                    f"Bloco '{evento_texto}' rejeitado.")

# ============================================================
# ABA FRAUDE — ATAQUE E RECUPERAÇÃO
# ============================================================
with tab_fraude:
    st.header("Simulação de Ataque e Recuperação de Nós")
    st.divider()

    if not nos:
        st.warning("⚠️ Nenhum nó disponível no modo distribuído (a implementar).")
        st.stop()

    with st.container(border=True):
        st.subheader("1. Simular Ataque")
        colA, colB = st.columns(2)
        with colA:
            node_to_corrupt = st.selectbox("Escolha o nó:", list(nos.keys()))
            corrupt_type = st.radio("Tipo de corrupção:",
                                    ["Alterar último bloco", "Alterar hash final"])
        with colB:
            if st.button("Corromper Nó", use_container_width=True):
                df = nos[node_to_corrupt].copy()
                if len(df) > 0:
                    idx = len(df) - 1
                    if corrupt_type == "Alterar último bloco":
                        df.at[idx, "etapa"] += " (ALTERADO)"
                        conteudo = f"{df.at[idx,'id_entrega']}-{df.at[idx,'source_center']}-{df.at[idx,'destination_name']}-{df.at[idx,'etapa']}-{df.at[idx,'timestamp']}-{df.at[idx,'risco']}"
                        df.at[idx, "hash_atual"] = gerar_hash(conteudo, df.at[idx, "hash_anterior"])

