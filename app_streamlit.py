# ============================================================
# SmartLog Blockchain — Simulador de Consenso e Fraude
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
    st.session_state["df_auditoria_hash"] = None

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
            hash_display = df.iloc[-1]["hash_atual"] if len(df) > 0 else "VAZIO"
            with cols[i]:
                st.metric(
                    label=f"Nó {nome}",
                    value=f"{hash_display[:12]}...{hash_display[-6:]}",
                    delta=f"Blocos: {len(df)}"
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
            hashes_finais = [df.iloc[-1]["hash_atual"] for df in nos.values()]
            hash_anterior = max(set(hashes_finais), key=hashes_finais.count)

            try:
                proposta = sb.propor_bloco(propositor, evento_texto, hash_anterior)
                proposta = sb.votar_proposta(proposta, nos, chaves)
            except Exception as e:
                st.error(f"Erro na proposta/votação: {e}")
                st.stop()

            votos_sim = sum(1 for a in proposta["assinaturas"].values() if not a.startswith("Recusado"))
            sucesso = sb.aplicar_consenso(proposta, nos, quorum=quorum)

            if sucesso:
                st.session_state["consenso_sucesso"] = True
                st.session_state["ultimo_evento"] = evento_texto
                st.session_state["ultimo_hash"] = proposta["hash_bloco"]

                st.success(f"Consenso alcançado! Novo bloco adicionado. Hash: `{proposta['hash_bloco'][:16]}...`")

                registrar_auditoria("Sistema", "consenso_aprovado",
                                    f"Bloco '{evento_texto}' aceito (quorum {quorum})")

                # Monta a auditoria de hashes
                comparacao_hash = []
                for nome, df in nos.items():
                    if len(df) >= 2:
                        hash_ant = df.iloc[-2]['hash_atual']
                        hash_atu = df.iloc[-1]['hash_atual']
                        mudou = hash_ant != hash_atu
                        comparacao_hash.append({
                            "Nó": nome,
                            "Hash Anterior": f"{hash_ant[:8]}...{hash_ant[-8:]}",
                            "Hash Atual": f"{hash_atu[:8]}...{hash_atu[-8:]}",
                            "Mudou?": "Sim" if mudou else "Não"
                        })
                st.session_state["df_auditoria_hash"] = pd.DataFrame(comparacao_hash)

                st.session_state["web3_evento_texto"] = evento_texto
                st.session_state["web3_hash"] = proposta["hash_bloco"]
                st.session_state["mostrar_web3"] = False

            else:
                st.warning("Quorum insuficiente. Bloco rejeitado.")
                registrar_auditoria("Sistema", "consenso_rejeitado",
                                    f"Bloco '{evento_texto}' rejeitado.")

    # --------------------------------------------------------
    # AUDITORIA E BOTÃO DE NOVO BLOCO (PERSISTENTE)
    # --------------------------------------------------------
    if st.session_state.get("consenso_sucesso", False):
        st.divider()
        st.subheader("Auditoria de Hashes (Antes ➜ Depois)")
        st.caption("Comparação dos hashes dos nós antes e depois da adição do bloco.")

        if st.session_state["df_auditoria_hash"] is not None:
            df_comp = st.session_state["df_auditoria_hash"]
            def color_diff(val): return "color:#d9534f" if val == "Sim" else "color:#5cb85c"
            st.dataframe(df_comp.style.applymap(color_diff, subset=["Mudou?"]),
                         use_container_width=True)

        st.divider()
        st.subheader("Adicionar Novo Bloco")
        st.caption("Crie uma nova proposta de bloco e inicie outra rodada de consenso.")
        if st.button("Criar Nova Proposta de Bloco", use_container_width=True, key="novo_bloco_global"):
            st.session_state["web3_evento_texto"] = None
            st.session_state["web3_hash"] = None
            st.session_state["mostrar_web3"] = False
            st.session_state["consenso_sucesso"] = False
            st.session_state["df_auditoria_hash"] = None
            st.rerun()

    # --------------------------------------------------------
    # VISUALIZAÇÃO WEB3 (SOMENTE POR BOTÃO)
    # --------------------------------------------------------
    if st.session_state["web3_evento_texto"]:
        st.divider()
        if st.button("Mostrar / Ocultar Integração Web3", use_container_width=True):
            st.session_state["mostrar_web3"] = not st.session_state["mostrar_web3"]
            st.rerun()

        if st.session_state["mostrar_web3"]:
            with st.container(border=True):
                mostrar_demo_web3(st.session_state["web3_evento_texto"],
                                  st.session_state["web3_hash"])

    # --------------------------------------------------------
    # FIRESTORE E AUDITORIA MANUAL
    # --------------------------------------------------------
    st.divider()
    st.subheader("Utilitários Firestore e Logs")

    col_sync, col_audit = st.columns(2)

    with col_sync:
        with st.container(border=True):
            st.markdown("##### Sincronização com Firestore")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Carregar da Nuvem", use_container_width=True):
                    df = carregar_blockchain_firestore()
                    if df is not None:
                        st.session_state.blockchain_df = df
                        nos["Node_A"] = df
                        st.success("Blockchain carregada com sucesso.")
                    else:
                        st.warning("Nenhum dado encontrado.")

            with col2:
                if st.button("Salvar Blockchain", use_container_width=True):
                    try:
                        salvar_blockchain_firestore(nos["Node_A"])
                        st.success("Blockchain salva na nuvem.")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

            with col3:
                if st.button("Resetar Firestore e Sessão", use_container_width=True):
                    try:
                        limpar_blockchain_firestore()
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.error("Sessão reiniciada. Recarregue a página.")
                        st.stop()
                    except Exception as e:
                        st.error(f"Erro ao limpar: {e}")

    with col_audit:
        with st.container(border=True):
            st.markdown("##### Log de Auditoria Manual")
            col_a1, col_a2 = st.columns([1, 2])
            with col_a1:
                audit_actor = st.selectbox("Ator:", ["Usuário", "Sistema", "Nó de Validação"])
            with col_a2:
                audit_msg = st.text_input("Mensagem:", "Teste de log manual.")
            if st.button("Registrar Log Manual", use_container_width=True):
                try:
                    registrar_auditoria(audit_actor, "log_manual", audit_msg)
                    st.success("Log registrado no Firestore.")
                except Exception as e:
                    st.error(f"Erro ao registrar log: {e}")

# ============================================================
# ABA FRAUDE — ATAQUE E RECUPERAÇÃO
# ============================================================
with tab_fraude:
    st.header("Simulação de Ataque e Recuperação de Nós")
    st.divider()

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
            if st.button("Detectar divergência", use_container_width=True):
                if validar_consenso(nos):
                    st.success("Todos os nós estão íntegros.")
                else:
                    corrompidos = detectar_no_corrompido(nos)
                    st.error(f"Nós divergentes: {', '.join(corrompidos)}")
        with colD:
            if st.button("Recuperar nós", use_container_width=True):
                ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
                freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
                hash_ok = max(freq, key=freq.get)
                nos = recuperar_no(nos, hash_ok)
                st.success("Nós restaurados com sucesso.")
