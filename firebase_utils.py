# ============================================================
# ☁️ firebase_utils.py — Integração segura com Firestore
# ============================================================
# Compatível com Streamlit Cloud (sem arquivo .json físico)
# ============================================================

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd


@st.cache_resource
def init_firebase():
    """
    Inicializa o Firebase usando credenciais do Streamlit Secrets
    (ou fallback local, se estiver rodando em ambiente de desenvolvimento).
    """
    if not firebase_admin._apps:
        try:
            # 🔹 Lê as credenciais do secrets (configuradas no Streamlit Cloud)
            firebase_config = dict(st.secrets["FIREBASE"])
            firebase_config["private_key"] = firebase_config["private_key"].replace("\\n", "\n")

            # 🔹 Inicializa o Firebase com credenciais do dicionário
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase inicializado via st.secrets")
        except Exception as e:
            # 🔹 Fallback local (usa serviceAccountKey.json, se existir)
            print(f"⚠️ Falha ao carregar do st.secrets: {e}")
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase inicializado via serviceAccountKey.json")
    
    return firestore.client()


# Inicializa Firestore (global)
db = init_firebase()


# ============================================================
# 🔹 Funções de sincronização da blockchain
# ============================================================

def salvar_blockchain_firestore(df_blockchain):
    """Salva o dataframe da blockchain no Firestore (corrigido para timestamps)."""
    try:
        df_safe = df_blockchain.copy()

        # 🔹 Converte timestamps problemáticos (datetime/NaT) em string
        if "timestamp" in df_safe.columns:
            df_safe["timestamp"] = df_safe["timestamp"].astype(str)

        # 🔹 Converte para lista de dicionários
        data = df_safe.to_dict(orient="records")

        # 🔹 Salva no Firestore (documento fixo 'rede_principal')
        db.collection("blockchains").document("rede_principal").set({
            "dados": data,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

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
    """Remove a blockchain da nuvem."""
    try:
        db.collection("blockchains").document("rede_principal").delete()
        st.warning("🧹 Blockchain removida do Firestore!")
    except Exception as e:
        st.error(f"❌ Erro ao limpar Firestore: {e}")

