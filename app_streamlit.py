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

    if st.session_state.modo_operacao == "Simulado (local)":
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
    st.header("Fluxo de Consenso Proof-of-Authority (PoA)")

    consenso_ok = validar_consenso(nos)
    if consenso_ok:
        st.success("Sistema sincronizado e íntegro.")
    else:
        st.warning("Divergência detectada entre os nós.")

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

    col1, col2 = st.columns([2, 1])
    with col1:
        propositor = st.selectbox("Nó propositor:", list(nos.keys()))
    with col2:
        quorum = st.slider("Quorum mínimo:", 1, len(nos), 2)
        st.caption(f"Quorum necessário: {quorum}/{len(nos)}")

    # ============================================================
    # FORMULÁRIO DE LOTE DE EVENTOS
    # ============================================================
    st.subheader("Cadastro de Lote de Entregas")

    num_eventos = st.number_input("Número de eventos no lote:", min_value=1, max_value=10, value=3)

    lote_eventos = []
    for i in range(int(num_eventos)):
        with st.expander(f"Evento {i+1}", expanded=False):
            id_entrega = st.text_input(f"ID da entrega {i+1}", f"{100+i}")
            origem = st.text_input(f"Origem {i+1}", "Depósito_SP")
            destino = st.text_input(f"Destino {i+1}", "Centro_MG")
            etapa = st.selectbox(f"Etapa {i+1}", ["Saiu do depósito", "Em rota", "Chegou ao destino"])
            risco = st.selectbox(f"Risco {i+1}", ["Baixo", "Médio", "Alto"], index=0)
            lote_eventos.append({
                "id_entrega": id_entrega,
                "origem": origem,
                "destino": destino,
                "etapa": etapa,
                "risco": risco,
                "timestamp": datetime.now().isoformat()
            })

    # ============================================================
    # SIMULAÇÃO DE CONSENSO
    # ============================================================
    if st.button("🚀 Iniciar Simulação de Consenso", use_container_width=True):
        st.session_state["consenso_sucesso"] = False
        st.info(f"O nó {propositor} propôs um novo bloco contendo {len(lote_eventos)} eventos.")

        try:
            if st.session_state.modo_operacao == "Simulado (local)":
                hash_anterior = nos[propositor].iloc[-1]["hash_atual"]
                proposta = sb.propor_bloco(propositor, lote_eventos, hash_anterior)
                proposta = sb.votar_proposta(proposta, nos, chaves)
                sucesso, tx_id = sb.aplicar_consenso(proposta, nos, quorum)
            else:
                hash_anterior = "GENESIS"
                st.info("Enviando proposta de bloco aos nós reais...")
                votos = propor_bloco_remoto(lote_eventos, hash_anterior)
                proposta = {
                    "propositor": propositor,
                    "eventos": lote_eventos,
                    "assinaturas": {k: v.get("assinatura", "erro") for k, v in votos.items()},
                    "hash_bloco": max([v.get("hash_bloco", "") for v in votos.values()], default="GENESIS")
                }
                sucesso = True

            if sucesso:
                st.session_state["consenso_sucesso"] = True
                st.session_state["ultimo_lote"] = lote_eventos
                st.session_state["ultimo_hash"] = proposta["hash_bloco"]

                st.success(f"✅ Consenso alcançado! Novo bloco adicionado com {len(lote_eventos)} eventos.")
                st.text_input("🔗 Hash do Bloco Confirmado:", proposta["hash_bloco"])

                st.markdown("### 📦 Eventos incluídos neste bloco:")
                st.json(lote_eventos)

                registrar_auditoria("Sistema", "consenso_aprovado", f"Bloco com {len(lote_eventos)} eventos aceito (quorum {quorum})")

            else:
                st.warning("⚠️ Quorum insuficiente. Bloco rejeitado.")

        except Exception as e:
            st.error(f"Erro na proposta/votação: {e}")
            st.stop()

    # ============================================================
    # AUDITORIA DE HASHES
    # ============================================================
    if st.session_state.get("consenso_sucesso", False):
        st.divider()
        st.subheader("Auditoria de Hashes (Antes ➜ Depois)")
        st.caption("Comparação dos hashes dos nós antes e depois da adição do bloco.")

        comparacao_hash = []
        for nome, df in nos.items():
            if len(df) >= 2 and "hash_atual" in df.columns:
                hash_ant = df.iloc[-2]["hash_atual"]
                hash_atu = df.iloc[-1]["hash_atual"]
                mudou = hash_ant != hash_atu
                comparacao_hash.append({
                    "Nó": nome,
                    "Hash Anterior": f"{hash_ant[:8]}...{hash_ant[-8:]}",
                    "Hash Atual": f"{hash_atu[:8]}...{hash_atu[-8:]}",
                    "Mudou?": "Sim" if mudou else "Não"
                })
            elif len(df) == 1:
                hash_atu = df.iloc[-1]["hash_atual"]
                comparacao_hash.append({
                    "Nó": nome,
                    "Hash Anterior": "-",
                    "Hash Atual": f"{hash_atu[:8]}...{hash_atu[-8:]}",
                    "Mudou?": "Novo bloco"
                })
            else:
                comparacao_hash.append({
                    "Nó": nome,
                    "Hash Anterior": "-",
                    "Hash Atual": "-",
                    "Mudou?": "Sem dados"
                })

        if comparacao_hash:
            df_comp = pd.DataFrame(comparacao_hash)
            st.dataframe(df_comp, use_container_width=True)
        else:
            st.info("Sem dados de auditoria disponíveis.")

        # ============================================================
        # VISUALIZAÇÃO WEB3
        # ============================================================
        if st.session_state.get("ultimo_evento"):
            st.divider()
            if st.button("Mostrar / Ocultar Integração Web3", use_container_width=True):
                st.session_state["mostrar_web3"] = not st.session_state["mostrar_web3"]
                st.rerun()

            if st.session_state["mostrar_web3"]:
                with st.container(border=True):
                    mostrar_demo_web3(st.session_state["ultimo_lote"], st.session_state["ultimo_hash"])

        # ============================================================
        # FIRESTORE E AUDITORIA MANUAL
        # ============================================================
        st.divider()
        st.subheader("Firestore & Auditoria de Logs")

        col_sync, col_audit = st.columns(2)

        with col_sync:
            with st.container(border=True):
                st.markdown("### Sincronização com Firestore")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Carregar", use_container_width=True):
                        df = carregar_blockchain_firestore()
                        if df is not None:
                            st.session_state.blockchain_df = df
                            nos["Node_A"] = df
                            st.success("Blockchain carregada da nuvem.")
                        else:
                            st.warning("Nenhum dado encontrado.")
                with col2:
                    if st.button("Salvar", use_container_width=True):
                        try:
                            salvar_blockchain_firestore(nos["Node_A"])
                            st.success("Blockchain salva na nuvem.")
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")
                with col3:
                    if st.button("Resetar", use_container_width=True):
                        limpar_blockchain_firestore()
                        for k in list(st.session_state.keys()):
                            del st.session_state[k]
                        st.error("Sessão reiniciada. Recarregue a página.")
                        st.stop()

        with col_audit:
            with st.container(border=True):
                st.markdown("### Log de Auditoria Manual")
                colA, colB = st.columns([1, 2])
                with colA:
                    audit_actor = st.selectbox("Ator:", ["Usuário", "Sistema", "Nó de Validação"])
                with colB:
                    audit_msg = st.text_input("Mensagem:", "Teste de log manual.")
                if st.button("Registrar Log", use_container_width=True):
                    registrar_auditoria(audit_actor, "log_manual", audit_msg)
                    st.success("Log registrado no Firestore.")


