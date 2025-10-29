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
# 🧠 PROPOR NOVO BLOCO — VERSÃO DIDÁTICA
# ============================================================
st.markdown("---")
st.subheader("🧠 Propor Novo Bloco (Explicativo)")

evento_texto = st.text_input("📝 Descrição do novo evento:", "Entrega #104 — Saiu do depósito — SP → MG")
propositor = st.selectbox("👤 Selecione o nó propositor:", list(nos.keys()))
quorum = st.slider("📊 Defina o quorum mínimo:", 1, len(nos), 2)

if st.button("🚀 Iniciar Simulação de Consenso"):
    st.markdown("### 🧱 Etapa 1: Criação da Proposta")
    st.info(f"📦 {propositor} está propondo o bloco: **'{evento_texto}'**")

    hash_anterior = list(nos.values())[0].iloc[-1]["hash_atual"]
    st.write(f"🔗 Hash anterior: `{hash_anterior[:16]}...`")

    proposta = propor_bloco(propositor, evento_texto, hash_anterior)

    st.markdown("### 🔍 Etapa 2: Votação dos Nós")
    st.write("Cada nó agora vai recalcular o hash do bloco e decidir se aceita ou recusa a proposta...")

    # Executa a votação simulada
    proposta = votar_proposta(proposta, nos, chaves)

    st.markdown("#### 📊 Resultado das Assinaturas")
    assinaturas = []
    for no, assinatura in proposta["assinaturas"].items():
        if assinatura.startswith("Recusado"):
            st.error(f"❌ {no} recusou o bloco (hash divergente ou rejeição simulada).")
            assinaturas.append({"Nó": no, "Assinatura": "❌ Rejeitado"})
        else:
            st.success(f"✅ {no} validou e assinou o bloco.")
            assinaturas.append({"Nó": no, "Assinatura": assinatura[:20] + "..."})

    st.dataframe(pd.DataFrame(assinaturas), use_container_width=True)

    st.markdown("### 🧮 Etapa 3: Cálculo do Consenso (Quorum)")
    st.write(f"É necessário **{quorum}** de {len(nos)} nós para aprovar o bloco.")

    sucesso = aplicar_consenso(proposta, nos, quorum=quorum)

    if sucesso:
        st.balloons()
        st.success("✅ Consenso alcançado! O bloco foi adicionado em todos os nós.")
        st.session_state.historico.append({
            "evento": evento_texto,
            "propositor": propositor,
            "assinaturas": len([a for a in proposta['assinaturas'].values() if not a.startswith('Recusado')]),
            "status": "Aceito"
        })
    else:
        st.warning("⚠️ Quorum insuficiente. O bloco foi rejeitado.")
        st.session_state.historico.append({
            "evento": evento_texto,
            "propositor": propositor,
            "assinaturas": len([a for a in proposta['assinaturas'].values() if not a.startswith('Recusado')]),
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

# ============================================================
# 🧩 DEMONSTRAÇÃO DE IMUTABILIDADE (Hash Validation)
# ============================================================
st.markdown("---")
st.subheader("🧩 Demonstração de Validação de Hash entre Nós")
st.markdown("""
Nesta seção, cada nó recalcula o hash do mesmo bloco.
Se todos gerarem o mesmo hash → o bloco é íntegro ✅  
Se um nó tiver um dado diferente → divergência é detectada ❌
---
""")

import hashlib

def gerar_hash(conteudo, hash_anterior):
    return hashlib.sha256((conteudo + hash_anterior).encode()).hexdigest()

evento = st.text_input("📦 Evento proposto:", "Entrega #200 — Saiu do depósito")
hash_anterior = st.text_input("🔗 Hash anterior:", "abc123")
erro_nodeC = st.checkbox("⚠️ Simular erro no Node_C (dados alterados)")

# Simula 3 nós
nodos = {
    "Node_A": evento,
    "Node_B": evento,
    "Node_C": evento.replace("depósito", "deposito") if erro_nodeC else evento
}

# Calcula hash de cada nó
resultados = []
for nome, conteudo in nodos.items():
    hash_calc = gerar_hash(conteudo, hash_anterior)
    resultados.append({
        "Nó": nome,
        "Conteúdo": conteudo,
        "Hash gerado": hash_calc[:16] + "...",
        "Status": "🟢 Igual" if conteudo == evento else "🔴 Diferente"
    })

df = pd.DataFrame(resultados)
st.dataframe(df, use_container_width=True)

# Validação de consenso
hashes_unicos = {gerar_hash(c, hash_anterior) for c in nodos.values()}
if len(hashes_unicos) == 1:
    st.success("✅ Todos os nós calcularam o mesmo hash. O bloco é válido e foi aceito!")
else:
    st.error("⚠️ Hashes divergentes detectados! O bloco foi rejeitado pelo consenso.")

