# ===========================================================
# smartlog_blockchain.py — Módulo Base do Simulador (PoA)
# ===========================================================
# Autor: Claudio Hideki Yoshida (Orion IA)
# Versão revisada com bloco gênesis determinístico e correções
# no hashing para funcionamento correto do consenso PoA.
# ===========================================================

import pandas as pd
import hashlib
import json
from datetime import datetime
import uuid

# ===========================================================
# Funções de Hash e Blockchain
# ===========================================================

def gerar_hash(conteudo, hash_anterior):
    """
    Calcula o hash SHA256 de forma determinística.
    """
    bloco_str = f"{conteudo}{hash_anterior}"
    return hashlib.sha256(bloco_str.encode()).hexdigest()

# ===========================================================
# BLOCO GÊNESIS DETERMINÍSTICO
# ===========================================================

GENESIS_CONTENT = "SMARTLOG_GENESIS_BLOCK_V1"
GENESIS_HASH = hashlib.sha256(GENESIS_CONTENT.encode()).hexdigest()
GENESIS_TIMESTAMP = "2024-01-01T00:00:00Z"

GENESIS_BLOCK = {
    "bloco_id": 0,
    "eventos": {},
    "hash_anterior": "0",
    "hash_atual": GENESIS_HASH,
    "tx_id": "GENESIS",
    "timestamp": GENESIS_TIMESTAMP
}

# ===========================================================
# Criação da Blockchain Inicial
# ===========================================================

def criar_blockchain_inicial(df_eventos=None, limite_blocos=20):
    """
    Cria blockchain inicial com bloco gênesis fixo (determinístico).
    Depois adiciona blocos iniciais opcionais derivados da tabela.
    """
    blockchain = [GENESIS_BLOCK]
    hash_anterior = GENESIS_HASH

    if df_eventos is None:
        return pd.DataFrame(blockchain)

    for _, evento in df_eventos.head(limite_blocos).iterrows():
        # Serializa evento
        lote = evento.to_dict()
        for k, v in lote.items():
            if isinstance(v, (datetime, pd.Timestamp)):
                lote[k] = v.isoformat()

        conteudo = json.dumps(lote, ensure_ascii=False, sort_keys=True)
        hash_atual = gerar_hash(conteudo, hash_anterior)

        bloco = {
            "bloco_id": len(blockchain),
            "eventos": lote,
            "hash_anterior": hash_anterior,
            "hash_atual": hash_atual,
            "tx_id": f"INIT_{len(blockchain)}",
            "timestamp": GENESIS_TIMESTAMP  # manter determinístico
        }

        blockchain.append(bloco)
        hash_anterior = hash_atual

    return pd.DataFrame(blockchain)


# ===========================================================
# Validação da Blockchain
# ===========================================================

def validar_blockchain(blockchain_df):
    """Valida encadeamento e hashes."""
    for i in range(1, len(blockchain_df)):
        atual = blockchain_df.iloc[i]
        anterior = blockchain_df.iloc[i - 1]

        conteudo = json.dumps(atual.eventos, ensure_ascii=False, sort_keys=True)
        hash_recalc = gerar_hash(conteudo, atual.hash_anterior)

        if atual.hash_anterior != anterior.hash_atual:
            return False
        if atual.hash_atual != hash_recalc:
            return False

    return True


# ===========================================================
# Funções de Nós
# ===========================================================

def criar_nos(blockchain_df, total=3):
    """Cria múltiplos nós idênticos."""
    return {f"Node_{chr(65+i)}": blockchain_df.copy() for i in range(total)}

def validar_consenso(nos):
    """Verifica se todos possuem mesmo último hash."""
    ultimos = [df.iloc[-1]["hash_atual"] for df in nos.values()]
    return len(set(ultimos)) == 1

def detectar_no_corrompido(nos):
    """Identifica nós divergentes."""
    ultimos = {nome: df.iloc[-1]["hash_atual"] for nome, df in nos.items()}
    freq = {}
    for h in ultimos.values():
        freq[h] = freq.get(h, 0) + 1
    hash_ok = max(freq, key=freq.get)
    return [n for n, h in ultimos.items() if h != hash_ok]

def recuperar_no(nos, hash_ok):
    """Restaura nó copiando blockchain da maioria."""
    fonte = None
    for nome, df in nos.items():
        if df.iloc[-1]["hash_atual"] == hash_ok:
            fonte = df.copy()
            break
    for nome, df in nos.items():
        if df.iloc[-1]["hash_atual"] != hash_ok:
            nos[nome] = fonte.copy()
    return nos


# ===========================================================
# Chaves, Propostas e Assinaturas (PoA)
# ===========================================================

def simular_chaves_privadas(nos):
    return {n: f"key_{n}_secret" for n in nos}

def assinar_bloco(chave_privada, hash_bloco):
    return hashlib.sha256((chave_privada + ":" + hash_bloco).encode()).hexdigest()

def propor_bloco(nodo_nome, eventos, hash_anterior):
    """
    Cria proposta de bloco.  
    **Removido timestamp variável para evitar divergência.**
    """
    tx_id = str(uuid.uuid4())

    if isinstance(eventos, (list, dict)):
        conteudo = json.dumps(eventos, ensure_ascii=False, sort_keys=True)
    else:
        conteudo = str(eventos)

    # Sem datetime.now() para manter determinístico
    conteudo_final = f"{conteudo}-{tx_id}"

    hash_bloco = gerar_hash(conteudo_final, hash_anterior)

    return {
        "propositor": nodo_nome,
        "eventos": eventos,
        "hash_anterior": hash_anterior,
        "hash_bloco": hash_bloco,
        "tx_id_proposta": tx_id,
        "assinaturas": {}
    }

# ===========================================================
# Aplicação do Consenso
# ===========================================================

def aplicar_consenso(proposta, nos, quorum=2):
    """Adiciona o bloco final idêntico em todos os nós."""
    votos_validos = sum(1 for a in proposta["assinaturas"].values() if not a.startswith("Recusado"))

    if votos_validos < quorum:
        return False, None

    tx_id_final = proposta["tx_id_proposta"]

    for nome, df in nos.items():
        bloco = {
            "bloco_id": len(df),
            "eventos": json.dumps(proposta["eventos"], ensure_ascii=False),
            "timestamp": GENESIS_TIMESTAMP,  # determinístico
            "hash_anterior": proposta["hash_anterior"],
            "hash_atual": proposta["hash_bloco"],
            "tx_id": tx_id_final
        }

        nos[nome] = pd.concat([df, pd.DataFrame([bloco])], ignore_index=True)

    return True, tx_id_final


# ===========================================================
# Auditoria
# ===========================================================

def auditar_nos(nos):
    return pd.DataFrame([
        {
            "nó": nome,
            "hash_final": df.iloc[-1]["hash_atual"],
            "tx_id_final": df.iloc[-1]["tx_id"],
            "tamanho": len(df)
        }
        for nome, df in nos.items()
    ])


# ===========================================================
# Exportações do módulo
# ===========================================================

__all__ = [
    "gerar_hash",
    "criar_blockchain_inicial",
    "validar_blockchain",
    "criar_nos",
    "validar_consenso",
    "detectar_no_corrompido",
    "recuperar_no",
    "simular_chaves_privadas",
    "propor_bloco",
    "votar_proposta",      
    "aplicar_consenso",
    "auditar_nos"
]

