# ===========================================================
# smartlog_blockchain.py — Módulo Base do Simulador (PoA)
# ===========================================================
# Autor: Claudio Hideki Yoshida (Orion IA)
# Descrição: Módulo central da simulação SmartLog Blockchain
# Refatorado para modelo Permissionado (Proof-of-Authority),
# agora com suporte a múltiplos eventos (lotes logísticos).
# ===========================================================

import pandas as pd
import hashlib
import json
from datetime import datetime
import uuid
import copy

# ===========================================================
# Funções de Hash e Blockchain (Foco em Encadeamento)
# ===========================================================

def gerar_hash(conteudo, hash_anterior):
    """
    Calcula o hash SHA256 do bloco de forma determinística
    com base no conteúdo (string/JSON) e no hash anterior.
    """
    bloco_str = f"{conteudo}{hash_anterior}"
    return hashlib.sha256(bloco_str.encode()).hexdigest()


def criar_blockchain_inicial(df_eventos, limite_blocos=3, tamanho_lote=2):
    """
    Cria blockchain inicial simulada com blocos de múltiplos eventos.
    Cada bloco representa um 'lote logístico'.
    """
    blockchain = []
    hash_anterior = "0"

    for i in range(0, min(len(df_eventos), limite_blocos * tamanho_lote), tamanho_lote):
        lote = df_eventos.iloc[i:i + tamanho_lote].to_dict(orient="records")
        tx_id = str(uuid.uuid4())
        conteudo = json.dumps(lote, ensure_ascii=False, sort_keys=True)
        hash_atual = gerar_hash(conteudo, hash_anterior)

        bloco = {
            "bloco_id": len(blockchain) + 1,
            "eventos": conteudo,  # JSON string do lote
            "hash_anterior": hash_anterior,
            "hash_atual": hash_atual,
            "tx_id": tx_id,
            "timestamp": datetime.now()
        }
        blockchain.append(bloco)
        hash_anterior = hash_atual

    return pd.DataFrame(blockchain)


def validar_blockchain(blockchain_df):
    """
    Valida integridade da blockchain simulada (PoA).
    Verifica o encadeamento de hashes e o conteúdo dos blocos.
    """
    for i in range(1, len(blockchain_df)):
        atual = blockchain_df.iloc[i]
        anterior = blockchain_df.iloc[i - 1]

        conteudo = atual.eventos
        hash_recalc = gerar_hash(conteudo, atual.hash_anterior)

        if atual.hash_anterior != anterior.hash_atual or atual.hash_atual != hash_recalc:
            print(f"❌ Falha de validação no Bloco {atual.bloco_id}:")
            print(f"Hash Anterior incorreto? {atual.hash_anterior != anterior.hash_atual}")
            print(f"Hash Atual incorreto? {atual.hash_atual != hash_recalc}")
            return False

    return True


# ===========================================================
# Funções de Nós e Consenso (PoA)
# ===========================================================

def criar_nos(blockchain_df, total=3):
    """Cria múltiplos nós idênticos a partir da blockchain base."""
    nos = {}
    for i in range(total):
        nos[f"Node_{chr(65 + i)}"] = blockchain_df.copy()
    return nos


def validar_consenso(nos):
    """Verifica se todos os nós possuem o mesmo último hash."""
    ultimos = [n.iloc[-1]["hash_atual"] for n in nos.values() if not n.empty]
    return len(set(ultimos)) == 1


def detectar_no_corrompido(nos):
    """Detecta quais nós estão fora do consenso."""
    ultimos = {nome: n.iloc[-1]["hash_atual"] for nome, n in nos.items() if not n.empty}
    freq = {}
    for h in ultimos.values():
        freq[h] = freq.get(h, 0) + 1
    hash_ok = max(freq, key=freq.get)
    return [nome for nome, h in ultimos.items() if h != hash_ok]


def recuperar_no(nos, hash_ok):
    """Recupera nós corrompidos copiando blockchain da maioria."""
    fonte = None
    for nome, df in nos.items():
        if not df.empty and df.iloc[-1]["hash_atual"] == hash_ok:
            fonte = df.copy()
            break

    if fonte is None or fonte.empty:
        raise ValueError("Nenhum nó válido encontrado para restauração.")

    for nome, df in nos.items():
        if df.empty or df.iloc[-1]["hash_atual"] != hash_ok:
            nos[nome] = fonte.copy()

    return nos


