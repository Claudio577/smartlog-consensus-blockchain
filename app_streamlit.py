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

# ------------------------------------------------------------
# Importações internas (Preservadas da estrutura original)
# ------------------------------------------------------------
# ATENÇÃO: Estes módulos devem ser fornecidos separadamente
# se a aplicação for executada fora deste ambiente.
# Assumimos que estão disponíveis no PATH.
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
        gerar_hash # Adicionado gerar_hash para a lógica de corrupção
    )
except ImportError as e:
    st.error(f"Erro de importação. Certifique-se de que os módulos auxiliares (smartlog_blockchain, audit_logger, web3_demo_simulado, firebase_utils) estão definidos: {e}")
    # Definindo um stub para gerar_hash para evitar erro de NameError no tab_fraude
    def gerar_hash(*args): return "HASH_STUB"
    # Adicionando stubs para as funções principais para permitir que o app carregue
    def criar_blockchain_inicial(df): return pd.DataFrame()
    def criar_nos(df): return {"Node_A": df}
    def simular_chaves_privadas(nos): return {}
    def validar_consenso(nos): return True
    def detectar_no_corrompido(nos): return []
    def recuperar_no(nos, hash_ok): return nos


# ============================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain", layout="wide")
st.title("🛡️ SmartLog Blockchain — Simulador de Consenso (PoA)")

st.markdown("""
*Imagine uma Blockchain não como uma rede pública (como o Bitcoin), mas sim como um cartório digital ultra-seguro gerenciado por Membros da Rede Autorizados.*
""")

st.markdown("""
O **SmartLog Blockchain** demonstra o funcionamento de um consenso *Proof-of-Authority* em redes logísticas. 
Cada nó valida e assina digitalmente os blocos propostos. Se o número de assinaturas atinge o *quorum mínimo*, o bloco é aceito por toda a rede.
""")

# ============================================================
# ESTADO INICIAL — Blockchain e Nós
# ============================================================
if "nos" not in st.session_state:
    # --------------------------------------------------------
    # Inicialização dos dados (mantida a lógica original)
    # --------------------------------------------------------
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
    st.session_state.historico = []

nos = st.session_state.nos
chaves = st.session_state.chaves

# ============================================================
# INTERFACE EM ABAS
# ============================================================
tab_main, tab_fraude = st.tabs(["⚙️ Simulador de Consenso", "🚨 Simulador de Fraude / Ataque"])

