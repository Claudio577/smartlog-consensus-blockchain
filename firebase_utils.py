# ============================================================
# 🔥 firebase_utils.py — Integração com Firestore
# ============================================================

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pandas as pd
import streamlit as st

# ============================================================
# 🚀 Inicializa o Firebase (usando cache pra não duplicar)
# ============================================================
@st.cache_resource
def init_firebase():
    cred = credentials.Certificate("secrets/firebase_key.json")  # coloque o caminho correto
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ============================================================
# 💾 Salvar Blockchain
# ============================================================
def salvar_blockchain_firestore(df_blockchain, nome_rede="rede_principal"):
    """Salva a blockchain atual como documento no Firestore."""
    dados = df_blockchain.to_dict(orient="records")
    db.collection("blockchains").document(nome_rede).set({
        "blocks": dados,
        "atualizado_em": datetime.now().isoformat()
    })

# ============================================================
# 📥 Carregar Blockchain
# ============================================================
def carregar_blockchain_firestore(nome_rede="rede_principal"):
    """Carrega blockchain salva da nuvem."""
    doc = db.collection("blockchains").document(nome_rede).get()
    if doc.exists:
        data = doc.to_dict()
        return pd.DataFrame(data["blocks"])
    return None

# ============================================================
# 🧹 Resetar Blockchain
# ============================================================
def limpar_blockchain_firestore(nome_rede="rede_principal"):
    """Remove a blockchain da nuvem."""
    db.collection("blockchains").document(nome_rede).delete()
