# ============================================================
# SmartLog Blockchain — Simulador de Consenso e Fraude (FINAL)
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

    from audit_logger import registrar_auditoria
    from web3_demo_simulado import mostrar_demo_web3

    from firebase_utils import (
        salvar_blockchain_firestore,
        carregar_blockchain_firestore,
        limpar_blockchain_firestore
    )

except Exception as e:
    st.error(f"Erro ao carregar módulos internos: {e}")

    # fallbacks mínimos
    def gerar_hash(c, p): return hashlib.sha256((c + p).encode()).hexdigest()
    def criar_blockchain_inicial(df=None): return pd.DataFrame()
    def criar_nos(df): return {"Node_A": df}
    def validar_consenso(nos): return True
    def votar_proposta(p, nos, chaves): return p
    def aplicar_consenso(p, n, q): return True, "X"
    def simular_chaves_privadas(n): return {k: "key" for k in n}
    def detectar_no_corrompido(n): return []
    def recuperar_no(n, h): return n
    def registrar_auditoria(*args): pass
    def mostrar_demo_web3(*args): pass
    def salvar_blockchain_firestore(*args): pass
    def carregar_blockchain_firestore(): return None
    def limpar_blockchain_firestore(): pass


# ============================================================
# CONFIGURAÇÕES DA PÁGINA
# ============================================================

