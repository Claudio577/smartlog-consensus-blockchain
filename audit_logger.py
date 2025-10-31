# ============================================================
# 🧾 audit_logger.py — Registro de Auditoria no Firestore
# ============================================================

from datetime import datetime
from firebase_utils import init_firebase

db = init_firebase()

def registrar_auditoria(usuario, acao, detalhes):
    """
    Registra no Firestore quem fez o quê e quando.
    """
    log = {
        "usuario": usuario,
        "acao": acao,
        "detalhes": detalhes,
        "timestamp": datetime.now().isoformat()
    }

    # 🔹 Aqui cria um novo documento (ID automático)
    db.collection("auditoria_logs").add(log)
