# ============================================================
# SmartLog Blockchain — Simulador de Consenso (PoA)
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import json
import uuid
import requests

# ------------------------------------------------------------
# Importações internas com fallback
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
except Exception as e:
    st.error(f"Erro ao importar módulos internos: {e}")

    # Fallback simples
    def registrar_auditoria(*args): pass
    def mostrar_demo_web3(*args): pass
    def salvar_blockchain_firestore(*args): pass
    def carregar_blockchain_firestore(*args): return None
    def limpar_blockchain_firestore(*args): pass

# ============================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain", layout="wide")
st.title("SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("Simulador didático de consenso Proof-of-Authority (PoA) para redes logísticas e privadas.")

# ============================================================
# MODO DE OPERAÇÃO
# ============================================================
st.sidebar.header("Configurações da Simulação")

modo_operacao = st.sidebar.radio(
    "Modo de operação:",
    ["Simulado (local)", "Distribuído (rede)"],
    index=0
)

st.markdown(f"### Modo atual: **{modo_operacao}**")

if modo_operacao == "Simulado (local)":
    st.caption("Rodando localmente — ideal para demonstração didática.")
else:
    st.caption("Modo distribuído — nós conectados via rede real.")

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
    df_eventos = pd.DataFrame(dados)

    blockchain_df = sb.criar_blockchain_inicial(df_eventos)
    nos = sb.criar_nos(blockchain_df)
    chaves = sb.simular_chaves_privadas(nos)

    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state.consenso_sucesso = False
    st.session_state.ultimo_lote = None
    st.session_state.ultimo_hash = None
    st.session_state.mostrar_web3 = False

nos = st.session_state.nos
chaves = st.session_state.chaves

# ============================================================
# Função para nós remotos
# ============================================================
def propor_bloco_remoto(evento_texto, hash_anterior):
    votos = {}
    for nome, url in NOS_REMOTOS.items():
        try:
            r = requests.post(
                f"{url}/proposta",
                json={"evento": evento_texto, "hash_anterior": hash_anterior},
                timeout=5
            )
            votos[nome] = r.json() if r.status_code == 200 else {"erro": "Falha"}
        except:
            votos[nome] = {"erro": "Nó offline"}
    return votos

# ============================================================
# Layout principal com abas
# ============================================================
tab_main, tab_fraude = st.tabs(["Consenso Principal", "Simulador de Fraude"])

# ============================================================
# ABA PRINCIPAL — CONSENSO
# ============================================================
with tab_main:

    st.header("Fluxo de Consenso Proof-of-Authority (PoA)")

    consenso_ok = sb.validar_consenso(nos)
    st.success("Sistema sincronizado.") if consenso_ok else st.warning("Divergência encontrada!")

    # --------------------------------------------------------
    # Status da Rede
    # --------------------------------------------------------
    with st.expander("Status da Rede e Últimos Hashes"):
        cols = st.columns(len(nos))
        for i, (nome, df) in enumerate(nos.items()):
            if len(df) == 0:
                val = "VAZIO"
            else:
                val = df.iloc[-1]["hash_atual"]

            cols[i].metric(f"Nó {nome}", val[:10] + "..." if val != "VAZIO" else "VAZIO", f"{len(df)} blocos")

    st.divider()

    # --------------------------------------------------------
    # Formulário de Proposta
    # --------------------------------------------------------
    st.subheader("1. Proposta de Novo Bloco")

    propositor = st.selectbox("Nó propositor:", list(nos.keys()))
    quorum = st.slider("Quorum mínimo:", 1, len(nos), 2)

    st.subheader("Cadastro de Lote de Eventos")
    qtd = st.number_input("Quantidade de eventos:", 1, 10, 3)

    lote = []
    for i in range(qtd):
        with st.expander(f"Evento {i+1}"):
            lote.append({
                "id_entrega": st.text_input(f"ID {i+1}", f"{100+i}"),
                "origem": st.text_input(f"Origem {i+1}", "Depósito_SP"),
                "destino": st.text_input(f"Destino {i+1}", "Centro_MG"),
                "etapa": st.selectbox(f"Etapa {i+1}", ["Saiu", "Em rota", "Chegou"], key=f"etp{i}"),
                "risco": st.selectbox(f"Risco {i+1}", ["Baixo", "Médio", "Alto"], key=f"rsk{i}"),
                "timestamp": datetime.now().isoformat()
            })

    # --------------------------------------------------------
    # INICIAR CONSENSO
    # --------------------------------------------------------
    if st.button("🚀 Iniciar Consenso"):

        try:
            hash_ant = nos[propositor].iloc[-1]["hash_atual"]

            proposta = sb.propor_bloco(propositor, lote, hash_ant)
            proposta = sb.votar_proposta(proposta, nos, chaves)

            sucesso, tx_id = sb.aplicar_consenso(proposta, nos, quorum)

            if sucesso:
                st.success("✅ Consenso alcançado! Bloco adicionado.")
                st.session_state.consenso_sucesso = True
                st.session_state.ultimo_lote = lote
                st.session_state.ultimo_hash = proposta["hash_bloco"]

            else:
                st.session_state.consenso_sucesso = False
                st.warning("❌ Quorum insuficiente. Bloco rejeitado.")

        except Exception as e:
            st.error(f"Erro no consenso: {e}")

    # --------------------------------------------------------
    # Auditoria após consenso
    # --------------------------------------------------------
    if st.session_state.consenso_sucesso:

        st.divider()
        st.subheader("Auditoria de Hashes — Antes ➜ Depois")

        linhas = []
        for nome, df in nos.items():
            if len(df) > 1:
                h_ant = df.iloc[-2]["hash_atual"]
                h_at = df.iloc[-1]["hash_atual"]
                linhas.append({
                    "Nó": nome,
                    "Anterior": h_ant[:10],
                    "Atual": h_at[:10],
                    "Mudou?": "Sim" if h_ant != h_at else "Não"
                })
        st.dataframe(pd.DataFrame(linhas), use_container_width=True)

        # ----------------------------------------------------
        # Integração Web3
        # ----------------------------------------------------
        if st.button("🌐 Mostrar Integração Web3"):
            st.session_state.mostrar_web3 = not st.session_state.mostrar_web3

        if st.session_state.mostrar_web3:
            mostrar_demo_web3(st.session_state.ultimo_lote, st.session_state.ultimo_hash)

# ============================================================
# ABA FRAUDE — ATAQUE E RECUPERAÇÃO
# ============================================================
with tab_fraude:

    st.header("Simulação de Ataque e Recuperação")
    st.divider()

    node = st.selectbox("Nó alvo:", list(nos.keys()))
    tipo = st.radio("Tipo de ataque:", ["Alterar dados", "Alterar hash"], horizontal=True)

    if st.button("💣 Corromper nó"):

        df = nos[node].copy()
        if len(df) == 0:
            st.warning("Nó vazio.")
        else:
            idx = len(df) - 1
            original = df.iloc[idx].to_dict()

            eventos = df.at[idx, "eventos"]

            if tipo == "Alterar dados":
                novo = str(eventos) + " 🚨"
                df.at[idx, "eventos"] = novo
                df.at[idx, "hash_atual"] = sb.gerar_hash(novo, df.at[idx, "hash_anterior"])
            else:
                df.at[idx, "hash_atual"] = sb.gerar_hash("ATAQUE", df.at[idx, "hash_anterior"])

            nos[node] = df
            mod = df.iloc[idx].to_dict()

            st.error(f"Nó {node} corrompido!")

            # Comparação
            try:
                ev_ant = json.dumps(original["eventos"], ensure_ascii=False, indent=2)
            except:
                ev_ant = str(original["eventos"])

            try:
                ev_dep = json.dumps(mod["eventos"], ensure_ascii=False, indent=2)
            except:
                ev_dep = str(mod["eventos"])

            comp = pd.DataFrame([
                {"Campo": "Eventos", "Antes": ev_ant, "Depois": ev_dep},
                {"Campo": "Hash Atual", "Antes": original["hash_atual"][:12], "Depois": mod["hash_atual"][:12]},
                {"Campo": "Hash Anterior", "Antes": original["hash_anterior"][:12], "Depois": mod["hash_anterior"][:12]}
            ])
            st.dataframe(comp, use_container_width=True)

    st.divider()

    if st.button("🔍 Detectar divergências"):
        if sb.validar_consenso(nos):
            st.success("Tudo íntegro.")
        else:
            st.warning("Divergência detectada.")
            corrompidos = sb.detectar_no_corrompido(nos)
            st.write("Nós corrompidos:", corrompidos)

    st.divider()

    if st.button("🧹 Recuperar nós corrompidos"):
        ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
        freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
        hash_ok = max(freq, key=freq.get)

        st.session_state.nos = sb.recuperar_no(nos, hash_ok)
        nos = st.session_state.nos

        st.success("Nós recuperados da maioria!")

    st.divider()

    if st.button("📊 Exibir resumo dos nós"):
        for nome, df in nos.items():
            st.markdown(f"### Nó {nome} — {len(df)} blocos")
            st.dataframe(df.tail(3), use_container_width=True)

