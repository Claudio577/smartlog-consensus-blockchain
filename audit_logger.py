# ============================================================
# 🧾 audit_logger.py — Registro de Auditoria no Firestore
# ============================================================

from datetime import datetime
from firebase_utils import init_firebase

# Conecta ao Firestore (reaproveitando o mesmo projeto)
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
    db.collection("auditoria_logs").add(log)
