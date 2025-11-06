# ============================================================
# Servidor Flask — Nó PoA do SmartLog
# ============================================================
from flask import Flask, request, jsonify
import hashlib
import json
import os
from datetime import datetime

app = Flask(__name__)

NOME_NO = os.getenv("NOME_NO", "Node_A")

# Blockchain local do nó
blockchain = []


def gerar_hash(conteudo, prev_hash):
    return hashlib.sha256((conteudo + prev_hash).encode()).hexdigest()


# ------------------------------------------------------------
# Endpoint: Status do nó
# ------------------------------------------------------------
@app.route("/status", methods=["GET"])
def status():
    if blockchain:
        ultimo_hash = blockchain[-1]["hash_atual"]
    else:
        ultimo_hash = "GENESIS"
    return jsonify({
        "node": NOME_NO,
        "ultimo_hash": ultimo_hash,
        "tamanho": len(blockchain)
    })


# ------------------------------------------------------------
# Endpoint: Proposta de bloco
# ------------------------------------------------------------
@app.route("/proposta", methods=["POST"])
def proposta():
    data = request.json
    evento = data.get("evento", "")
    hash_anterior = data.get("hash_anterior", "GENESIS")

    novo_hash = gerar_hash(evento, hash_anterior)
    resposta = {
        "node": NOME_NO,
        "assinatura": f"OK-{NOME_NO}",
        "hash_bloco": novo_hash,
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(resposta)


# ------------------------------------------------------------
# Endpoint: Adicionar bloco (após consenso)
# ------------------------------------------------------------
@app.route("/bloco", methods=["POST"])
def bloco():
    data = request.json
    blockchain.append(data)
    return jsonify({"status": "OK", "node": NOME_NO})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
