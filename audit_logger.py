# ===========================================================
# 🧾 audit_logger.py — Controle de Logs e Auditoria (Firestore)
# ===========================================================

from datetime import datetime
from firebase_utils import init_firebase # Depende da sua implementação no Streamlit
import streamlit as st
# Importar o tipo firestore para referência correta de constantes
from google.cloud.firestore import firestore 

# --- Variáveis de Ambiente (Simulação do Canvas/Streamlit Secrets) ---
# Em um ambiente real do Canvas, 'APP_ID' deve ser o valor de '__app_id'.
APP_ID = "smartlog-simulador" # Placeholder para __app_id.
# --------------------------------------------------------------------

# Inicializa Firestore compartilhado APENAS UMA VEZ para performance
@st.cache_resource
def get_db():
    # A função init_firebase() deve injetar a configuração do Firebase
    return init_firebase()

db = get_db()


def registrar_auditoria(user_id: str, acao: str, detalhes: str):
    """
    Registra um evento de auditoria no Firestore.
    
    A collection é estruturada como: /artifacts/{APP_ID}/users/{user_id}/auditoria_logs
    para cumprir os requisitos de segurança do ambiente.
    
    Evita duplicações consecutivas do mesmo log.
    """
    try:
        # CONFORME REGRAS DO AMBIENTE: Usar path seguro e privado por usuário
        # Substitua 'APP_ID' pela sua variável de ambiente real (__app_id) se necessário
        logs_ref = db.collection(f"artifacts/{APP_ID}/users/{user_id}/auditoria_logs")

        # 1. OBTENDO O ÚLTIMO LOG
        # Nota: order_by no Firestore exige um índice na coluna 'timestamp'.
        q = logs_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
        ultimo_log = q.stream()
        ultimo_doc = next(ultimo_log, None)

        # 2. Evita duplicação imediata
        if ultimo_doc:
            data = ultimo_doc.to_dict()
            # Checa apenas acao e detalhes, pois o user_id é implícito no path
            if (
                data.get("acao") == acao
                and data.get("detalhes") == detalhes
            ):
                st.toast("⚠️ Log duplicado consecutivo detectado — ignorado.", icon="🚨")
                return

        # 3. Registra novo log
        log = {
            "user_id": user_id, # Redundante, mas útil para consultas (where user_id=X)
            "acao": acao,
            "detalhes": detalhes,
            "timestamp": datetime.utcnow().isoformat(),
            "origem": "SmartLog Streamlit"
        }

        logs_ref.add(log)
        st.toast(f"✅ Auditoria registrada: {acao}", icon="🔒")

    except Exception as e:
        # Loga o erro no console para debug e mostra uma mensagem genérica
        print(f"ERRO DE AUDITORIA FIREBASE: {e}")
        st.error("❌ Erro ao registrar auditoria. Verifique a configuração do Firestore e os índices.")
