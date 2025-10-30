# ===========================================================
# 📦 smartlog_blockchain.py — Módulo Base do Simulador
# ===========================================================
# Este módulo contém as funções principais do simulador de
# blockchain e consenso para rastreamento logístico inteligente.
# ===========================================================

import pandas as pd
import hashlib
from datetime import datetime
import copy
from firebase_utils import salvar_blockchain_firestore, carregar_blockchain_firestore, limpar_blockchain_firestore

# ===========================================================
# 🔹 Funções de Hash e Blockchain
# ===========================================================

def gerar_hash(conteudo, hash_anterior="0"):
    """Gera hash SHA256 de um conteúdo + hash anterior."""
    return hashlib.sha256((str(conteudo) + hash_anterior).encode()).hexdigest()


def criar_blockchain_inicial(df_eventos, limite_blocos=20):
    """Cria blockchain simulada a partir de eventos."""
    blockchain = []
    hash_anterior = "0"

    for i, evento in df_eventos.head(limite_blocos).iterrows():
        conteudo = f"{evento.id_entrega}-{evento.source_center}-{evento.destination_name}-{evento.etapa}-{evento.timestamp}-{evento.risco}"
        hash_atual = gerar_hash(conteudo, hash_anterior)
        bloco = {
            "bloco_id": len(blockchain) + 1,
            "id_entrega": evento.id_entrega,
            "source_center": evento.source_center,
            "destination_name": evento.destination_name,
            "etapa": evento.etapa,
            "timestamp": evento.timestamp,
            "risco": evento.risco,
            "hash_anterior": hash_anterior,
            "hash_atual": hash_atual
        }
        blockchain.append(bloco)
        hash_anterior = hash_atual

    return pd.DataFrame(blockchain)


def validar_blockchain(blockchain_df):
    """Valida integridade da blockchain simulada."""
    for i in range(1, len(blockchain_df)):
        atual = blockchain_df.iloc[i]
        anterior = blockchain_df.iloc[i - 1]
        conteudo = f"{atual.id_entrega}-{atual.source_center}-{atual.destination_name}-{atual.etapa}-{atual.timestamp}-{atual.risco}"
        hash_recalc = gerar_hash(conteudo, atual.hash_anterior)
        if atual.hash_anterior != anterior.hash_atual or atual.hash_atual != hash_recalc:
            return False
    return True


# ===========================================================
# 🔹 Funções de Nós e Consenso
# ===========================================================

def criar_nos(blockchain_df, total=3):
    """Cria múltiplos nós a partir da blockchain base."""
    nos = {}
    for i in range(total):
        nos[f"Node_{chr(65 + i)}"] = blockchain_df.copy()
    return nos


def validar_consenso(nos):
    """Verifica se todos os nós possuem o mesmo último hash."""
    ultimos = [n.iloc[-1]["hash_atual"] for n in nos.values()]
    return len(set(ultimos)) == 1


def detectar_no_corrompido(nos):
    """Detecta quais nós estão fora do consenso."""
    ultimos = {nome: n.iloc[-1]["hash_atual"] for nome, n in nos.items()}
    freq = {}
    for h in ultimos.values():
        freq[h] = freq.get(h, 0) + 1
    hash_ok = max(freq, key=freq.get)
    return [nome for nome, h in ultimos.items() if h != hash_ok]


def recuperar_no(nos, hash_ok):
    """Recupera nós corrompidos, copiando blockchain da maioria."""
    fonte = None
    for nome, df in nos.items():
        if df.iloc[-1]["hash_atual"] == hash_ok:
            fonte = df.copy()
            break
    if not fonte:
        raise ValueError("Nenhum nó válido encontrado para restauração.")
    for nome, df in nos.items():
        if df.iloc[-1]["hash_atual"] != hash_ok:
            nos[nome] = fonte.copy()
    return nos


# ===========================================================
# 🔹 Funções de Consenso (Assinatura / Quorum)
# ===========================================================

def simular_chaves_privadas(nos):
    """Cria chaves privadas simuladas para cada nó."""
    return {n: f"key_{n}_secret" for n in nos.keys()}


def assinar_bloco(chave_privada, hash_bloco):
    """Assinatura simulada via hash(priv + hash_bloco)."""
    return hashlib.sha256((chave_privada + ":" + hash_bloco).encode()).hexdigest()


def propor_bloco(nodo_nome, evento, hash_anterior):
    """Cria proposta de novo bloco (não adiciona ainda)."""
    conteudo = f"{evento}-{hash_anterior}"
    hash_bloco = gerar_hash(conteudo)
    return {
        "propositor": nodo_nome,
        "evento": evento,
        "hash_anterior": hash_anterior,
        "hash_bloco": hash_bloco,
        "assinaturas": {}
    }


def votar_proposta(proposta, nos, chaves_privadas):
    """Simula votação e assinatura pelos nós."""
    for n in nos.keys():
        ultimo_hash = nos[n].iloc[-1]["hash_atual"]
        if ultimo_hash == proposta["hash_anterior"]:
            proposta["assinaturas"][n] = assinar_bloco(chaves_privadas[n], proposta["hash_bloco"])
    return proposta


def aplicar_consenso(proposta, nos, quorum=2):
    """Aplica o bloco se atingir quorum mínimo."""
    if len(proposta["assinaturas"]) >= quorum:
        for nome in nos.keys():
            novo = {
                "bloco_id": len(nos[nome]) + 1,
                "dados": proposta["evento"],
                "hash_anterior": proposta["hash_anterior"],
                "hash_atual": proposta["hash_bloco"]
            }
            nos[nome] = pd.concat([nos[nome], pd.DataFrame([novo])], ignore_index=True)
        return True
    return False

