# ===========================================================
# 🌐 web3_demo_simulado.py — Demonstração Web3 (sem blockchain real)
# ===========================================================
# Mostra como o SmartLog Blockchain poderia ancorar seus blocos
# em uma rede pública Web3, sem precisar de conexão real.
# ===========================================================

import hashlib
import random
from datetime import datetime
import streamlit as st

def mostrar_demo_web3(evento_texto, hash_final):
    st.markdown("### 🌐 Demonstração de Integração Web3 (Simulada)")
    st.write("Nesta simulação, mostramos como o bloco SmartLog seria registrado em uma blockchain pública:")

    # 🔹 Gera hash da entrega (simulando payload da transação)
    conteudo = f"{evento_texto}-{hash_final}-{datetime.utcnow().isoformat()}"
    tx_hash = hashlib.sha256(conteudo.encode()).hexdigest()

    st.code(tx_hash, language="bash")
    st.caption("🪙 Hash de transação simulada — representaria o registro on-chain deste bloco.")
    st.info("✅ Demonstração concluída — o sistema está pronto para integração real com Web3 (Ethereum, Polygon, etc.).")

    return tx_hash
