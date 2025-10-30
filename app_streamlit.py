# ============================================================
# 💰 SmartLog Blockchain — Simulador de Consenso e Fraude
# ============================================================
# Interface visual que demonstra consenso Proof-of-Authority
# com simulação de corrupção e recuperação de nós.
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
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
    recuperar_no
)

from firebase_utils import (
    salvar_blockchain_firestore,
    carregar_blockchain_firestore,
    limpar_blockchain_firestore
)

# ============================================================
# 🎨 CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain", page_icon="⛓️", layout="wide")

st.title("⛓️ SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("""
O **SmartLog Blockchain** demonstra o funcionamento de um consenso *Proof-of-Authority* 
em redes logísticas. Cada nó valida e assina digitalmente os blocos propostos.  
Se o número de assinaturas atinge o *quorum mínimo*, o bloco é aceito por toda a rede.  
---
""")

# ============================================================
# 🧱 ESTADO INICIAL — Blockchain e Nós
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

# ============================================================
# 🧭 INTERFACE DIVIDIDA EM ABAS
# ============================================================
tab_main, tab_fraude = st.tabs(["🔗 Simulador de Consenso", "🚨 Simulador de Fraude / Ataque"])

# ============================================================
# 🔗 ABA 1 — SIMULADOR DE CONSENSO (PRINCIPAL)
# ============================================================
with tab_main:
    st.header("🔗 Simulação de Consenso Proof-of-Authority")

    # Estado atual dos nós
    st.subheader("📦 Estado Atual dos Nós")
    col1, col2, col3 = st.columns(3)
    for i, (nome, df) in enumerate(nos.items()):
        with [col1, col2, col3][i]:
            st.metric(label=f"{nome}", value=f"Hash final: {df.iloc[-1]['hash_atual'][:12]}")

    # Propor novo bloco
    st.markdown("---")
    st.subheader("🧠 Propor Novo Bloco")
    evento_texto = st.text_input("📝 Descrição do novo evento:", "Entrega #104 — Saiu do depósito — SP → MG")
    propositor = st.selectbox("👤 Selecione o nó propositor:", list(nos.keys()))
    quorum = st.slider("📊 Defina o quorum mínimo:", 1, len(nos), 2)

    if st.button("🚀 Iniciar Simulação de Consenso"):
        st.markdown("### 🧱 Etapa 1: Criação da Proposta")
        st.info(f"📦 {propositor} está propondo o bloco: **'{evento_texto}'**")

        hash_anterior = list(nos.values())[0].iloc[-1]["hash_atual"]
        proposta = propor_bloco(propositor, evento_texto, hash_anterior)

        st.markdown("### 🔍 Etapa 2: Votação dos Nós")
        proposta = votar_proposta(proposta, nos, chaves)

        st.markdown("#### 📊 Resultado das Assinaturas")
        assinaturas = []
        for no, assinatura in proposta["assinaturas"].items():
            if assinatura.startswith("Recusado"):
                st.error(f"❌ {no} recusou o bloco.")
                assinaturas.append({"Nó": no, "Assinatura": "❌ Rejeitado"})
            else:
                st.success(f"✅ {no} validou e assinou o bloco.")
                assinaturas.append({"Nó": no, "Assinatura": assinatura[:20] + "..."})
        st.dataframe(pd.DataFrame(assinaturas), use_container_width=True)

        st.markdown("### 🧮 Etapa 3: Cálculo do Consenso")
        st.write(f"É necessário **{quorum}** de {len(nos)} nós para aprovar o bloco.")

        sucesso = aplicar_consenso(proposta, nos, quorum=quorum)

        if sucesso:
            st.success("✅ Consenso alcançado! O bloco foi adicionado em todos os nós.")
            st.session_state.historico.append({
                "evento": evento_texto,
                "propositor": propositor,
                "assinaturas": len(proposta["assinaturas"]),
                "status": "Aceito"
            })
            try:
                blockchain_atual = nos["Node_A"]
                salvar_blockchain_firestore(blockchain_atual)
                st.info("☁️ Blockchain sincronizada com o Firestore!")
            except Exception as e:
                st.error(f"Erro ao salvar no Firestore: {e}")
        else:
            st.warning("⚠️ Quorum insuficiente. O bloco foi rejeitado.")
            st.session_state.historico.append({
                "evento": evento_texto,
                "propositor": propositor,
                "assinaturas": len(proposta["assinaturas"]),
                "status": "Rejeitado"
            })

    # Histórico de consenso
    if st.session_state.historico:
        st.markdown("---")
        st.subheader("📜 Histórico de Propostas")
        st.dataframe(pd.DataFrame(st.session_state.historico), use_container_width=True)

    # Firestore manual
    st.markdown("---")
    st.subheader("☁️ Firestore — Sincronização Manual")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📥 Carregar da Nuvem"):
            df = carregar_blockchain_firestore()
            if df is not None:
                st.dataframe(df)
                st.success("✅ Blockchain carregada!")
            else:
                st.warning("⚠️ Nenhum dado encontrado.")
    with col2:
        if st.button("💾 Salvar Manualmente"):
            salvar_blockchain_firestore(nos["Node_A"])
    with col3:
        if st.button("🧹 Resetar Firestore"):
            limpar_blockchain_firestore()

    # Status de consenso
    st.markdown("---")
    st.subheader("🔍 Status da Rede")
    if validar_consenso(nos):
        st.success("🟢 Todos os nós estão sincronizados.")
    else:
        st.warning("🟠 Divergência detectada entre os nós!")

    # Demonstração hash
    st.markdown("---")
    st.subheader("🧩 Demonstração de Validação de Hash")
    evento = st.text_input("📦 Evento proposto:", "Entrega #200 — Saiu do depósito")
    hash_ant = st.text_input("🔗 Hash anterior:", "abc123")
    erro_nodeC = st.checkbox("⚠️ Simular erro no Node_C (dados alterados)")

    nodos = {
        "Node_A": evento,
        "Node_B": evento,
        "Node_C": evento.replace("depósito", "deposito") if erro_nodeC else evento
    }

    resultados = []
    for nome, conteudo in nodos.items():
        hash_calc = hashlib.sha256((conteudo + hash_ant).encode()).hexdigest()
        resultados.append({
            "Nó": nome,
            "Conteúdo": conteudo,
            "Hash gerado": hash_calc[:16] + "...",
            "Status": "🟢 Igual" if conteudo == evento else "🔴 Diferente"
        })
    st.dataframe(pd.DataFrame(resultados), use_container_width=True)

# ============================================================
# 🚨 ABA 2 — SIMULADOR DE FRAUDE / ATAQUE
# ============================================================
with tab_fraude:
    st.header("🚨 Simulador de Fraude / Nó Malicioso")
    st.markdown(
        "Demonstração didática de corrupção proposital de um nó. "
        "Permite ver como o consenso detecta e recupera discrepâncias."
    )

    colA, colB, colC = st.columns(3)
    with colA:
        node_to_corrupt = st.selectbox("Escolha o nó:", list(nos.keys()), key="fraude_node")
        corrupt_type = st.radio("Tipo de corrupção:", ["Alterar último bloco (dados)", "Alterar hash final"])

    with colB:
        if st.button("💥 Corromper nó (simular ataque)", key="fraude_attack"):
            df = nos[node_to_corrupt].copy()
            if len(df) > 0:
                idx = len(df) - 1
                if corrupt_type == "Alterar último bloco (dados)":
                    df.at[idx, "etapa"] += " (ALTERADO MALICIOSAMENTE)"
                    conteudo = f"{df.at[idx,'id_entrega']}-{df.at[idx,'source_center']}-{df.at[idx,'destination_name']}-{df.at[idx,'etapa']}-{df.at[idx,'timestamp']}-{df.at[idx,'risco']}"
                    df.at[idx, "hash_atual"] = sb.gerar_hash(conteudo, df.at[idx, "hash_anterior"])
                else:
                    df.at[idx, "hash_atual"] = sb.gerar_hash("ataque", df.at[idx, "hash_anterior"])
                nos[node_to_corrupt] = df
                st.error(f"⚠️ {node_to_corrupt} corrompido (simulado).")
                st.dataframe(df.tail(1))
            else:
                st.warning("Nó vazio — nada a corromper.")

    with colC:
        if st.button("🔍 Detectar divergência", key="fraude_detect"):
            if validar_consenso(nos):
                st.success("🟢 Nenhuma divergência detectada.")
            else:
                st.warning("🟠 Divergência encontrada!")
                corrompidos = detectar_no_corrompido(nos)
                st.write("Nós corrompidos:", corrompidos)
                hashes = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
                st.dataframe(pd.DataFrame(hashes.items(), columns=["Nó", "Hash atual"]))

    st.markdown("---")
    if st.button("🔁 Recuperar nós corrompidos (restaurar da maioria)", key="fraude_recover"):
        try:
            ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
            freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
            hash_ok = max(freq, key=freq.get)
            nos = recuperar_no(nos, hash_ok)
            st.success("✅ Nós restaurados com sucesso.")
        except Exception as e:
            st.error(f"Erro ao restaurar: {e}")

    if st.button("📊 Mostrar resumo das blockchains", key="fraude_summary"):
        for nome, df in nos.items():
            st.markdown(f"**{nome}** — {len(df)} blocos — hash final `{df.iloc[-1]['hash_atual'][:16]}...`")
            st.dataframe(df.tail(2))