# ============================================================
# ABA FRAUDE — ATAQUE E RECUPERAÇÃO (versão avançada)
# ============================================================
with tab_fraude:
    st.header("Simulação de Ataque e Recuperação de Nós")
    st.divider()

    colA, colB, colC = st.columns(3)

    # ============================
    # 🎯 Seleção do nó e tipo de ataque
    # ============================
    with colA:
        node_to_corrupt = st.selectbox("Escolha o nó para ataque:", list(nos.keys()))
        corrupt_type = st.radio(
            "Tipo de corrupção:",
            ["Alterar último bloco (dados)", "Alterar hash final"],
            horizontal=True
        )

    # ============================
    # 🧨 Simular Ataque
    # ============================
    with colB:
        if st.button("💣 Corromper nó (simular ataque)", key="fraude_attack"):
            df = nos[node_to_corrupt].copy()
            if len(df) > 0:
                idx = len(df) - 1
                # Salva o estado original do último bloco
                original = df.iloc[idx].to_dict()

                # --- Aplica corrupção ---
                # Corrupção de bloco no novo formato (JSON de eventos)
                # --- Aplica corrupção ---
                if corrupt_type == "Alterar último bloco (dados)":
                    # Corrupção de bloco no novo formato (JSON de eventos)
                    eventos_json = df.at[idx, "eventos"]
                    df.at[idx, "eventos"] = str(eventos_json) + " 🚨 (BLOCO ALTERADO)"
                    conteudo_corrompido = str(df.at[idx, "eventos"])
                    df.at[idx, "hash_atual"] = sb.gerar_hash(conteudo_corrompido, df.at[idx, "hash_anterior"])
                else:
                     df.at[idx, "hash_atual"] = sb.gerar_hash("ATAQUE_MALICIOSO", df.at[idx, "hash_anterior"])

                # Atualiza nó
                nos[node_to_corrupt] = df
                modificado = df.iloc[idx].to_dict()

                # --- Mostra comparação didática ---
                st.error(f"⚠️ {node_to_corrupt} corrompido (simulado).")
                registrar_auditoria("Sistema", "no_corrompido", f"{node_to_corrupt} corrompido ({corrupt_type})")

                comparacao = pd.DataFrame([
                    {"Campo": "Etapa", "Antes": original["etapa"], "Depois": modificado["etapa"]},
                    {"Campo": "Hash Atual", "Antes": original["hash_atual"][:16], "Depois": modificado["hash_atual"][:16]},
                    {"Campo": "Hash Anterior", "Antes": original["hash_anterior"][:16], "Depois": modificado["hash_anterior"][:16]},
                ])
                st.dataframe(comparacao, use_container_width=True)
            else:
                st.warning("⚠️ Este nó não contém blocos para corromper.")

    # ============================
    # 🔍 Detectar divergências
    # ============================
    with colC:
        if st.button("🔍 Detectar divergência", key="fraude_detect"):
            if validar_consenso(nos):
                st.success("🟢 Todos os nós estão íntegros e sincronizados.")
            else:
                st.warning("🟠 Divergência detectada entre os nós!")
                corrompidos = detectar_no_corrompido(nos)
                st.write("Nós corrompidos identificados:", corrompidos)
                ultimos = {n: df.iloc[-1]["hash_atual"][:16] for n, df in nos.items()}
                st.dataframe(pd.DataFrame(list(ultimos.items()), columns=["Nó", "Hash final"]), use_container_width=True)

    # ============================
    # 🔁 Recuperação e Resumo
    # ============================
    st.markdown("---")
    if st.button("🧹 Recuperar nós corrompidos (copiar da maioria)", key="fraude_recover"):
        try:
            ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
            freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
            hash_ok = max(freq, key=freq.get)
            nos = recuperar_no(nos, hash_ok)
            st.success("✅ Nós corrompidos restaurados com sucesso usando a blockchain da maioria.")
        except Exception as e:
            st.error(f"❌ Erro ao restaurar nós: {e}")
        registrar_auditoria("Sistema", "no_recuperado", "Nós restaurados com base no hash majoritário.")

    # ============================
    # 📊 Resumo final das blockchains
    # ============================
    if st.button("📊 Mostrar resumo das blockchains (por nó)", key="fraude_summary"):
        for nome, df in nos.items():
            st.markdown(f"**{nome}** — {len(df)} blocos — hash final `{df.iloc[-1]['hash_atual'][:16]}...`")
            if "eventos" in df.columns:
                st.dataframe(df[["bloco_id", "timestamp", "hash_atual", "eventos"]].tail(2), use_container_width=True)
            else:
                st.dataframe(df.tail(2), use_container_width=True)


    