st.set_page_config(page_title="SmartLog Blockchain", layout="wide")
st.title("SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("Simulador didático de consenso Proof-of-Authority (PoA) para redes privadas e logística.")


# ============================================================
# SIDEBAR — MODO DE OPERAÇÃO
# ============================================================

st.sidebar.header("Configurações da Simulação")

modo_operacao = st.sidebar.radio(
    "Modo de operação:",
    ["Simulado (local)", "Distribuído (rede)"],
    index=0
)

st.sidebar.info(
    "*Modo Simulado:* tudo roda localmente em um só Streamlit.\n\n"
    "*Modo Distribuído:* cada nó será um servidor real conectado via HTTP."
)


# ============================================================
# CONFIG REMOTOS (Modo distribuído)
# ============================================================

NOS_REMOTOS = {
    "Node_A": "http://127.0.0.1:5000",
    "Node_B": "http://127.0.0.1:5001",
    "Node_C": "http://127.0.0.1:5002"
}


# ============================================================
# ESTADO INICIAL — CARREGAR BLOCKCHAIN & NÓS
# ============================================================

if "nos" not in st.session_state:

    # cria dados iniciais simulados
    dados = {
        "id_entrega": [1, 2, 3],
        "source_center": ["Depósito_SP"] * 3,
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
        nos = {n: pd.DataFrame() for n in NOS_REMOTOS}
        chaves = {}

    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state.consenso_sucesso = False
    st.session_state.ultimo_lote = None
    st.session_state.ultimo_hash = None


nos = st.session_state.nos
chaves = st.session_state.chaves


# ============================================================
# FUNÇÃO DE PROPOSTA REMOTA
# ============================================================

def propor_bloco_remoto(eventos, hash_anterior):
    votos = {}
    for nome, url in NOS_REMOTOS.items():
        try:
            resp = requests.post(
                url + "/proposta",
                json={"evento": eventos, "hash_anterior": hash_anterior},
                timeout=5
            )
            votos[nome] = resp.json() if resp.status_code == 200 else {"erro": f"status {resp.status_code}"}
        except Exception as e:
            votos[nome] = {"erro": str(e)}
    return votos


# ============================================================
# INTERFACE EM ABAS
# ============================================================

tab_main, tab_fraude = st.tabs(["Consenso Principal", "Simulador de Fraude"])


# ============================================================
# ABA PRINCIPAL
# ============================================================

with tab_main:
    st.header("Fluxo de Consenso Proof-of-Authority (PoA)")

    consenso_ok = validar_consenso(nos)

    if consenso_ok:
        st.success("Sistema sincronizado.")
    else:
        st.warning("Divergência detectada!")

    # STATUS DA REDE -----------------------------------------
    with st.expander("Status da Rede e Hashes Finais", expanded=False):

        col_status = st.columns(len(nos))

        for i, (nome, df) in enumerate(nos.items()):
            if len(df) == 0 or "hash_atual" not in df.columns:
                h = "VAZIO"
            else:
                h = df.iloc[-1]["hash_atual"]

            col_status[i].metric(
                label=f"Nó {nome}",
                value=h[:12] + "..." if h != "VAZIO" else "VAZIO",
                delta=f"Blocos: {len(df)}"
            )

    st.divider()

    # FORM PROPOSIÇÃO ----------------------------------------

    st.subheader("1) Proposta e Votação de Novo Bloco")

    col_pp1, col_pp2 = st.columns([2, 1])

    with col_pp1:
        propositor = st.selectbox("Nó propositor:", list(nos.keys()))
    with col_pp2:
        quorum = st.slider("Quorum mínimo:", 1, len(nos), 2)

    st.subheader("Cadastro do Lote de Eventos")

    num_events = st.number_input("Número de eventos:", 1, 10, 3)

    lote = []
    for i in range(int(num_events)):
        with st.expander(f"Evento {i+1}"):
            lote.append({
                "id_entrega": st.text_input(f"ID entrega {i+1}", f"{100+i}"),
                "origem": st.text_input(f"Origem {i+1}", "Depósito_SP"),
                "destino": st.text_input(f"Destino {i+1}", "Centro_MG"),
                "etapa": st.selectbox(f"Etapa {i+1}", ["Saiu do depósito", "Em rota", "Chegou ao destino"]),
                "risco": st.selectbox(f"Risco {i+1}", ["Baixo", "Médio", "Alto"]),
                "timestamp": datetime.now().isoformat()
            })

    if st.button("🚀 Iniciar Consenso", use_container_width=True):

        st.session_state.consenso_sucesso = False

        try:

            if modo_operacao == "Simulado (local)":

                hash_anterior = nos[propositor].iloc[-1]["hash_atual"]

                proposta = propor_bloco(propositor, lote, hash_anterior)
                proposta = votar_proposta(proposta, nos, chaves)
                sucesso, tx_id = aplicar_consenso(proposta, nos, quorum)

            else:
                hash_anterior = "GENESIS"
                votos = propor_bloco_remoto(lote, hash_anterior)

                proposta = {
                    "propositor": propositor,
                    "eventos": lote,
                    "assinaturas": {k: v.get("assinatura", "?") for k, v in votos.items()},
                    "hash_bloco": max([v.get("hash_bloco", "") for v in votos.values()])
                }
                sucesso = True

            if sucesso:
                st.success("Novo bloco adicionado via consenso!")
                st.session_state.consenso_sucesso = True
                st.session_state.ultimo_lote = lote
                st.session_state.ultimo_hash = proposta["hash_bloco"]

                st.text_input("Hash confirmado:", proposta["hash_bloco"])
                st.json(lote)

                registrar_auditoria("Sistema", "consenso_aprovado", f"Bloco com {len(lote)} eventos")

            else:
                st.error("❌ Quorum insuficiente. Bloco rejeitado.")
                st.session_state.consenso_sucesso = False

        except Exception as e:
            st.error(f"Erro durante consenso: {e}")

    # --------------------------------------------------------
    # AUDITORIA DE HASHES
    # --------------------------------------------------------

    if st.session_state.consenso_sucesso:

        st.divider()
        st.subheader("Auditoria de Hashes (Antes ➜ Depois)")

        tabela = []

        for nome, df in nos.items():

            if len(df) >= 2:
                h_ant = df.iloc[-2]["hash_atual"]
                h_atu = df.iloc[-1]["hash_atual"]
                tabela.append({
                    "Nó": nome,
                    "Anterior": h_ant[:12] + "...",
                    "Atual": h_atu[:12] + "...",
                    "Mudou?": "Sim" if h_ant != h_atu else "Não"
                })
            else:
                h = df.iloc[-1]["hash_atual"]
                tabela.append({
                    "Nó": nome,
                    "Anterior": "-",
                    "Atual": h[:12] + "...",
                    "Mudou?": "Novo"
                })

        st.dataframe(pd.DataFrame(tabela))

        # ----------------------------------------------------
        # INTEGRAÇÃO WEB3 SIMULADA
        # ----------------------------------------------------

        st.divider()
        st.subheader("Integração Web3 (Simulada)")

        if st.button("🌐 Exibir / Ocultar Web3"):
            st.session_state.show_web3 = not st.session_state.get("show_web3", False)
            st.rerun()

        if st.session_state.get("show_web3", False):
            with st.container(border=True):
                mostrar_demo_web3(st.session_state.ultimo_lote, st.session_state.ultimo_hash)


# ============================================================
# ABA FRAUDE
# ============================================================

with tab_fraude:

    st.header("Simulação de Ataque e Recuperação")
    st.divider()

    colA, colB, colC = st.columns(3)

    with colA:
        node_target = st.selectbox("Nó para corromper:", list(nos.keys()))
        tipo_corr = st.radio("Tipo de ataque:", ["Alterar último bloco (dados)", "Alterar hash final"])

    # ============================================================
    # ATAQUE
    # ============================================================

    with colB:
        if st.button("💣 Corromper nó"):
            df = nos[node_target].copy()

            if len(df) == 0:
                st.warning("Nó vazio — nada para corromper.")
            else:
                idx = len(df) - 1
                original = df.iloc[idx].to_dict()

                # CORRUPÇÃO
                if tipo_corr == "Alterar último bloco (dados)":
                    eventos_orig = df.at[idx, "eventos"]
                    df.at[idx, "eventos"] = str(eventos_orig) + " 🚨 BLOCO ALTERADO"
                    df.at[idx, "hash_atual"] = gerar_hash(df.at[idx, "eventos"], df.at[idx, "hash_anterior"])
                else:
                    df.at[idx, "hash_atual"] = gerar_hash("ATAQUE_MALICIOSO", df.at[idx, "hash_anterior"])

                nos[node_target] = df
                mod = df.iloc[idx].to_dict()

                registrar_auditoria("Sistema", "no_corrompido", f"{node_target} corrompido")

                st.error(f"Nó {node_target} foi corrompido!")

                comparação = pd.DataFrame([
                    {
                        "Campo": "Eventos",
                        "Antes": json.dumps(original.get("eventos"), ensure_ascii=False),
                        "Depois": json.dumps(mod.get("eventos"), ensure_ascii=False)
                    },
                    {
                        "Campo": "Hash Atual",
                        "Antes": original["hash_atual"][:16],
                        "Depois": mod["hash_atual"][:16]
                    }
                ])

                st.dataframe(comparação)

    # ============================================================
    # DETECÇÃO
    # ============================================================

    with colC:
        if st.button("🔍 Detectar divergência"):
            if validar_consenso(nos):
                st.success("Todos os nós estão íntegros.")
            else:
                st.warning("Divergência encontrada!")
                corrompidos = detectar_no_corrompido(nos)
                st.write("Nós corrompidos:", corrompidos)

    st.divider()

    # ============================================================
    # RECUPERAÇÃO
    # ============================================================

    if st.button("🧹 Recuperar nós corrompidos"):
        try:
            ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
            mais_frequente = max(set(ultimos.values()), key=list(ultimos.values()).count)
            nos = recuperar_no(nos, mais_frequente)
            st.success("Nós recuperados com sucesso!")
            registrar_auditoria("Sistema", "no_recuperado", "Recuperação concluída.")
        except Exception as e:
            st.error(f"Erro ao recuperar: {e}")

    # ============================================================
    # RESUMO FINAL
    # ============================================================

    if st.button("📊 Resumo dos nós"):
        for n, df in nos.items():
            st.markdown(f"### {n} — {len(df)} blocos")
            st.dataframe(df.tail(2))