# ============================================================
# ABA 1 — CONSENSO PRINCIPAL (Layout Otimizado)
# ============================================================
with tab_main:
    st.header("Fluxo de Consenso Proof-of-Authority (PoA)")
    
    # --------------------------------------------------------
    # STATUS DA REDE - Uso de st.expander para Metrics
    # --------------------------------------------------------
    consenso_ok = validar_consenso(nos)
    
    status_msg = f"Blockchain com **{len(next(iter(nos.values())))}** blocos."
    if consenso_ok:
        st.success(f"✅ Todos os nós estão sincronizados e íntegros. {status_msg}")
    else:
        st.warning(f"⚠️ Divergência detectada entre os nós! Verifique a seção 'Status da Rede'. {status_msg}")

    with st.expander("Status da Rede e Hashes Finais", expanded=False):
        col_metrics = st.columns(len(nos))
        for i, (nome, df) in enumerate(nos.items()):
            hash_display = df.iloc[-1]['hash_atual'][:12] if len(df) > 0 else "VAZIO"
            
            # Usando st.metric em colunas para uma visualização limpa
            with col_metrics[i]:
                st.metric(
                    label=f"Nó: {nome}",
                    value=f"{hash_display}...",
                    delta=f"Blocos: {len(df)}"
                )
    
    st.divider()

    # --------------------------------------------------------
    # PROPOSTA DE NOVO BLOCO - Organização em Card/Container
    # --------------------------------------------------------
    st.subheader("1. Propor Novo Bloco e Votação")
    with st.container(border=True):
        
        col_prop, col_quorum = st.columns([2, 1])

        with col_prop:
            propositor = st.selectbox(
                "🧑‍💻 Nó Propositor (Assina e envia):",
                list(nos.keys()),
                key="select_propositor_main"
            )

        with col_quorum:
            quorum = st.slider(
                "🔢 Quorum Mínimo para Aprovação:",
                1, len(nos), 2,
                key="slider_quorum_main"
            )
            st.caption(f"Quorum necessário: **{quorum}** de {len(nos)} votos.")

        evento_texto = st.text_input(
            "📝 Descrição do novo evento (dados do bloco de logística):",
            "Entrega #104 — Saiu do depósito — SP → MG",
            key="input_evento_main"
        )

        st.markdown("---")
        if st.button("🚀 INICIAR SIMULAÇÃO DE CONSENSO", key="botao_consenso_main", type="primary", use_container_width=True):
            
            st.info(f"**Proposta:** {propositor} está propondo o bloco: **'{evento_texto}'**")

            hashes_finais = [df.iloc[-1]["hash_atual"] for df in nos.values()]
            
            # Lógica para garantir que o hash anterior seja o da maioria (evitando nós corrompidos)
            try:
                hash_anterior = max(set(hashes_finais), key=hashes_finais.count)
            except ValueError:
                hash_anterior = "0" * 64 # Hash inicial se a blockchain estiver vazia

            try:
                proposta = sb.propor_bloco(propositor, evento_texto, hash_anterior)
                proposta = sb.votar_proposta(proposta, nos, chaves)
            except Exception as e:
                st.error(f"❌ Erro na fase de Proposta/Votação: {e}")
                st.stop()

            st.markdown("##### Votação dos Nós (Assinaturas)")
            col_votes = st.columns(len(nos))
            votos_sim = 0
            for i, (no, assinatura) in enumerate(proposta["assinaturas"].items()):
                with col_votes[i]:
                    if assinatura.startswith("Recusado"):
                        st.error(f"⛔ {no} recusou")
                    else:
                        st.success(f"✍️ {no} assinou")
                        votos_sim += 1

            st.markdown("---")
            st.markdown("##### 2. Aplicação do Consenso")
            st.write(f"Votos válidos: **{votos_sim}**. Quorum necessário: **{quorum}**.")

            try:
                sucesso = sb.aplicar_consenso(proposta, nos, quorum=quorum)
            except Exception as e:
                st.error(f"❌ Erro ao aplicar consenso: {e}")
                sucesso = False

            if sucesso:
                st.balloons()
                st.success("🎉 Consenso alcançado! O bloco foi adicionado em todos os nós.")
                registrar_auditoria(
                    "Sistema",
                    "consenso_aprovado",
                    f"Bloco '{evento_texto}' aceito (quorum {quorum})"
                )

                st.session_state["web3_evento_texto"] = evento_texto
                st.session_state["web3_hash"] = proposta["hash_bloco"]
                st.session_state["mostrar_web3"] = True # Mostrar automaticamente em caso de sucesso

            else:
                st.warning("💔 Quorum insuficiente. O bloco foi rejeitado e não foi adicionado.")
                registrar_auditoria(
                    "Sistema",
                    "consenso_rejeitado",
                    f"Bloco '{evento_texto}' rejeitado (quorum {quorum})"
                )
                st.session_state["mostrar_web3"] = False # Esconder o painel Web3 se rejeitado

    # --------------------------------------------------------
    # VISUALIZAÇÃO WEB3 — ESTILO LIMPO E CENTRALIZADO
    # --------------------------------------------------------
    if "web3_evento_texto" in st.session_state and st.session_state["web3_evento_texto"]:
        st.divider()
        st.subheader("3. Detalhes da Transação na Blockchain (Web3 Simulado)")
        st.caption("A transação (bloco) aceita é refletida no Explorer.")

        # Inicializa o estado de exibição se ainda não existir
        if "mostrar_web3" not in st.session_state:
            st.session_state["mostrar_web3"] = False

        if st.session_state["mostrar_web3"]:
            with st.container(border=True):
                mostrar_demo_web3(
                    st.session_state["web3_evento_texto"],
                    st.session_state["web3_hash"]
                )
            if st.button("Esconder Detalhes Web3", key="hide_web3", use_container_width=True):
                st.session_state["mostrar_web3"] = False
                st.rerun()
        else:
            if st.button("Mostrar Detalhes Web3", key="show_web3", use_container_width=True):
                st.session_state["mostrar_web3"] = True
                st.rerun()


    # --------------------------------------------------------
    # UTILITÁRIOS FIRESTORE E AUDITORIA - Layout em colunas
    # --------------------------------------------------------
    st.divider()
    st.subheader("🗄️ Utilitários de Sincronização e Auditoria")

    col_sync, col_audit = st.columns(2)

    with col_sync:
        with st.container(border=True):
            st.markdown("##### Sincronização e Gestão de Dados (Firestore)")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📥 Carregar da Nuvem", use_container_width=True):
                    df = carregar_blockchain_firestore()
                    if df is not None:
                        st.session_state.blockchain_df = df
                        nos["Node_A"] = df
                        st.success("Blockchain carregada e Node_A atualizado!")
                    else:
                        st.warning("Nenhum dado encontrado no Firestore.")

            with col2:
                if st.button("📤 Salvar Manualmente", use_container_width=True):
                    try:
                        salvar_blockchain_firestore(nos["Node_A"])
                        st.success("Blockchain salva manualmente!")
                    except Exception as e:
                        st.error(f"Erro ao salvar blockchain: {e}")

            with col3:
                if st.button("🧹 Resetar Tudo", use_container_width=True):
                    try:
                        limpar_blockchain_firestore()
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        st.error("Blockchain removida e sessão reiniciada. Por favor, **Recarregue a página (Rerun)**.")
                        st.stop()
                    except Exception as e:
                        st.error(f"Erro ao limpar Firestore: {e}")

    with col_audit:
        with st.container(border=True):
            st.markdown("##### Log de Auditoria Manual")
            col_audit_actor, col_audit_message = st.columns([1, 2])

            with col_audit_actor:
                audit_actor = st.selectbox(
                    "Ator/Fonte do Log:",
                    ["Usuário-Streamlit", "Sistema", "Nó de Validação"],
                    key="audit_actor"
                )

            with col_audit_message:
                audit_message = st.text_input(
                    "Mensagem de Auditoria (Ação):",
                    "Evento de teste manual disparado.",
                    key="audit_message"
                )

            if st.button("📝 Enviar Log de Auditoria", key="botao_teste_auditoria", use_container_width=True):
                try:
                    registrar_auditoria(audit_actor, "teste_envio_manual", audit_message)
                    st.success(f"Log enviado: {audit_actor} registrou '{audit_message}'")
                except Exception as e:
                    st.error(f"Erro ao registrar auditoria: {e}")

