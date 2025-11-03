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
# Importações internas (Preservadas da estrutura original)
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
        gerar_hash
    )
except ImportError as e:
    st.error(f"Erro de importação. Certifique-se de que os módulos auxiliares (smartlog_blockchain, audit_logger, web3_demo_simulado, firebase_utils) estão definidos: {e}")
    
    # Adicionando stubs para as funções principais para permitir que o app carregue
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
*Simulador de consenso Proof-of-Authority para redes privadas/consorciadas (ex: logística).*
""")
st.markdown("""
**Regra de Consenso:** Cada nó autorizado valida e assina digitalmente os blocos propostos. O bloco é aceito por toda a rede se o número de assinaturas atingir o *quorum mínimo* definido.
""")

# ============================================================
# ESTADO INICIAL — Blockchain e Nós
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
    st.session_state.historico = []
    st.session_state["mostrar_web3"] = False
    st.session_state["web3_evento_texto"] = None
    st.session_state["web3_hash"] = None
    st.session_state["consenso_sucesso"] = False # Flag para controlar o display Pós-Consenso


# Recupera o estado
nos = st.session_state.nos
chaves = st.session_state.chaves

# ============================================================
# INTERFACE EM ABAS
# ============================================================
tab_main, tab_fraude = st.tabs(["Consenso Principal", "Simulador de Fraude"])

# ============================================================
# ABA 1 — CONSENSO PRINCIPAL
# ============================================================
with tab_main:
    st.header("Fluxo de Consenso Proof-of-Authority (PoA)")
    
    # --------------------------------------------------------
    # STATUS DA REDE (Pré-Proposta)
    # --------------------------------------------------------
    consenso_ok = validar_consenso(nos)
    
    status_msg = f"Blockchain com **{len(next(iter(nos.values())))}** blocos."
    if consenso_ok:
        st.success(f"Sistema sincronizado e íntegro. {status_msg}")
    else:
        st.warning(f"Divergência detectada entre os nós. {status_msg}")

    with st.expander("Status da Rede e Hashes Finais (Antes da Proposta)", expanded=False):
        col_metrics = st.columns(len(nos))
        for i, (nome, df) in enumerate(nos.items()):
            # Aumentando o display do hash para 16 caracteres para melhor comparação
            hash_display = df.iloc[-1]['hash_atual'][:16] if len(df) > 0 else "VAZIO" 
            
            with col_metrics[i]:
                st.metric(
                    label=f"Nó: {nome}",
                    value=f"{hash_display}...",
                    delta=f"Blocos: {len(df)}"
                )
    
    st.divider()

    # --------------------------------------------------------
    # PROPOSTA DE NOVO BLOCO
    # --------------------------------------------------------
    st.subheader("1. Proposta e Votação de Novo Bloco")
    with st.container(border=True):
        
        col_prop, col_quorum = st.columns([2, 1])

        with col_prop:
            propositor = st.selectbox(
                "Nó Propositor (Assina e envia):",
                list(nos.keys()),
                key="select_propositor_main"
            )

        with col_quorum:
            quorum = st.slider(
                "Quorum Mínimo para Aprovação:",
                1, len(nos), 2,
                key="slider_quorum_main"
            )
            st.caption(f"Quorum necessário: **{quorum}** de {len(nos)} votos.")

        evento_texto = st.text_input(
            "Descrição do novo evento (dados do bloco de logística):",
            "Entrega #104 — Saiu do depósito — SP → MG",
            key="input_evento_main"
        )

        st.markdown("---")
        if st.button("INICIAR SIMULAÇÃO DE CONSENSO", key="botao_consenso_main", type="primary", use_container_width=True):
            
            # Resetamos a flag de sucesso ao iniciar nova proposta
            st.session_state["consenso_sucesso"] = False

            st.info(f"Proposta: O nó {propositor} está propondo o bloco: '{evento_texto}'")

            hashes_finais = [df.iloc[-1]["hash_atual"] for df in nos.values()]
            try:
                hash_anterior = max(set(hashes_finais), key=hashes_finais.count)
            except ValueError:
                # Se não houver blocos, usa o hash inicial (Gênesis)
                hash_anterior = "0" * 64

            try:
                proposta = sb.propor_bloco(propositor, evento_texto, hash_anterior)
                proposta = sb.votar_proposta(proposta, nos, chaves)
            except Exception as e:
                st.error(f"Erro na fase de Proposta/Votação: {e}")
                st.stop()
            
            # --- Exibição do Hash Proposto e Anterior (Aumentado para 16 caracteres) ---
            hash_proposto = proposta["hash_bloco"]
            st.info(f"""
                Hash Anterior (Base do Consenso): `{hash_anterior[:16]}...`  
                Hash do Bloco Proposto: `{hash_proposto[:16]}...`
            """)
            # --------------------------------------------------------------------------

            st.markdown("##### 1.1. Verificação de Integridade (Pré-Votação)")
            col_integrity = st.columns(len(nos))
            
            # Verifica se o hash do nó bate com o hash anterior da proposta para justificar a assinatura
            for i, (nome, df) in enumerate(nos.items()):
                hash_no = df.iloc[-1]['hash_atual'] if len(df) > 0 else "0" * 64
                compara_ok = (hash_no == hash_anterior)
                
                with col_integrity[i]:
                    if compara_ok:
                        st.success(f"Nó {nome}: ÍNTEGRO")
                        st.caption(f"Último Hash do Nó corresponde ao Hash Anterior: `{hash_no[:16]}...`")
                    else:
                        st.error(f"Nó {nome}: CORROMPIDO / FORA DE SINCRONIA")
                        st.caption(f"Esperado `{hash_anterior[:16]}...` | Achado `{hash_no[:16]}...`")

            st.markdown("---")
            
            st.markdown("##### Votação dos Nós (Assinaturas)")
            col_votes = st.columns(len(nos))
            votos_sim = 0
            for i, (no, assinatura) in enumerate(proposta["assinaturas"].items()):
                with col_votes[i]:
                    if assinatura.startswith("Recusado"):
                        st.error(f"Nó {no} recusou")
                    else:
                        st.success(f"Nó {no} assinou")
                        votos_sim += 1

            st.markdown("---")
            st.markdown("##### 2. Aplicação do Consenso")
            st.write(f"Votos válidos: **{votos_sim}**. Quorum necessário: **{quorum}**.")

            try:
                sucesso = sb.aplicar_consenso(proposta, nos, quorum=quorum)
            except Exception as e:
                st.error(f"Erro ao aplicar consenso: {e}")
                sucesso = False

            if sucesso:
                st.session_state["consenso_sucesso"] = True # Define sucesso
                
                # Novo Hash Display também aumentado para 16 caracteres
                novo_hash_display = proposta["hash_bloco"][:16]
                st.success(f"Consenso alcançado. O bloco foi adicionado em todos os nós. (Novo Hash: `{novo_hash_display}...`)")
                
                registrar_auditoria(
                    "Sistema",
                    "consenso_aprovado",
                    f"Bloco '{evento_texto}' aceito (quorum {quorum})"
                )
    # --------------------------------------------------------
    # 🔍 AUDITORIA DE HASHES (Antes e Depois do Consenso)
    # --------------------------------------------------------
    st.markdown("##### Auditoria de Hashes dos Nós (Antes ➜ Depois)")
    st.caption("Comparação dos hashes dos nós antes e depois da sincronização do novo bloco.")

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

    # 🔹 Cores para destaque visual
    def color_diff(val):
        return "color: #d9534f;" if val == "Sim" else "color: #5cb85c;"

    st.dataframe(
        df_comp.style.applymap(color_diff, subset=["Mudou?"]),
        use_container_width=True
    )

                st.session_state["web3_evento_texto"] = evento_texto
                st.session_state["web3_hash"] = proposta["hash_bloco"]
                st.session_state["mostrar_web3"] = False 

            else:
                st.warning("Quorum insuficiente. O bloco foi rejeitado e não foi adicionado.")
                registrar_auditoria(
                    "Sistema",
                    "consenso_rejeitado",
                    f"Bloco '{evento_texto}' rejeitado (quorum {quorum})"
                )
                st.session_state["mostrar_web3"] = False
                st.session_state["web3_evento_texto"] = None
                st.session_state["web3_hash"] = None
            
            st.rerun() # Força o rerun para exibir o status pós-consenso

    # --------------------------------------------------------
    # 2.1. STATUS PÓS-CONSENSO (Nós Sincronizados)
    # --------------------------------------------------------
    if st.session_state.get("consenso_sucesso", False):
        st.markdown("##### 2.1. Status Pós-Consenso (Nós Sincronizados)")
        st.caption("Confirmando que o novo bloco foi sincronizado. Os hashes atuais devem ser idênticos.")
        
        col_post_status = st.columns(len(nos))
        for i, (nome, df) in enumerate(nos.items()):
            # Pega o NOVO hash atual após a aplicação do consenso (Aumentado para 16 caracteres)
            hash_display = df.iloc[-1]['hash_atual'][:16] if len(df) > 0 else "VAZIO" 
            
            with col_post_status[i]:
                st.metric(
                    label=f"Nó {nome} (Novo Hash)",
                    value=f"{hash_display}...",
                )
        st.markdown("---")


    # --------------------------------------------------------
    # VISUALIZAÇÃO WEB3 — CONTROLADO POR BOTÃO (Não roda direto)
    # --------------------------------------------------------
    if st.session_state["web3_evento_texto"]:
        st.divider()
        st.subheader("3. Detalhes da Transação na Blockchain (Web3 Simulado)")
        st.caption("A transação (bloco) aceita é refletida no Explorer.")

        # O botão agora é um toggle que muda o estado e força o rerun
        if st.button("Mostrar / Ocultar Detalhes Web3", key="toggle_web3_main", use_container_width=True):
            st.session_state["mostrar_web3"] = not st.session_state["mostrar_web3"]
            st.rerun()

        if st.session_state.get("mostrar_web3"):
            with st.container(border=True):
                # A função mostrar_demo_web3 só é chamada aqui dentro
                mostrar_demo_web3(
                    st.session_state["web3_evento_texto"],
                    st.session_state["web3_hash"]
                )
        else:
            st.info("Clique no botão acima para visualizar os detalhes da transação simulada.")


    # --------------------------------------------------------
    # UTILITÁRIOS FIRESTORE E AUDITORIA
    # --------------------------------------------------------
    st.divider()
    st.subheader("Utilitários de Sincronização e Auditoria (Firestore)")

    col_sync, col_audit = st.columns(2)

    with col_sync:
        with st.container(border=True):
            st.markdown("##### Sincronização e Gestão de Dados (Firestore)")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Carregar da Nuvem", key="load_cloud", use_container_width=True):
                    df = carregar_blockchain_firestore()
                    if df is not None:
                        st.session_state.blockchain_df = df
                        nos["Node_A"] = df
                        st.success("Blockchain carregada e Node_A atualizado!")
                    else:
                        st.warning("Nenhum dado encontrado no Firestore.")

            with col2:
                if st.button("Salvar Manualmente", key="save_cloud", use_container_width=True):
                    try:
                        salvar_blockchain_firestore(nos["Node_A"])
                        st.success("Blockchain salva manualmente!")
                    except Exception as e:
                        st.error(f"Erro ao salvar blockchain: {e}")

            with col3:
                if st.button("Resetar Firestore e Sessão", key="reset_cloud", use_container_width=True):
                    try:
                        limpar_blockchain_firestore()
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        st.error("Blockchain removida e sessão reiniciada. Por favor, Recarregue a página (Rerun).")
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

            if st.button("Enviar Log de Auditoria", key="botao_teste_auditoria", use_container_width=True):
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
    Demonstração didática de corrupção proposital em um nó. 
    Permite observar como a integridade dos dados é quebrada e como o sistema detecta e recupera divergências.
    """)
    st.divider()

    # --------------------------------------------------------
    # Simular Ataque
    # --------------------------------------------------------
    with st.container(border=True):
        st.subheader("1. Simular Ataque e Quebra de Integridade")
        
        colA, colB = st.columns([1, 1])

        with colA:
            node_to_corrupt = st.selectbox("Escolha o nó para corromper:", list(nos.keys()), key="fraude_node")
            corrupt_type = st.radio("Tipo de corrupção:", ["Alterar último bloco (dados)", "Alterar hash final"])

        with colB:
            st.markdown(" ") # Espaçamento
            if st.button("CORROMPER NÓ (Simular ataque)", key="fraude_attack", type="secondary", use_container_width=True):
                df = nos[node_to_corrupt].copy()
                if len(df) > 0:
                    idx = len(df) - 1
                    original = df.iloc[idx].copy().to_dict()

                    if corrupt_type == "Alterar último bloco (dados)":
                        # Altera os dados e recalcula o hash para o novo conteúdo (incorreto)
                        df.at[idx, "etapa"] = str(df.at[idx, "etapa"]) + " (ALTERADO MALICIOSAMENTE)"
                        conteudo = f"{df.at[idx,'id_entrega']}-{df.at[idx,'source_center']}-{df.at[idx,'destination_name']}-{df.at[idx,'etapa']}-{df.at[idx,'timestamp']}-{df.at[idx,'risco']}"
                        df.at[idx, "hash_atual"] = gerar_hash(conteudo, df.at[idx, "hash_anterior"])
                    
                    else:
                        # Altera o hash final diretamente, quebrando o elo.
                        df.at[idx, "hash_atual"] = "FRAUDE" + str(uuid.uuid4()).replace('-', '')[:len(df.at[idx, "hash_atual"]) - 6]

                    nos[node_to_corrupt] = df
                    modificado = df.iloc[idx].copy().to_dict()
                    st.error(f"Nó {node_to_corrupt} corrompido (simulado).")
                    registrar_auditoria("Sistema", "no_corrompido", f"{node_to_corrupt} corrompido ({corrupt_type})")

                    st.markdown("##### Comparação do Bloco Corrompido:")
                    comparacao = pd.DataFrame([
                        {"Campo": "Etapa", "Antes": original["etapa"], "Depois": modificado["etapa"]},
                        # Aumentando a exibição do hash para 16 caracteres para melhor visualização na tabela
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
        st.subheader("2. Detecção e Recuperação de Consenso")

        colC, colD = st.columns(2)

        with colC:
            if st.button("Detectar divergência", key="fraude_detect", use_container_width=True):
                if validar_consenso(nos):
                    st.success("Todos os nós estão íntegros e sincronizados.")
                else:
                    corrompidos = detectar_no_corrompido(nos)
                    st.error("Divergência detectada entre os nós!")
                    st.warning(f"Nós corrompidos identificados: **{', '.join(corrompidos)}**")

        with colD:
            if st.button("Recuperar nós corrompidos", key="fraude_recover", type="primary", use_container_width=True):
                try:
                    ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items() if len(df) > 0}
                    
                    if not ultimos:
                        st.warning("Nenhum nó tem blocos para recuperar.")
                    else:
                        # Encontra o hash majoritário (o correto)
                        freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
                        hash_ok = max(freq, key=freq.get)
                        
                        nos = recuperar_no(nos, hash_ok)
                        st.success("Nós corrompidos restaurados com sucesso para o estado majoritário.")
                        registrar_auditoria("Sistema", "no_recuperado", "Nós restaurados com base no hash majoritário.")
                except Exception as e:
                    st.error(f"Erro ao restaurar nós: {e}")

    st.divider()

    if st.button("Mostrar Resumo Completo das Blockchains (por Nó)", key="fraude_summary"):
        for nome, df in nos.items():
            # Aumentando o display do hash na tabela resumo
            hash_final = df.iloc[-1]['hash_atual'][:16] if len(df) > 0 else "VAZIO" 
            st.markdown(f"**{nome}** — **{len(df)}** blocos — hash final `{hash_final}...`")
            st.dataframe(
                df[["bloco_id", "id_entrega", "source_center", "destination_name", "etapa", "hash_atual"]].tail(5),
                use_container_width=True
            )

# ============================================================
# FIM DO ARQUIVO
# ============================================================
