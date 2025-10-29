# ============================================================
# 💰 SmartLog Blockchain — Simulador de Consenso (Streamlit)
# ============================================================
# Interface visual que usa o módulo smartlog_blockchain.py
# para demonstrar consenso Proof-of-Authority na prática.
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
from smartlog_blockchain import (
    criar_blockchain_inicial, criar_nos, validar_consenso,
    simular_chaves_privadas, propor_bloco, votar_proposta,
    aplicar_consenso
)

# ============================================================
# 🎨 CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain Consensus", page_icon="⛓️", layout="wide")

st.title("⛓️ SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("""
Este simulador demonstra o funcionamento de um **consenso Proof-of-Authority** em uma rede blockchain logística.
Cada nó assina digitalmente um novo bloco proposto — e, se atingir o *quorum* (2 de 3), o bloco é aceito por todos.  
---
""")

# ============================================================
# 🧱 CRIAR BLOCKCHAIN BASE E NÓS
# ============================================================
if "nos" not in st.session_state:
    # Criar dataframe de eventos simulados
    dados = {
        "id_entrega": [1, 2, 3],
        "source_center": ["Depósito_SP", "Depósito_SP", "Depósito_RJ"],
        "destination_name": ["Centro_MG", "Centro_PR", "Centro_BA"],
        "etapa": ["Saiu do depósito", "Em rota", "Chegou ao destino"],
        "timestamp": [datetime.now()] * 3,
        "risco": ["Baixo", "Médio", "Baixo"]
    }
    eventos_df = pd.DataFrame(dados)

    # Criar blockchain inicial e nós
    blockchain_df = criar_blockchain_inicial(eventos_df)
    nos = criar_nos(blockchain_df)
    chaves = simular_chaves_privadas(nos)

    # Guardar em sessão
    st.session_state.blockchain_df = blockchain_df
    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state.historico = []

nos = st.session_state.nos
chaves = st.session_state.chaves

# ============================================================
# 📦 VISUALIZAÇÃO DOS NÓS
# ============================================================
st.subheader("📦 Estado Atual dos Nós")

col1, col2, col3 = st.columns(3)
for i, (nome, df) in enumerate(nos.items()):
    with [col1, col2, col3][i]:
        ultimo_hash = df.iloc[-1]["hash_atual"][:12]
        st.metric(label=f"{nome}", value=f"Hash final: {ultimo_hash}")

# ============================================================
# 🧠 PROPOR NOVO BLOCO
# ============================================================
st.markdown("---")
st.subheader("🧠 Propor Novo Bloco")

evento_texto = st.text_input("Descrição do novo evento:", "Entrega #104 — Saiu do depósito — SP → MG")
propositor = st.selectbox("Selecione o nó propositor:", list(nos.keys()))
quorum = st.slider("Defina o quorum mínimo:", 1, len(nos), 2)

if st.button("🚀 Propor e Validar"):
    hash_anterior = list(nos.values())[0].iloc[-1]["hash_atual"]
    proposta = propor_bloco(propositor, evento_texto, hash_anterior)
    proposta = votar_proposta(proposta, nos, chaves)

    sucesso = aplicar_consenso(proposta, nos, quorum=quorum)

    if sucesso:
        st.success("✅ Consenso alcançado! O bloco foi adicionado em todos os nós.")
        st.session_state.historico.append({
            "evento": evento_texto,
            "propositor": propositor,
            "assinaturas": len(proposta["assinaturas"]),
            "status": "Aceito"
        })
    else:
        st.error("❌ Quorum insuficiente. O bloco foi rejeitado.")
        st.session_state.historico.append({
            "evento": evento_texto,
            "propositor": propositor,
            "assinaturas": len(proposta["assinaturas"]),
            "status": "Rejeitado"
        })

# ============================================================
# 📜 HISTÓRICO DE CONSENSOS
# ============================================================
if st.session_state.historico:
    st.markdown("---")
    st.subheader("📜 Histórico de Propostas")
    historico_df = pd.DataFrame(st.session_state.historico)
    st.dataframe(historico_df, use_container_width=True)

# ============================================================
# 🔍 STATUS DE CONSENSO
# ============================================================
st.markdown("---")
st.subheader("🔍 Status de Consenso da Rede")

if validar_consenso(nos):
    st.success("🟢 Todos os nós estão sincronizados.")
else:
    st.warning("🟠 Divergência detectada entre os nós!")
