# ============================================================
# 🧾 audit_logger.py — Controle de Logs e Auditoria (Firestore)
# ============================================================

from datetime import datetime
from google.cloud import firestore

# ============================================================
# 🔐 Função de Auditoria
# ============================================================

def registrar_auditoria(usuario: str, acao: str, detalhes: str):
    """
    Registra um evento de auditoria no Firestore, evitando duplicações consecutivas.
    
    Args:
        usuario (str): nome do usuário ou sistema que gerou o log
        acao (str): tipo de evento (ex: "consenso_aprovado", "no_corrompido", etc.)
        detalhes (str): descrição detalhada do evento
    """
    try:
        db = firestore.Client()
        logs_ref = db.collection("auditoria_logs")

        # Obtém o último registro (ordenado por timestamp)
        ultimo_log = logs_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
        ultimo_doc = next(ultimo_log, None)

        # Evita duplicação imediata
        if ultimo_doc:
            data = ultimo_doc.to_dict()
            if (
                data.get("acao") == acao
                and data.get("detalhes") == detalhes
                and data.get("usuario") == usuario
            ):
                print("[AUDITORIA] Log duplicado detectado — ignorado.")
                return  # Não cria novo documento

        # Se passou da checagem, registra novo log
        logs_ref.add({
            "usuario": usuario,
            "acao": acao,
            "detalhes": detalhes,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[AUDITORIA] Log registrado: {acao} — {detalhes}")

    except Exception as e:
        print(f"[ERRO AUDITORIA] Falha ao registrar log: {e}")
