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
# Assumindo que estes módulos existam no ambiente de execução:
import smartlog_blockchain as sb
from audit_logger import registrar_auditoria
from web3_demo_simulado import mostrar_demo_web3 # RE-ADICIONADO

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
    gerar_hash # Importando explicitamente gerar_hash, se necessário
)

from firebase_utils import (
    salvar_blockchain_firestore,
    carregar_blockchain_firestore,
    limpar_blockchain_firestore
)

# ============================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================
# Configuração de página (removido o page_icon)
st.set_page_config(page_title="SmartLog Blockchain", layout="wide")

st.title("SmartLog Blockchain — Simulador de Consenso (PoA)")

# A nova frase entra aqui, antes do markdown existente
st.markdown("""
*Imagine uma Blockchain não como uma rede pública (como o Bitcoin), mas sim como um cartório digital ultra-seguro gerenciado por Membros da Rede Autorizados.*
""")

# Explicação técnica
st.markdown("""
O **SmartLog Blockchain** demonstra o funcionamento de um consenso *Proof-of-Authority* em redes logísticas. Cada nó valida e assina digitalmente os blocos propostos. 
Se o número de assinaturas atinge o *quorum mínimo*, o bloco é aceito por toda a rede. 
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

nos = st.session_state.nos
chaves = st.session_state.chaves
# Compatibilidade: renomeia nós antigos (Node_ -> Nó_)
nos = {nome.replace("Node_", "Nó_"): df for nome, df in nos.items()}


# ============================================================
# INTERFACE DIVIDIDA EM ABAS
# ============================================================
# Removidos emojis dos títulos das abas
tab_main, tab_fraude = st.tabs(["Simulador de Consenso", "Simulador de Fraude / Ataque"])

# ============================================================
# ABA 1 — SIMULADOR DE CONSENSO (PRINCIPAL)
# ============================================================
with tab_main:
    st.header("Simulação de Consenso Proof-of-Authority")
    st.divider()

    # --- Container para Status de Rede (Visual Profissional) ---
    st.subheader("Status Atual da Rede")
    
    # Verifica se há divergências (removidos emojis da mensagem de sucesso/alerta)
    if validar_consenso(nos):
        st.success("Todos os nós estão sincronizados e íntegros. Blockchain com "
                   f"**{len(next(iter(nos.values())))}** blocos.")
    else:
        st.warning("Divergência detectada entre os nós! Verifique a seção 'Status da Rede'.")

    # Estado atual dos nós (Melhorado visualmente com container)
    with st.container(border=True):
        st.markdown("##### Hashes Finais dos Nós (Sincronização)")
        cols = st.columns(len(nos))
        for i, (nome, df) in enumerate(nos.items()):
            with cols[i]:
                # Usando metric para destaque
                st.metric(
                    label=f"{nome}", 
                    value=f"{df.iloc[-1]['hash_atual'][:12]}...",
                    delta=f"Blocos: {len(df)}"
                )
    
    st.divider()

    # --- Propor novo bloco (Agrupado em Expander) ---
    with st.expander("Propor Novo Bloco e Iniciar Votação", expanded=True):
        
        col_prop, col_quorum = st.columns([2, 1])

        with col_prop:
            # Removido emoji do label
            propositor = st.selectbox(
                "Selecione o nó propositor:",
                list(nos.keys()),
                key="select_propositor_main"
            )

        with col_quorum:
            # Removido emoji do label
            quorum = st.slider(
                "Defina o quorum mínimo:",
                1, len(nos), 2,
                key="slider_quorum_main"
            )

        evento_texto = st.text_input(
            "📝 Descrição do novo evento (dados do bloco):",
            "Entrega #104 — Saiu do depósito — SP → MG",
            key="input_evento_main"
        )

    # ===============================================
    # Iniciar Simulação de Consenso (Execução)
    # ===============================================
    # Removido emoji do botão
    if st.button("Iniciar Simulação de Consenso", key="botao_consenso_main", use_container_width=True):
        
        st.info(f"**Proposta:** {propositor} está propondo o bloco: **'{evento_texto}'**")
        
        # Usa o último hash da maioria para garantir integridade
        hashes_finais = [df.iloc[-1]["hash_atual"] for df in nos.values()]
        hash_anterior = max(set(hashes_finais), key=hashes_finais.count)

        # Etapa 1: Proposta e votação
        try:
            proposta = sb.propor_bloco(propositor, evento_texto, hash_anterior)
            proposta = sb.votar_proposta(proposta, nos, chaves)
        except Exception as e:
            st.error(f"Erro na fase de Proposta/Votação: {e}")
            st.stop()


        # Etapa 2: Mostrar assinaturas
        st.markdown("### Votação dos Nós (Assinaturas)")
        
        col_votes = st.columns(len(nos))
        for i, (no, assinatura) in enumerate(proposta["assinaturas"].items()):
            with col_votes[i]:
                # Removidos emojis de sucesso/erro
                if assinatura.startswith("Recusado"):
                    st.error(f"{no} recusou")
                else:
                    st.success(f"{no} assinou")
        
        st.divider()

        # ===============================================
        # Cálculo do Consenso e Aplicação
        # ===============================================
        st.markdown("### Aplicação do Consenso")
        st.write(f"Quorum necessário: **{quorum}** de {len(nos)} nós.")

        try:
            sucesso = sb.aplicar_consenso(proposta, nos, quorum=quorum)
        except Exception as e:
            st.error(f"Erro ao aplicar consenso: {e}")
            sucesso = False

        if sucesso:
            # Removido emoji da mensagem de sucesso
            st.success("Consenso alcançado! O bloco foi adicionado em todos os nós.")
            registrar_auditoria(
                "Sistema",
                "consenso_aprovado",
                f"Bloco '{evento_texto}' aceito (quorum {quorum})"
            )

            # RE-ADICIONADO: Visualização Web3 (Simulada)
            with st.expander("Visualização Web3 (Simulada)", expanded=False):
                mostrar_demo_web3(evento_texto, proposta["hash_bloco"])

        else:
            # Removido emoji da mensagem de alerta
            st.warning("Quorum insuficiente. O bloco foi rejeitado e não foi adicionado.")
            registrar_auditoria(
                "Sistema",
                "consenso_rejeitado",
                f"Bloco '{evento_texto}' rejeitado (quorum {quorum})"
            )


    st.divider()

    # --- Visualização do Ledger (Melhoria de UI) ---
    # Removido emoji do expander
    with st.expander("Visualizar Ledger (Node A)", expanded=False):
        st.dataframe(nos["Node_A"], use_container_width=True)

    # ============================================================
    # FIRESTORE E AUDITORIA — UTilitários
    # ============================================================
    # Removido emoji do subheader
    st.subheader("Utilitários de Sincronização e Auditoria (Firestore)")
    
    with st.container(border=True):
        
        # NOVOS CAMPOS PARA TESTE DE AUDITORIA MANUAL
        st.markdown("##### Envio Manual de Log de Auditoria")
        col_audit_actor, col_audit_message = st.columns([1, 3])
        
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
        
        st.markdown("---") # Separador para os botões

        col1, col2, col3, col4 = st.columns([1.5, 1.5, 2, 2])

        # --- Botão: Carregar blockchain da nuvem ---
        with col1:
            # Removido emoji do botão
            if st.button("Carregar da Nuvem", use_container_width=True):
                df = carregar_blockchain_firestore()
                if df is not None:
                    st.session_state.blockchain_df = df # Atualiza o estado da sessão (melhor prática)
                    nos["Node_A"] = df # Apenas atualiza um nó para demonstração
                    # Removido emoji
                    st.success("Blockchain carregada e Node_A atualizado da nuvem!")
                else:
                    # Removido emoji
                    st.warning("Nenhum dado encontrado no Firestore.")

        # --- Botão: Salvar blockchain manualmente ---
        with col2:
            # Removido emoji do botão
            if st.button("Salvar Manualmente", use_container_width=True):
                try:
                    salvar_blockchain_firestore(nos["Node_A"])
                    # Removido emoji
                    st.success("Blockchain salva manualmente no Firestore!")
                except Exception as e:
                    # Removido emoji
                    st.error(f"Erro ao salvar blockchain: {e}")

        # --- Botão: Resetar Firestore e limpar sessão ---
        with col3:
            # Removido emoji do botão
            if st.button("Resetar Firestore e Sessão", use_container_width=True):
                try:
                    limpar_blockchain_firestore()
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    # Removido emoji
                    st.warning("Blockchain removida do Firestore e sessão reiniciada. Clique em 'Rerun'.")
                    st.stop()
                except Exception as e:
                    # Removido emoji
                    st.error(f"Erro ao limpar Firestore: {e}")
        
        # --- Botão: Teste de Auditoria Manual (AGORA DINÂMICO) ---
        with col4:
            # Removido emoji do botão
            if st.button("Enviar Log de Auditoria", key="botao_teste_auditoria", use_container_width=True):
                try:
                    # Usa os valores dinâmicos de Ator e Mensagem
                    registrar_auditoria(audit_actor, "teste_envio_manual", audit_message)
                    # Removido emoji
                    st.success(f"Log de auditoria enviado: **{audit_actor}** registrou: '{audit_message}'")
                except Exception as e:
                    # Removido emoji
                    st.error(f"Erro ao registrar auditoria: {e}")

# ============================================================
# ABA 2 — SIMULADOR DE FRAUDE / NÓ MALICIOSO
# ============================================================
with tab_fraude:
    # Removido emoji do header
    st.header("Simulador de Fraude / Nó Malicioso")
    st.markdown("""
    Demonstração **didática** de corrupção proposital em um nó. Permite observar como a integridade dos dados é quebrada e como o sistema detecta e recupera divergências.
    """)
    st.divider()

    # --- Ações de Fraude ---
    with st.container(border=True):
        # Removido emoji do subheader
        st.subheader("Simular Ataque e Quebra de Integridade")
        colA, colB = st.columns([1, 1])

        with colA:
            # Removido emoji do label
            node_to_corrupt = st.selectbox("Escolha o nó para corromper:", list(nos.keys()), key="fraude_node")
            # Removido emoji do label
            corrupt_type = st.radio("Tipo de corrupção:", ["Alterar último bloco (dados)", "Alterar hash final"])
        
        with colB:
            st.markdown(" ") # Espaço para alinhamento
            # Removido emoji do botão
            if st.button("Corromper nó (simular ataque)", key="fraude_attack", use_container_width=True):
                df = nos[node_to_corrupt].copy()
                if len(df) > 0:
                    idx = len(df) - 1
                    original = df.iloc[idx].to_dict()

                    # --- Aplica corrupção ---
                    if corrupt_type == "Alterar último bloco (dados)":
                        df.at[idx, "etapa"] = str(df.at[idx, "etapa"]) + " (ALTERADO MALICIOSAMENTE)"
                        conteudo = f"{df.at[idx,'id_entrega']}-{df.at[idx,'source_center']}-{df.at[idx,'destination_name']}-{df.at[idx,'etapa']}-{df.at[idx,'timestamp']}-{df.at[idx,'risco']}"
                        df.at[idx, "hash_atual"] = sb.gerar_hash(conteudo, df.at[idx, "hash_anterior"])
                    else:
                        # Corrompendo o hash com um valor totalmente novo
                        df.at[idx, "hash_atual"] = sb.gerar_hash("ATAQUE_MALICIOSO", df.at[idx, "hash_anterior"])

                    # Atualiza nó
                    nos[node_to_corrupt] = df
                    modificado = df.iloc[idx].to_dict()

                    # --- Mostra comparação didática ---
                    # Removido emoji
                    st.error(f"{node_to_corrupt} corrompido (simulado).")
                    registrar_auditoria("Sistema", "no_corrompido", f"{node_to_corrupt} corrompido ({corrupt_type})")

                    comparacao = pd.DataFrame([
                        {"Campo": "Etapa", "Antes": original["etapa"], "Depois": modificado["etapa"]},
                        {"Campo": "Hash Atual", "Antes": original["hash_atual"][:16] + "...", "Depois": modificado["hash_atual"][:16] + "..."},
                        {"Campo": "Hash Anterior", "Antes": original["hash_anterior"][:16] + "...", "Depois": modificado["hash_anterior"][:16] + "..."},
                    ])
                    st.dataframe(comparacao, use_container_width=True)

                else:
                    # Removido emoji
                    st.warning("Este nó não contém blocos para corromper.")

    st.divider()

    # --- Detecção e Recuperação ---
    with st.container(border=True):
        # Removido emoji do subheader
        st.subheader("Detecção e Recuperação de Consenso")
        
        colC, colD = st.columns(2)
        
        # Detectar divergências
        with colC:
            # Removido emoji do botão
            if st.button("Detectar divergência", key="fraude_detect", use_container_width=True):
                if validar_consenso(nos):
                    # Removido emoji
                    st.success("Todos os nós estão íntegros e sincronizados.")
                else:
                    # Removido emoji
                    st.error("Divergência detectada entre os nós!")
                    corrompidos = detectar_no_corrompido(nos)
                    # Removido emoji
                    st.warning(f"Nós corrompidos identificados: **{', '.join(corrompidos)}**")
                    
                    ultimos = {n: df.iloc[-1]["hash_atual"][:16] for n, df in nos.items()}
                    st.markdown("##### Hashes Finais (para comparação):")
                    st.dataframe(pd.DataFrame(list(ultimos.items()), columns=["Nó", "Hash final"]), use_container_width=True)

        # Recuperação
        with colD:
            # Removido emoji do botão
            if st.button("Recuperar nós corrompidos (copiar da maioria)", key="fraude_recover", use_container_width=True):
                try:
                    ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
                    # Encontra o hash majoritário
                    freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
                    hash_ok = max(freq, key=freq.get)
                    
                    # Recupera o estado de todos os nós baseados no nó com o hash_ok
                    nos = recuperar_no(nos, hash_ok)
                    # Removido emoji
                    st.success("Nós corrompidos restaurados com sucesso usando a blockchain da maioria.")
                    registrar_auditoria("Sistema", "no_recuperado", "Nós restaurados com base no hash majoritário.")
                except Exception as e:
                    # Removido emoji
                    st.error(f"Erro ao restaurar nós: {e}")
                    
        
        st.divider()

        # Resumo
        # Removido emoji do botão
        if st.button("Mostrar resumo das blockchains (por nó)", key="fraude_summary"):
            for nome, df in nos.items():
                st.markdown(f"**{nome}** — {len(df)} blocos — hash final `{df.iloc[-1]['hash_atual'][:16]}...`")
                st.dataframe(
                    df[["bloco_id", "id_entrega", "source_center", "destination_name", "etapa", "hash_atual"]].tail(2),
                    use_container_width=True
                )

# ============================================================
# FIM DO ARQUIVO
# ============================================================



