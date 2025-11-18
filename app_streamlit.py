# ============================================================
# SmartLog Blockchain — Simulador de Consenso e Fraude (IA-Labs Edition)
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import uuid
import requests

# ============================================================
# 🎨 ESTILO IA-LABS (Clean / Profissional / Azul Corporativo)
# ============================================================
st.markdown("""
<style>

/* ======================== */
/*   ESTRUTURA GERAL        */
/* ======================== */
body {
    background-color: #f5f7fa;
    font-family: 'Poppins', sans-serif;
    color: #1a1a1a;
}

[data-testid="stSidebarNav"] { display: none !important; }
header { visibility: hidden; }

/* Remove bordas padrão */
.css-18e3th9, .css-1d391kg { padding: 0 !important; }

/* ======================== */
/*   TÍTULOS                */
/* ======================== */
h1, h2, h3, h4 {
    font-weight: 600;
    color: #2D8CFF !important;
    letter-spacing: -0.5px;
}

/* ======================== */
/*   CARDS                  */
/* ======================== */
.card {
    background-color: #ffffff;
    border-radius: 18px;
    padding: 25px;
    margin: 20px 0;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.06);
    border: 1px solid #e6eaf0;
}

.card-title {
    font-size: 1.3rem;
    font-weight: 600;
    color: #2D8CFF;
    margin-bottom: 12px;
}

/* ======================== */
/*   BOTÕES                 */
/* ======================== */
div.stButton > button {
    background-color: #2D8CFF;
    color: white;
    border-radius: 12px;
    padding: 10px 18px;
    border: none;
    font-weight: 600;
    transition: .3s ease;
}

div.stButton > button:hover {
    background-color: #1b6fd8;
    transform: scale(1.02);
}

/* Botão de perigo */
button[kind="secondary"]:hover {
    background-color: #ff3b3b !important;
    color: white !important;
}

/* ======================== */
/*   VISUALIZAÇÃO DE BLOCOS */
/* ======================== */
.blockchain-linha {
    display: flex;
    flex-direction: row;
    gap: 12px;
    margin-top: 15px;
    margin-bottom: 20px;
    justify-content: center;
}

.bloco-ok {
    background-color: #e8f1ff;
    border: 2px solid #2D8CFF;
    color: #2D8CFF;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
}

.bloco-novo {
    background-color: #e7fff1;
    border: 2px solid #06D6A0;
    color: #06D6A0;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
}

.bloco-corrupcao {
    background-color: #ffe7e7;
    border: 2px solid #ff3b3b;
    color: #ff3b3b;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# VISUALIZAÇÃO GRÁFICA DOS BLOCOS (FUNÇÃO NOVA)
# ============================================================
def mostrar_blockchain_visual(nome_no, df_no):
    st.markdown(f"### 📦 Blockchain do Nó **{nome_no}**")

    if len(df_no) == 0:
        st.info("Nenhum bloco registrado ainda.")
        return

    html = "<div class='blockchain-linha'>"
    
    for i, row in df_no.iterrows():
        etapa = str(row.get("etapa", ""))
        hash_atual = row["hash_atual"][:6]

        if "ALTERADO" in etapa or "🚨" in etapa:
            classe = "bloco-corrupcao"
            label = f"CORR<br>{hash_atual}"
        elif i == len(df_no) - 1:
            classe = "bloco-novo"
            label = f"NOVO<br>{hash_atual}"
        else:
            classe = "bloco-ok"
            label = f"OK<br>{hash_atual}"

        html += f"<div class='{classe}'>{label}</div>"

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ------------------------------------------------------------
# Importações internas (com fallback)
# ------------------------------------------------------------
try:
    import smartlog_blockchain as sb
    from audit_logger import registrar_auditoria
    from web3_demo_simulado import mostrar_demo_web3
    from firebase_utils import salvar_blockchain_firestore, carregar_blockchain_firestore, limpar_blockchain_firestore
    from smartlog_blockchain import (
        criar_blockchain_inicial, criar_nos, validar_consenso, simular_chaves_privadas,
        propor_bloco, votar_proposta, aplicar_consenso, detectar_no_corrompido,
        recuperar_no, gerar_hash
    )
except ImportError:
    st.warning("⚠️ Módulos internos não encontrados. Executando em modo de fallback.")
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
    def mostrar_demo_web3(event, h): st.info("Módulo Web3 Simulado")


# ============================================================
# CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain", layout="wide")
st.title("SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("Simulador visual para redes blockchain privadas com auditoria e prevenção de fraudes.")

# ============================================================
# MODO DE OPERAÇÃO
# ============================================================
st.sidebar.header("Configurações da Simulação")
modo_operacao = st.sidebar.radio("Modo:", ["Simulado (local)", "Distribuído (rede)"], index=0)
st.markdown(f"### Modo atual: **{modo_operacao}**")

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

    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state.consenso_sucesso = False

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

    st.header("Fluxo de Consenso (PoA) — Visualização em Tempo Real")

    # -------------------------------
    # 🔵 Visualização gráfica dos nós
    # -------------------------------
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>Visualização Gráfica da Blockchain</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    for idx, (nome, df) in enumerate(nos.items()):
        with [col1, col2, col3][idx % 3]:
            mostrar_blockchain_visual(nome, df)

    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # -------------------------------
    # SIMULAÇÃO DE CONSENSO
    # -------------------------------
    st.subheader("Proposta e Votação de Novo Bloco")

    propositor = st.selectbox("Nó propositor:", list(nos.keys()))
    quorum = st.slider("Quorum mínimo:", 1, len(nos), 2)

    st.subheader("Cadastro de Lote de Eventos")
    num_eventos = st.number_input("Quantidade:", min_value=1, max_value=10, value=2)

    lote_eventos = []
    for i in range(num_eventos):
        with st.expander(f"Evento {i+1}"):
            lote_eventos.append({
                "id_entrega": st.text_input(f"ID {i+1}", f"{100+i}"),
                "origem": st.text_input(f"Origem {i+1}", "Depósito_SP"),
                "destino": st.text_input(f"Destino {i+1}", "Centro_MG"),
                "etapa": st.selectbox(f"Etapa {i+1}", ["Saiu do depósito", "Em rota", "Chegou ao destino"]),
                "risco": st.selectbox(f"Risco {i+1}", ["Baixo", "Médio", "Alto"]),
                "timestamp": datetime.now().isoformat()
            })

    if st.button("🚀 Iniciar Consenso", use_container_width=True):
        try:
            hash_anterior = nos[propositor].iloc[-1]["hash_atual"]
            proposta = sb.propor_bloco(propositor, lote_eventos, hash_anterior)
            proposta = sb.votar_proposta(proposta, nos, chaves)
            sucesso, tx_id = sb.aplicar_consenso(proposta, nos, quorum)

            if sucesso:
                st.success("✔ Consenso alcançado! Bloco aprovado.")
                st.session_state.consenso_sucesso = True
                st.session_state.ultimo_hash = proposta["hash_bloco"]
                st.session_state.ultimo_lote = lote_eventos
            else:
                st.warning("⚠️ Quorum insuficiente.")
        except Exception as e:
            st.error(f"Erro: {e}")


    # -------------------------------
    # AUDITORIA DE HASHES
    # -------------------------------
    if st.session_state.consenso_sucesso:
        st.divider()
        st.subheader("Auditoria de Hashes")

        comparacao = []
        for nome, df in nos.items():
            if len(df) >= 2:
                h1 = df.iloc[-2]["hash_atual"]
                h2 = df.iloc[-1]["hash_atual"]
                comparacao.append({
                    "Nó": nome,
                    "Hash Antigo": h1[:10],
                    "Hash Novo": h2[:10],
                    "Mudou?": "Sim" if h1 != h2 else "Não"
                })

        st.dataframe(pd.DataFrame(comparacao), use_container_width=True)

# ============================================================
# ABA DE FRAUDE
# ============================================================
with tab_fraude:

    st.header("Simulação de Ataque")

    colA, colB = st.columns(2)

    with colA:
        alvo = st.selectbox("Nó para corromper:", list(nos.keys()))
        modo = st.radio("Tipo:", ["Alterar dados", "Alterar hash"])

    with colB:
        if st.button("💣 Corromper Bloco"):
            df = nos[alvo].copy()
            idx = len(df) - 1

            if modo == "Alterar dados":
                df.at[idx, "etapa"] += " 🚨 (ALTERADO)"
            df.at[idx, "hash_atual"] = sb.gerar_hash("ATAQUE", df.at[idx]["hash_anterior"])

            nos[alvo] = df
            st.error(f"{alvo} foi corrompido!")

    st.divider()

    if st.button("🔍 Detectar Divergência"):
        if validar_consenso(nos):
            st.success("Tudo sincronizado")
        else:
            st.warning("Diferença detectada!")
            st.write(detectar_no_corrompido(nos))

    if st.button("🧹 Recuperar"):
        try:
            ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
            freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
            hash_ok = max(freq, key=freq.get)
            nos = recuperar_no(nos, hash_ok)
            st.success("Nós recuperados.")
        except:
            st.error("Erro ao recuperar.")


    
