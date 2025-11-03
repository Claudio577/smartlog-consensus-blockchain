# ===========================================================
# 🧾 audit_logger.py — Controle de Logs e Auditoria (Firestore)
# ===========================================================

from datetime import datetime
from firebase_utils import init_firebase
import streamlit as st
from firebase_admin import firestore  # ✅ Correção da importação

APP_ID = "smartlog-simulador"

@st.cache_resource
def get_db():
    return init_firebase()

db = get_db()

def registrar_auditoria(user_id: str, acao: str, detalhes: str):
    """
    Registra um evento de auditoria no Firestore.
    Usa a coleção /auditoria_logs na raiz, para compatibilidade com versão anterior.
    """
    try:
        # ✅ Caminho simplificado (raiz)
        logs_ref = db.collection("auditoria_logs")

        # 1️⃣ Obtém o último log para evitar duplicação consecutiva
        q = logs_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
        ultimo_log = q.stream()
        ultimo_doc = next(ultimo_log, None)

        if ultimo_doc:
            data = ultimo_doc.to_dict()
            if data.get("acao") == acao and data.get("detalhes") == detalhes:
                st.toast("⚠️ Log duplicado consecutivo detectado — ignorado.", icon="🚨")
                return

        # 2️⃣ Novo log
        log = {
            "usuario": user_id,
            "acao": acao,
            "detalhes": detalhes,
            "timestamp": datetime.utcnow().isoformat(),
            "origem": "Streamlit Cloud",
        }

        logs_ref.add(log)
        st.toast(f"✅ Auditoria registrada: {acao}", icon="🔒")

    except Exception as e:
        print(f"ERRO DE AUDITORIA FIREBASE: {e}")
        st.error("❌ Erro ao registrar auditoria. Verifique a configuração do Firestore e os índices.")