# ===========================================================
# Funções de Assinatura e Proposta
# ===========================================================

def simular_chaves_privadas(nos):
    """Cria chaves privadas simuladas para cada nó."""
    return {n: f"key_{n}_secret" for n in nos.keys()}


def assinar_bloco(chave_privada, hash_bloco):
    """Assinatura simulada via hash(priv + hash_bloco)."""
    return hashlib.sha256((chave_privada + ":" + hash_bloco).encode()).hexdigest()


def propor_bloco(nodo_nome, eventos, hash_anterior):
    """
    Cria proposta de novo bloco (PoA) com suporte a múltiplos eventos logísticos.
    'eventos' pode ser uma string (único evento) ou lista/dict (lote).
    """
    tx_id_proposta = str(uuid.uuid4())

    # Converter lista de eventos em JSON determinístico
    if isinstance(eventos, (list, dict)):
        conteudo_serializado = json.dumps(eventos, ensure_ascii=False, sort_keys=True)
    else:
        conteudo_serializado = str(eventos)

    conteudo = f"{conteudo_serializado}-{datetime.now().isoformat()}-{tx_id_proposta}"
    hash_bloco = gerar_hash(conteudo, hash_anterior)

    return {
        "propositor": nodo_nome,
        "eventos": eventos,  # Lote de eventos
        "hash_anterior": hash_anterior,
        "hash_bloco": hash_bloco,
        "tx_id_proposta": tx_id_proposta,
        "assinaturas": {}
    }


def votar_proposta(proposta, nos, chaves_privadas):
    """Simula votação e assinatura pelos nós (Proof-of-Authority)."""
    for n in nos.keys():
        ultimo_hash = nos[n].iloc[-1]["hash_atual"] if not nos[n].empty else "0"
        if ultimo_hash == proposta["hash_anterior"]:
            proposta["assinaturas"][n] = assinar_bloco(chaves_privadas[n], proposta["hash_bloco"])
        else:
            proposta["assinaturas"][n] = "Recusado"
    return proposta


# ===========================================================
# Aplicação do Consenso e Atualização dos Nós
# ===========================================================

def aplicar_consenso(proposta, nos, quorum=2):
    """
    Aplica o consenso e adiciona o bloco idêntico em todos os nós.
    Agora aceita múltiplos eventos (lote logístico).
    """
    votos_validos = sum(1 for a in proposta["assinaturas"].values() if not a.startswith("Recusado"))

    if votos_validos >= quorum:
        tx_id_final = proposta["tx_id_proposta"]

        for nome, df in nos.items():
            hash_atual = proposta["hash_bloco"]
            hash_anterior = proposta["hash_anterior"]

            bloco = {
                "bloco_id": len(df) + 1,
                "eventos": json.dumps(proposta["eventos"], ensure_ascii=False),
                "timestamp": datetime.now(),
                "hash_anterior": hash_anterior,
                "hash_atual": hash_atual,
                "tx_id": tx_id_final,
            }

            nos[nome] = pd.concat([df, pd.DataFrame([bloco])], ignore_index=True)

        return True, tx_id_final
    else:
        return False, None


# ===========================================================
# Auditoria e Exportação
# ===========================================================

def auditar_nos(nos):
    """Cria um resumo dos hashes finais de cada nó."""
    auditoria = []
    for nome, df in nos.items():
        if not df.empty:
            auditoria.append({
                "nó": nome,
                "hash_final": df.iloc[-1]["hash_atual"],
                "tx_id_final": df.iloc[-1]["tx_id"],
                "tamanho": len(df)
            })
    return pd.DataFrame(auditoria)


def exportar_blockchain(blockchain_df, caminho="blockchain_export.csv"):
    """Exporta a blockchain para CSV."""
    blockchain_df.to_csv(caminho, index=False)
    return caminho


# ===========================================================
# Exportação pública
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
    "auditar_nos",
    "exportar_blockchain"
]