# ============================================================
# ABA 2 — SIMULADOR DE FRAUDE
# ============================================================
with tab_fraude:
    st.header("Simulação de Ataque e Recuperação de Nós")
    st.markdown("""
    Demonstração **didática** de corrupção proposital em um nó. 
    Observe como a integridade dos dados é quebrada e como o sistema detecta e recupera divergências.
    """)
    st.divider()

    # --------------------------------------------------------
    # Simular Ataque
    # --------------------------------------------------------
    with st.container(border=True):
        st.subheader("🔴 1. Simular Ataque e Quebra de Integridade")
        
        colA, colB = st.columns([1, 1])

        with colA:
            node_to_corrupt = st.selectbox("Escolha o nó para corromper:", list(nos.keys()), key="fraude_node")
            corrupt_type = st.radio("Tipo de corrupção:", ["Alterar último bloco (dados)", "Alterar hash final"])

        with colB:
            st.markdown(" ") # Espaçamento
            if st.button("🚨 CORROMPER NÓ (Simular ataque)", key="fraude_attack", type="secondary", use_container_width=True):
                df = nos[node_to_corrupt].copy()
                if len(df) > 0:
                    idx = len(df) - 1
                    original = df.iloc[idx].copy().to_dict()

                    if corrupt_type == "Alterar último bloco (dados)":
                        # Altera os dados e recalcula o hash para o novo conteúdo (incorreto)
                        df.at[idx, "etapa"] = str(df.at[idx, "etapa"]) + " (ALTERADO MALICIOSAMENTE)"
                        conteudo = f"{df.at[idx,'id_entrega']}-{df.at[idx,'source_center']}-{df.at[idx,'destination_name']}-{df.at[idx,'etapa']}-{df.at[idx,'timestamp']}-{df.at[idx,'risco']}"
                        
                        # Precisa da função gerar_hash do smartlog_blockchain
                        try:
                            df.at[idx, "hash_atual"] = sb.gerar_hash(conteudo, df.at[idx, "hash_anterior"])
                        except NameError:
                            df.at[idx, "hash_atual"] = hashlib.sha256((conteudo + df.at[idx, "hash_anterior"]).encode()).hexdigest()
                    
                    else:
                        # Altera o hash final diretamente, mantendo os dados intactos, quebrando o elo.
                        df.at[idx, "hash_atual"] = "FRAUDE" + df.at[idx, "hash_atual"][6:]

                    nos[node_to_corrupt] = df
                    modificado = df.iloc[idx].copy().to_dict()
                    st.error(f"🔴 {node_to_corrupt} corrompido (simulado).")
                    registrar_auditoria("Sistema", "no_corrompido", f"{node_to_corrupt} corrompido ({corrupt_type})")

                    st.markdown("##### Comparação do Bloco Corrompido:")
                    comparacao = pd.DataFrame([
                        {"Campo": "Etapa", "Antes": original["etapa"], "Depois": modificado["etapa"]},
                        {"Campo": "Hash Atual", "Antes": original["hash_atual"][:16] + "...", "Depois": modificado["hash_atual"][:16] + "..."},
                    ])
                    st.dataframe(comparacao, use_container_width=True)
                else:
                    st.warning("Este nó não contém blocos para corromper.")

    st.divider()

    # --------------------------------------------------------
    # Detecção e Recuperação
    # --------------------------------------------------------
    with st.container(border=True):
        st.subheader("🟢 2. Detecção e Recuperação de Consenso")

        colC, colD = st.columns(2)

        with colC:
            if st.button("🔍 Detectar divergência", key="fraude_detect", use_container_width=True):
                if validar_consenso(nos):
                    st.success("✅ Todos os nós estão íntegros e sincronizados.")
                else:
                    corrompidos = detectar_no_corrompido(nos)
                    st.error("❌ Divergência detectada entre os nós!")
                    st.warning(f"Nós corrompidos identificados: **{', '.join(corrompidos)}**")

        with colD:
            if st.button("🩹 Recuperar nós corrompidos", key="fraude_recover", type="primary", use_container_width=True):
                try:
                    ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items() if len(df) > 0}
                    
                    if not ultimos:
                        st.warning("Nenhum nó tem blocos para recuperar.")
                    else:
                        # Encontra o hash majoritário (o correto)
                        freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
                        hash_ok = max(freq, key=freq.get)
                        
                        # Aplica a recuperação (substitui a DF dos corrompidos pela DF que tem o hash_ok)
                        nos = recuperar_no(nos, hash_ok)
                        st.success("✅ Nós corrompidos restaurados com sucesso para o estado majoritário!")
                        registrar_auditoria("Sistema", "no_recuperado", "Nós restaurados com base no hash majoritário.")
                except Exception as e:
                    st.error(f"Erro ao restaurar nós: {e}")

    st.divider()

    if st.button("📊 Mostrar Resumo Completo das Blockchains (por Nó)", key="fraude_summary"):
        for nome, df in nos.items():
            hash_final = df.iloc[-1]['hash_atual'][:16] if len(df) > 0 else "VAZIO"
            st.markdown(f"**{nome}** — **{len(df)}** blocos — hash final `{hash_final}...`")
            st.dataframe(
                df[["bloco_id", "id_entrega", "source_center", "destination_name", "etapa", "hash_atual"]].tail(5),
                use_container_width=True
            )

# ============================================================
# FIM DO ARQUIVO
# ============================================================


# ============================================================
# FIM DO ARQUIVO
# ============================================================

