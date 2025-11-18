# ============================================================
# SmartLog Blockchain — Simulador de Consenso e Fraude (PoA)
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import json
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
    def criar_blockchain_inicial(df=None): return pd.DataFrame()
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
# CONFIGURAÇÃO DO LAYOUT
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain", layout="wide")
st.title("SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("Simulador didático de consenso Proof-of-Authority (PoA) para redes logísticas.")


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
    st.caption("🔧 Rodando localmente.")
else:
    st.caption("🌐 Rodando via rede distribuída entre múltiplos nós.")


# ============================================================
# CONFIG DOS NÓS REMOTOS (para modo distribuído)
# ============================================================
NOS_REMOTOS = {
    "Node_A": "http://127.0.0.1:5000",
    "Node_B": "http://127.0.0.1:5001",
    "Node_C": "http://127.0.0.1:5002"
}


# ============================================================
# ESTADO INICIAL
# ============================================================
if "nos" not in st.session_state:

    # eventos iniciais (didáticos)
    dados = {
        "id_entrega": [1, 2, 3],
        "source_center": ["Depósito_SP", "Depósito_SP", "Depósito_RJ"],
        "destination_name": ["Centro_MG", "Centro_PR", "Centro_BA"],
        "etapa": ["Saiu do depósito", "Em rota", "Chegou ao destino"],
        "timestamp": [datetime.now()] * 3,
        "risco": ["Baixo", "Médio", "Baixo"]
    }
    eventos_df = pd.DataFrame(dados)

    # modo local
    if modo_operacao == "Simulado (local)":
        blockchain_df = criar_blockchain_inicial(eventos_df)
        nos = criar_nos(blockchain_df)
        chaves = simular_chaves_privadas(nos)

    # modo distribuído
    else:
        nos = {"Node_A": pd.DataFrame(), "Node_B": pd.DataFrame(), "Node_C": pd.DataFrame()}
        chaves = {}

    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state.consenso_sucesso = False
    st.session_state.ultimo_lote = None
    st.session_state.ultimo_hash = None
    st.session_state.mostrar_web3 = False

nos = st.session_state.nos
chaves = st.session_state.chaves


# ============================================================
# FUNÇÃO PARA PROPOR BLOCO A NÓS REAIS
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
            votos[nome] = resposta.json()
        except:
            votos[nome] = {"erro": "Falha ao conectar"}
    return votos


# ============================================================
# INTERFACE — ABAS PRINCIPAIS
# ============================================================
tab_main, tab_fraude = st.tabs(["Consenso Principal", "Simulador de Fraude"])


# ============================================================
# ABA PRINCIPAL — CONSENSO POA
# ============================================================
with tab_main:
    st.header("Fluxo de Consenso Proof-of-Authority (PoA)")

    # STATUS DA REDE
    consenso_ok = validar_consenso(nos)
    if consenso_ok:
        st.success("🟢 Blockchain sincronizada entre todos os nós.")
    else:
        st.warning("🟠 Divergência detectada entre os nós!")

    # STATUS DOS HASHES FINAIS
    with st.expander("Status dos Nós — Hash Final", expanded=False):
        cols = st.columns(len(nos))
        for i, (nome, df) in enumerate(nos.items()):
            último = df.iloc[-1]["hash_atual"] if len(df) else "VAZIO"
            with cols[i]:
                st.metric(
                    label=f"Nó {nome}",
                    value=f"{último[:12]}...{último[-6:]}" if último != "VAZIO" else "VAZIO",
                    delta=f"{len(df)} blocos"
                )

    st.divider()
    st.subheader("1. Proposta de Novo Bloco")

    col1, col2 = st.columns([2, 1])
    propositor = col1.selectbox("Nó propositor:", list(nos.keys()))
    quorum = col2.slider("Quorum mínimo:", 1, len(nos), 2)

    # FORMULÁRIO DE EVENTOS
    st.subheader("Cadastro de Lote de Eventos")

    num_eventos = st.number_input("Quantidade de eventos:", 1, 10, 3)
    lote_eventos = []

    for i in range(num_eventos):
        with st.expander(f"Evento {i+1}"):
            id_entrega = st.text_input(f"ID {i+1}", f"{100+i}")
            origem = st.text_input(f"Origem {i+1}", "Depósito_SP")
            destino = st.text_input(f"Destino {i+1}", "Centro_MG")
            etapa = st.selectbox(f"Etapa {i+1}", ["Saiu do depósito", "Em rota", "Chegou ao destino"])
            risco = st.selectbox(f"Risco {i+1}", ["Baixo", "Médio", "Alto"])

            lote_eventos.append({
                "id_entrega": id_entrega,
                "origem": origem,
                "destino": destino,
                "etapa": etapa,
                "risco": risco,
                "timestamp": datetime.now().isoformat()
            })

    # BOTÃO PARA INICIAR CONSENSO
    if st.button("🚀 Iniciar Consenso", use_container_width=True):

        try:
            hash_anterior = nos[propositor].iloc[-1]["hash_atual"]

            # Criar proposta
            proposta = sb.propor_bloco(propositor, lote_eventos, hash_anterior)

            # Votação
            proposta = sb.votar_proposta(proposta, nos, chaves)

            # Aplicação do consenso
            sucesso, tx_id = sb.aplicar_consenso(proposta, nos, quorum)

            if sucesso:
                st.success("✅ Consenso alcançado! Bloco adicionado.")
                st.session_state.consenso_sucesso = True
                st.session_state.ultimo_lote = lote_eventos
                st.session_state.ultimo_hash = proposta["hash_bloco"]

                st.json(lote_eventos)

                registrar_auditoria("Sistema", "consenso_aprovado",
                                    f"Bloco com {len(lote_eventos)} eventos aceito.")

            else:
                st.warning("❌ Quorum insuficiente. Bloco rejeitado.")

        except Exception as e:
            st.error(f"Erro na simulação: {e}")
            st.stop()

    # AUDITORIA DE HASHES
    if st.session_state.consenso_sucesso:

        st.divider()
        st.subheader("Auditoria de Hashes")

        registros = []
        for nome, df in nos.items():
            if len(df) >= 2:
                ant = df.iloc[-2]["hash_atual"]
                atu = df.iloc[-1]["hash_atual"]
                registros.append({
                    "Nó": nome,
                    "Anterior": ant[:12],
                    "Atual": atu[:12],
                    "Mudou?": "Sim" if ant != atu else "Não"
                })

        st.dataframe(pd.DataFrame(registros), use_container_width=True)

        # WEB3 SIMULADA
        st.divider()
        st.subheader("🌐 Integração Web3 (Simulada)")

        if st.button("Mostrar / Ocultar Web3"):
            st.session_state.mostrar_web3 = not st.session_state.mostrar_web3
            st.rerun()

        if st.session_state.mostrar_web3:
            mostrar_demo_web3(st.session_state.ultimo_lote, st.session_state.ultimo_hash)


# ============================================================
# ABA DE FRAUDE — ATAQUES E RECUPERAÇÃO
# ============================================================
with tab_fraude:
    st.header("⚠️ Simulação de Ataques e Recuperação de Nós")

    colA, colB, colC = st.columns(3)

    # Escolha de nó
    node_to_corrupt = colA.selectbox("Escolha o nó", list(nos.keys()))
    corrupt_type = colA.radio("Tipo de corrupção:", ["Alterar último bloco (dados)", "Alterar hash final"])

    # BOTÃO DE ATAQUE
    if colB.button("💣 Corromper nó"):

        df = nos[node_to_corrupt].copy()

        if len(df) == 0:
            st.warning("⚠️ Nó vazio.")
        else:
            idx = len(df) - 1
            original = df.iloc[idx].to_dict()

            # ATAQUE
            if corrupt_type == "Alterar último bloco (dados)":
                eventos_orig = df.at[idx, "eventos"]

                if isinstance(eventos_orig, dict):
                    eventos_str = json.dumps(eventos_orig, ensure_ascii=False)
                else:
                    eventos_str = str(eventos_orig)

                eventos_new = eventos_str + " 🚨(ALTERADO)"
                df.at[idx, "eventos"] = eventos_new
                df.at[idx, "hash_atual"] = sb.gerar_hash(eventos_new, df.at[idx, "hash_anterior"])

            else:
                df.at[idx, "hash_atual"] = sb.gerar_hash("ATAQUE_MALICIOSO", df.at[idx, "hash_anterior"])

            nos[node_to_corrupt] = df
            modificado = df.iloc[idx].to_dict()

            st.error(f"⚠️ Nó {node_to_corrupt} corrompido!")

            # Comparação
            antes = original["eventos"]
            depois = modificado["eventos"]

            try:
                antes = json.dumps(antes, ensure_ascii=False, indent=2)
            except:
                antes = str(antes)

            try:
                depois = json.dumps(depois, ensure_ascii=False, indent=2)
            except:
                depois = str(depois)

            comparacao = pd.DataFrame([
                {"Campo": "Eventos", "Antes": antes, "Depois": depois},
                {"Campo": "Hash Atual", "Antes": original["hash_atual"][:16], "Depois": modificado["hash_atual"][:16]},
                {"Campo": "Hash Anterior", "Antes": original["hash_anterior"][:16], "Depois": modificado["hash_anterior"][:16]},
            ])

            st.dataframe(comparacao, use_container_width=True)

    # DETECTAR DIVERGÊNCIA
    if colC.button("🔍 Detectar Divergência"):
        if validar_consenso(nos):
            st.success("🟢 Nenhuma divergência encontrada.")
        else:
            st.warning("🟠 Divergência detectada!")
            divergentes = detectar_no_corrompido(nos)
            st.write("Nós divergentes:", divergentes)

    st.divider()

    # RECUPERAÇÃO
    if st.button("🧹 Recuperar Nós Corrompidos"):
        try:
            ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
            freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
            hash_ok = max(freq, key=freq.get)

            nos = recuperar_no(nos, hash_ok)
            st.success("Nós restaurados com sucesso.")

        except Exception as e:
            st.error(f"Erro na recuperação: {e}")

    # RESUMO FINAL
    if st.button("📊 Resumo das Blockchains"):
        for nome, df in nos.items():
            st.markdown(f"### Nó {nome} — {len(df)} blocos")
            st.dataframe(df.tail(3), use_container_width=True)


