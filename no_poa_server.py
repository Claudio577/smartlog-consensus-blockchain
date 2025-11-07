# ============================================================
# ⚙️ Servidor Flask — Nó PoA do SmartLog Blockchain
# ============================================================
from flask import Flask, request, jsonify
import hashlib
import os
from datetime import datetime
import json

app = Flask(__name__)

# Identificação do nó
NOME_NO = os.getenv("NOME_NO", "Node_A")

# Ledger local (blockchain do nó)
blockchain = []

# ------------------------------------------------------------
# Função utilitária para gerar hash
# ------------------------------------------------------------
def gerar_hash(conteudo, prev_hash):
    """Gera o hash SHA256 de um bloco."""
    bloco_str = f"{conteudo}{prev_hash}{datetime.now()}"
    return hashlib.sha256(bloco_str.encode()).hexdigest()

# ------------------------------------------------------------
# Função auxiliar: salvar blockchain em arquivo (opcional)
# ------------------------------------------------------------
def salvar_blockchain_local():
    """Salva o ledger local em JSON (para testes/hackathon)."""
    with open(f"blockchain_{NOME_NO}.json", "w") as f:
        json.dump(blockchain, f, indent=2, ensure_ascii=False)

# ------------------------------------------------------------
# Endpoint: status do nó
# ------------------------------------------------------------
@app.route("/status", methods=["GET"])
def status():
    ultimo_hash = blockchain[-1]["hash_atual"] if blockchain else "GENESIS"
    return jsonify({
        "node": NOME_NO,
        "ultimo_hash": ultimo_hash,
        "tamanho": len(blockchain),
        "sincronizado": True if len(blockchain) > 0 else False
    })

# ------------------------------------------------------------
# Endpoint: proposta de bloco (recebe do painel Streamlit)
# ------------------------------------------------------------
@app.route("/proposta", methods=["POST"])
def proposta():
    data = request.json or {}
    evento = data.get("evento", "")
    hash_anterior = data.get("hash_anterior", "GENESIS")

    # Gera hash do novo bloco proposto
    novo_hash = gerar_hash(evento, hash_anterior)

    # Monta bloco básico
    bloco = {
        "index": len(blockchain) + 1,
        "timestamp": datetime.now().isoformat(),
        "evento": evento,
        "hash_anterior": hash_anterior,
        "hash_atual": novo_hash,
        "validador": NOME_NO,
        "assinatura": f"SIG-{NOME_NO}"
    }

    print(f"[{NOME_NO}] Nova proposta recebida: {evento} | Hash: {novo_hash[:10]}...")

    # Retorna o voto/assinatura para o painel
    resposta = {
        "node": NOME_NO,
        "assinatura": bloco["assinatura"],
        "hash_bloco": bloco["hash_atual"],
        "timestamp": bloco["timestamp"]
    }
    return jsonify(resposta)

# ------------------------------------------------------------
# Endpoint: adicionar bloco final (após consenso)
# ------------------------------------------------------------
@app.route("/bloco", methods=["POST"])
def bloco():
    data = request.json or {}

    # Evita duplicar blocos
    if blockchain and data.get("hash_atual") == blockchain[-1].get("hash_atual"):
        return jsonify({"status": "IGNORADO", "node": NOME_NO})

    blockchain.append(data)
    salvar_blockchain_local()

    print(f"[{NOME_NO}] ✅ Novo bloco adicionado — Hash: {data.get('hash_atual', '')[:12]}...")

    return jsonify({"status": "OK", "node": NOME_NO, "tamanho": len(blockchain)})

# ------------------------------------------------------------
# Executar servidor
# ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
