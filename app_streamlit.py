# ============================================================
# SmartLog Blockchain — Simulador de Consenso e Fraude
# ============================================================
# Interface visual que demonstra consenso Proof-of-Authority
# com simulação de corrupção e recuperação de nós.
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import uuid

# ------------------------------------------------------------
# Importações internas
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
    # Stubs para evitar falhas
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

st.markdown("""
*Simulador de consenso Proof-of-Authority para redes logísticas e privadas.*
""")

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
    blockchain_df = criar_blockchain_inicial(eventos_df)
    nos = criar_nos(blockchain_df)
    chaves = simular_chaves_privadas(nos)

    st.session_state.blockchain_df = blockchain_df
    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state["mostrar_web3"] = False
    st.session_state["web3_evento_texto"] = None
    st.session_state["web3_hash"] = None
    st.session_state["consenso_sucesso"] = False

nos = st.session_state.nos
chaves = st.session_state.chaves

# ============================================================
# INTERFACE EM ABAS
# ============================================================
tab_main, tab_fraude = st.tabs(["Consenso Principal", "Simulador de Fraude"])

# ============================================================
# ABA PRINCIPAL — CONSENSO
# ============================================================
with tab_main:
    st.header("Fluxo de Consenso Proof-of-Authority")

    consenso_ok = validar_consenso(nos)
    status_msg = f"Blockchain com **{len(next(iter(nos.values())))}** blocos."
    if consenso_ok:
        st.success(f"Sistema sincronizado e íntegro. {status_msg}")
    else:
        st.warning(f"Divergência detectada entre os nós. {status_msg}")

    st.divider()

    # --------------------------------------------------------
    # PROPOSTA DE NOVO BLOCO
    # --------------------------------------------------------
    st.subheader("1. Proposta e Votação de Novo Bloco")
    with st.container(border=True):
        col_prop, col_quorum = st.columns([2, 1])
        with col_prop:
            propositor = st.selectbox("Nó propositor:", list(nos.keys()))
        with col_quorum:
            quorum = st.slider("Quorum mínimo:", 1, len(nos), 2)
            st.caption(f"Quorum: {quorum}/{len(nos)} nós")

        evento_texto = st.text_input("Descrição do evento:", "Entrega #104 — Saiu do depósito — SP → MG")

        if st.button("🚀 Iniciar Simulação de Consenso", use_container_width=True):
            st.session_state["consenso_sucesso"] = False
            st.info(f"Proposta: {propositor} propôs o bloco '{evento_texto}'")

            hashes_finais = [df.iloc[-1]["hash_atual"] for df in nos.values()]
            hash_anterior = max(set(hashes_finais), key=hashes_finais.count)

            try:
                proposta = sb.propor_bloco(propositor, evento_texto, hash_anterior)
                proposta = sb.votar_proposta(proposta, nos, chaves)
            except Exception as e:
                st.error(f"Erro na proposta/votação: {e}")
                st.stop()

            st.markdown("##### Votação dos Nós")
            col_votes = st.columns(len(nos))
            votos_sim = 0
            for i, (no, assinatura) in enumerate(proposta["assinaturas"].items()):
                with col_votes[i]:
                    if assinatura.startswith("Recusado"):
                        st.error(f"{no}: recusou")
                    else:
                        st.success(f"{no}: assinou")
                        votos_sim += 1

            sucesso = sb.aplicar_consenso(proposta, nos, quorum=quorum)

            if sucesso:
                st.session_state["consenso_sucesso"] = True
                novo_hash_display = proposta["hash_bloco"][:16]
                st.success(f"✅ Consenso alcançado! Bloco adicionado. Novo Hash: `{novo_hash_display}...`")

                registrar_auditoria(
                    "Sistema",
                    "consenso_aprovado",
                    f"Bloco '{evento_texto}' aceito (quorum {quorum})"
                )

                # --------------------------------------------------------
                # 🔍 AUDITORIA DE HASHES (Antes e Depois)
                # --------------------------------------------------------
                st.markdown("##### Auditoria de Hashes dos Nós (Antes ➜ Depois)")
                comparacao_hash = []
                for nome, df in nos.items():
                    if len(df) >= 2:
                        hash_anterior = df.iloc[-2]['hash_atual']
                        hash_atual = df.iloc[-1]['hash_atual']
                        mudou = hash_anterior != hash_atual
                        comparacao_hash.append({
                            "Nó": nome,
                            "Hash Anterior": f"{hash_anterior[:8]}...{hash_anterior[-8:]}",
                            "Hash Atual": f"{hash_atual[:8]}...{hash_atual[-8:]}",
                            "Mudou?": "Sim" if mudou else "Não"
                        })

                df_comp = pd.DataFrame(comparacao_hash)
                def color_diff(val):
                    return "color: #d9534f;" if val == "Sim" else "color: #5cb85c;"
                st.dataframe(
                    df_comp.style.applymap(color_diff, subset=["Mudou?"]),
                    use_container_width=True
                )

                # Dados para Web3
                st.session_state["web3_evento_texto"] = evento_texto
                st.session_state["web3_hash"] = proposta["hash_bloco"]
                st.session_state["mostrar_web3"] = False
            else:
                st.warning("❌ Quorum insuficiente. O bloco foi rejeitado.")
                registrar_auditoria("Sistema", "consenso_rejeitado", f"Bloco '{evento_texto}' rejeitado")

    # --------------------------------------------------------
    # VISUALIZAÇÃO WEB3 — ATIVADA POR BOTÃO
    # --------------------------------------------------------
    if st.session_state["web3_evento_texto"]:
        st.divider()
        if st.button("🔗 Mostrar / Ocultar Integração Web3", use_container_width=True):
            st.session_state["mostrar_web3"] = not st.session_state["mostrar_web3"]
            st.rerun()

        if st.session_state["mostrar_web3"]:
            with st.container(border=True):
                mostrar_demo_web3(st.session_state["web3_evento_texto"], st.session_state["web3_hash"])

