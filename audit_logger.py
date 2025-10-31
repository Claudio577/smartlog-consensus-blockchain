# ============================================================
# 🧾 audit_logger.py — Controle de Logs e Auditoria (Firestore)
# ============================================================

from datetime import datetime
from firebase_utils import init_firebase
import streamlit as st

# Inicializa Firestore compartilhado (seguro via st.secrets)
db = init_firebase()

def registrar_auditoria(usuario: str, acao: str, detalhes: str):
    """
    Registra um evento de auditoria no Firestore.
    Evita duplicações consecutivas do mesmo log.
    """
    try:
        logs_ref = db.collection("auditoria_logs")

        # Obtém o último registro (ordenado por timestamp)
        ultimo_log = logs_ref.order_by("timestamp", direction="DESCENDING").limit(1).stream()
        ultimo_doc = next(ultimo_log, None)

        # Evita duplicação imediata
        if ultimo_doc:
            data = ultimo_doc.to_dict()
            if (
                data.get("acao") == acao
                and data.get("detalhes") == detalhes
                and data.get("usuario") == usuario
            ):
                st.toast("⚠️ Log duplicado detectado — ignorado.")
                return

        # Se passou da checagem, registra novo log
        log = {
            "usuario": usuario,
            "acao": acao,
            "detalhes": detalhes,
            "timestamp": datetime.utcnow().isoformat(),
            "origem": "Streamlit Cloud"
        }

        logs_ref.add(log)
        st.toast(f"✅ Auditoria registrada: {acao}")

    except Exception as e:
        st.error(f"❌ Erro ao registrar auditoria: {e}")
