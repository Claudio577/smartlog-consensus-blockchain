# ============================================================
# ☁️ Firebase Utils — Integração com Firestore (modo seguro)
# ============================================================
# Compatível com Streamlit Cloud (sem .json físico)
# ============================================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import json


@st.cache_resource
def init_firebase():
    """Inicializa o Firebase usando credenciais do Streamlit Secrets."""
    if not firebase_admin._apps:
        # 🔹 Converte o conteúdo do secrets (TOML → dict JSON)
        firebase_config = dict(st.secrets["FIREBASE"])
        firebase_config["private_key"] = firebase_config["private_key"].replace("\\n", "\n")

        # 🔹 Inicializa o Firebase com credenciais no formato dict
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    
    return firestore.client()


# Inicializa o Firestore
db = init_firebase()


# ============================================================
# 🔹 Funções de sincronização
# ============================================================

def salvar_blockchain_firestore(df_blockchain):
    """Salva o dataframe da blockchain no Firestore."""
    try:
        data = df_blockchain.to_dict(orient="records")
        db.collection("blockchains").document("rede_principal").set({"dados": data})
        st.success("✅ Blockchain salva no Firestore com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao salvar blockchain no Firestore: {e}")


def carregar_blockchain_firestore():
    """Carrega a blockchain da nuvem."""
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
    """Remove blockchain da nuvem."""
    try:
        db.collection("blockchains").document("rede_principal").delete()
        st.warning("🧹 Blockchain removida do Firestore!")
    except Exception as e:
        st.error(f"❌ Erro ao limpar Firestore: {e}")