# ============================================================
# ABA 2 — FRAUDE
# ============================================================
with tab_fraude:
    st.header("Simulação de Ataque e Recuperação de Nós")
    st.markdown("Demonstração didática de corrupção proposital em um nó.")
    st.divider()

    with st.container(border=True):
        st.subheader("1. Simular Ataque")
        colA, colB = st.columns(2)
        with colA:
            node_to_corrupt = st.selectbox("Escolha o nó:", list(nos.keys()))
            corrupt_type = st.radio("Tipo de corrupção:", ["Alterar último bloco", "Alterar hash final"])
        with colB:
            if st.button("⚠️ Corromper Nó", use_container_width=True):
                df = nos[node_to_corrupt].copy()
                if len(df) > 0:
                    idx = len(df) - 1
                    original = df.iloc[idx].copy().to_dict()
                    if corrupt_type == "Alterar último bloco":
                        df.at[idx, "etapa"] += " (ALTERADO)"
                        conteudo = f"{df.at[idx,'id_entrega']}-{df.at[idx,'source_center']}-{df.at[idx,'destination_name']}-{df.at[idx,'etapa']}-{df.at[idx,'timestamp']}-{df.at[idx,'risco']}"
                        df.at[idx, "hash_atual"] = gerar_hash(conteudo, df.at[idx, "hash_anterior"])
                    else:
                        df.at[idx, "hash_atual"] = "FRAUDE" + str(uuid.uuid4())[:58]
                    nos[node_to_corrupt] = df
                    st.error(f"Nó {node_to_corrupt} corrompido!")
                else:
                    st.warning("Nenhum bloco encontrado.")

    st.divider()
    with st.container(border=True):
        st.subheader("2. Detecção e Recuperação")
        colC, colD = st.columns(2)
        with colC:
            if st.button("🔍 Detectar divergência", use_container_width=True):
                if validar_consenso(nos):
                    st.success("Todos os nós estão íntegros.")
                else:
                    corrompidos = detectar_no_corrompido(nos)
                    st.error(f"Nós divergentes: {', '.join(corrompidos)}")
        with colD:
            if st.button("♻️ Recuperar nós", use_container_width=True):
                ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
                freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
                hash_ok = max(freq, key=freq.get)
                nos = recuperar_no(nos, hash_ok)
                st.success("Nós restaurados com sucesso.")

# ============================================================
# FIM DO ARQUIVO
# ============================================================
