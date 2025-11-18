# ===========================================================
# smartlog_blockchain.py — Módulo Base do Simulador (PoA)
# ===========================================================
# Autor: Claudio Hideki Yoshida (Orion IA)
# Versão 3 — Totalmente determinística, com bloco gênesis garantido
# ===========================================================

import pandas as pd
import hashlib
import json
from datetime import datetime
import uuid

# ===========================================================
# HASH DETERMINÍSTICO
# ===========================================================

def gerar_hash(conteudo, hash_anterior):
    """
    Calcula hash SHA256 de maneira determinística.
    """
    bloco_str = f"{conteudo}{hash_anterior}"
    return hashlib.sha256(bloco_str.encode()).hexdigest()

# ===========================================================
# BLOCO GÊNESIS — FIXO E OBRIGATÓRIO
# ===========================================================

GENESIS_CONTENT = "SMARTLOG_GENESIS_BLOCK_V3"
GENESIS_HASH = hashlib.sha256(GENESIS_CONTENT.encode()).hexdigest()
GENESIS_TIMESTAMP = "2024-01-01T00:00:00Z"

GENESIS_BLOCK = {
    "bloco_id": 0,
    "eventos": {},               # Nenhum evento no gênesis
    "hash_anterior": "0",
    "hash_atual": GENESIS_HASH,
    "tx_id": "GENESIS",
    "timestamp": GENESIS_TIMESTAMP
}

# ===========================================================
# CRIAÇÃO DA BLOCKCHAIN INICIAL
# ===========================================================

def criar_blockchain_inicial(df_eventos=None, limite_blocos=20):
    """
    Cria blockchain sempre iniciando pelo bloco gênesis.
    Mesmo que df_eventos esteja vazio ou None.
    """
    blockchain = [GENESIS_BLOCK]  # Sempre inicia com 1 bloco
    hash_anterior = GENESIS_HASH

    # Se não houver eventos → retorna apenas o gênesis
    if df_eventos is None or len(df_eventos) == 0:
        return pd.DataFrame(blockchain)

    # Adiciona blocos derivados dos eventos iniciais
    for _, evento in df_eventos.head(limite_blocos).iterrows():

        lote = evento.to_dict()
        for k, v in lote.items():
            if isinstance(v, (datetime, pd.Timestamp)):
                lote[k] = v.isoformat()

        conteudo_json = json.dumps(lote, ensure_ascii=False, sort_keys=True)
        hash_atual = gerar_hash(conteudo_json, hash_anterior)

        bloco = {
            "bloco_id": len(blockchain),
            "eventos": lote,
            "hash_anterior": hash_anterior,
            "hash_atual": hash_atual,
            "tx_id": f"INIT_{len(blockchain)}",
            "timestamp": GENESIS_TIMESTAMP
        }

        blockchain.append(bloco)
        hash_anterior = hash_atual

    return pd.DataFrame(blockchain)

# ===========================================================
# VALIDAÇÃO
# ===========================================================

def validar_blockchain(blockchain_df):
    """
    Verifica encadeamento completo da blockchain.
    """
    if blockchain_df is None or len(blockchain_df) == 0:
        return False

    for i in range(1, len(blockchain_df)):
        atual = blockchain_df.iloc[i]
        anterior = blockchain_df.iloc[i - 1]

        conteudo = json.dumps(atual.eventos, ensure_ascii=False, sort_keys=True)
        recalculado = gerar_hash(conteudo, atual.hash_anterior)

        if atual.hash_anterior != anterior.hash_atual:
            return False

        if atual.hash_atual != recalculado:
            return False

    return True

# ===========================================================
# NÓS (copiados sempre iguais)
# ===========================================================

def criar_nos(blockchain_df, total=3):
    """
    Cria N nós idênticos (deep copy garantido).
    """
    return {f"Node_{chr(65+i)}": blockchain_df.copy() for i in range(total)}

# ===========================================================
# CONSENSO (determinístico)
# ===========================================================

