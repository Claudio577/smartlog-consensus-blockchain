# ============================================================
# ☁️ Firebase Utils — Integração com Firestore (modo seguro)
# ============================================================
# Este módulo usa as credenciais armazenadas no Streamlit Secrets
# para autenticar e manipular a blockchain no Firebase Firestore.
# ============================================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd


# ============================================================
# 🔐 Inicialização segura (usando Streamlit Secrets)
# ============================================================

@st.cache_resource
def init_firebase():
    """
    Inicializa o Firebase usando as credenciais armazenadas em st.secrets["FIREBASE"].
    O cache evita múltiplas inicializações durante a execução do app.
    """
    if not firebase_admin._apps:
        firebase_config = st.secrets["FIREBASE"]
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    return firestore.client()


# Inicializa o Firestore
db = init_firebase()


# ============================================================
# 🔹 Funções de sincronização da blockchain
# ============================================================

def salvar_blockchain_firestore(df_blockchain):
    """Salva o dataframe da blockchain no Firestore (coleção: 'blockchains')."""
    try:
        data = df_blockchain.to_dict(orient="records")
        db.collection("blockchains").document("rede_principal").set({"dados": data})
        st.success("✅ Blockchain salva no Firestore com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao salvar blockchain no Firestore: {e}")


def carregar_blockchain_firestore():
    """Carrega a blockchain da nuvem (coleção: 'blockchains')."""
    try:
        doc = db.collection("blockchains").document("rede_principal").get()
        if doc.exists:
            data = doc.to_dict().get("dados", [])
            if data:
                return pd.DataFrame(data)
        st.warning("⚠️ Nenhuma blockchain encontrada no Firestore.")
        return None
    except Exception as e:
        st.error(f"❌ Erro ao carregar blockchain: {e}")
        return None


def limpar_blockchain_firestore():
    """Remove a blockchain da nuvem (documento principal)."""
    try:
        db.collection("blockchains").document("rede_principal").delete()
        st.warning("🧹 Blockchain removida do Firestore!")
    except Exception as e:
        st.error(f"❌ Erro ao limpar Firestore: {e}")