def validar_consenso(nos):
    """
    Checa se todos os nós têm o mesmo hash final.
    Evita erros quando algum nó está vazio.
    """
    ultimos = []
    for df in nos.values():
        if df is None or len(df) == 0:
            ultimos.append("VAZIO")
        else:
            ultimos.append(df.iloc[-1]["hash_atual"])

    return len(set(ultimos)) == 1

def detectar_no_corrompido(nos):
    """
    Identifica nós fora do consenso.
    """
    ultimos = {}
    for nome, df in nos.items():
        if df is None or len(df) == 0:
            ultimos[nome] = "VAZIO"
        else:
            ultimos[nome] = df.iloc[-1]["hash_atual"]

    freq = {}
    for h in ultimos.values():
        freq[h] = freq.get(h, 0) + 1

    hash_ok = max(freq, key=freq.get)

    return [n for n, h in ultimos.items() if h != hash_ok]

def recuperar_no(nos, hash_ok):
    """
    Restaura nó copiando blockchain do nó majoritário.
    """
    base = None
    for df in nos.values():
        if len(df) > 0 and df.iloc[-1]["hash_atual"] == hash_ok:
            base = df.copy()
            break

    if base is None:
        raise ValueError("Nenhum nó válido encontrado para recuperação.")

    for nome, df in nos.items():
        if len(df) == 0 or df.iloc[-1]["hash_atual"] != hash_ok:
            nos[nome] = base.copy()

    return nos

# ===========================================================
# PROPOSTA E VOTAÇÃO PoA
# ===========================================================

def simular_chaves_privadas(nos):
    return {n: f"key_{n}_secret" for n in nos}

def assinar_bloco(chave_privada, hash_bloco):
    return hashlib.sha256((chave_privada + ":" + hash_bloco).encode()).hexdigest()

def propor_bloco(nodo_nome, eventos, hash_anterior):
    """
    Cria proposta determinística (sem timestamp).
    """
    tx_id = str(uuid.uuid4())

    if isinstance(eventos, (list, dict)):
        conteudo = json.dumps(eventos, ensure_ascii=False, sort_keys=True)
    else:
        conteudo = str(eventos)

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

def votar_proposta(proposta, nos, chaves_privadas):
    """
    Nó vota somente se estiver alinhado com o hash_anterior.
    """
    for n in nos.keys():
        ultimo_hash = nos[n].iloc[-1]["hash_atual"]

        if ultimo_hash == proposta["hash_anterior"]:
            assinatura = assinar_bloco(chaves_privadas[n], proposta["hash_bloco"])
            proposta["assinaturas"][n] = assinatura
        else:
            proposta["assinaturas"][n] = "Recusado"

    return proposta

# ===========================================================
# CONSENSO FINAL
# ===========================================================

def aplicar_consenso(proposta, nos, quorum=2):
    votos_validos = sum(
        1 for a in proposta["assinaturas"].values()
        if not a.startswith("Recusado")
    )

    if votos_validos < quorum:
        return False, None

    tx_id_final = proposta["tx_id_proposta"]

    for nome, df in nos.items():
        bloco = {
            "bloco_id": len(df),
            "eventos": json.dumps(proposta["eventos"], ensure_ascii=False),
            "timestamp": GENESIS_TIMESTAMP,
            "hash_anterior": proposta["hash_anterior"],
            "hash_atual": proposta["hash_bloco"],
            "tx_id": tx_id_final
        }

        nos[nome] = pd.concat([df, pd.DataFrame([bloco])], ignore_index=True)

    return True, tx_id_final

# ===========================================================
# AUDITORIA
# ===========================================================

def auditar_nos(nos):
    return pd.DataFrame([
        {
            "nó": nome,
            "hash_final": df.iloc[-1]["hash_atual"],
            "tx_id_final": df.iloc[-1]["tx_id"],
            "tamanho": len(df),
        }
        for nome, df in nos.items()
    ])

# ===========================================================
# EXPORTAÇÃO
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
