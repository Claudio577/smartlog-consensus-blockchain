# ===========================================================
# 💠 smartlog_blockchain.py — Módulo Base do Simulador
# ===========================================================
# Autor: Claudio Hideki Yoshida (Orion IA)
# Descrição: Módulo central da simulação SmartLog Blockchain.
# Corrigido para manter o hash_anterior idêntico ao do painel
# e garantir encadeamento perfeito entre blocos.
# ===========================================================

import pandas as pd
import hashlib
from datetime import datetime
import uuid

# ===========================================================
# 🔹 Funções de Hash e Blockchain
# ===========================================================

def gerar_hash(conteudo, hash_anterior="0"):
    """Gera hash SHA256 de um conteúdo + hash anterior."""
    return hashlib.sha256((str(conteudo) + str(hash_anterior)).encode()).hexdigest()


def criar_blockchain_inicial(df_eventos, limite_blocos=20):
    """Cria blockchain simulada a partir de eventos iniciais."""
    blockchain = []
    hash_anterior = "0"

    for _, evento in df_eventos.head(limite_blocos).iterrows():
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
# 🔹 Consenso e Propostas
# ===========================================================

def simular_chaves_privadas(nos):
    """Cria chaves privadas simuladas para cada nó."""
    return {n: f"key_{n}_secret" for n in nos.keys()}


def assinar_bloco(chave_privada, hash_bloco):
    """Assinatura simulada: hash(privada + hash_bloco)."""
    return hashlib.sha256((chave_privada + ":" + hash_bloco).encode()).hexdigest()


def propor_bloco(nodo_nome, evento, hash_anterior):
    """Cria proposta de novo bloco com hash calculado e encadeado."""
    conteudo = f"{evento}-{datetime.now().isoformat()}"
    hash_bloco = gerar_hash(conteudo, hash_anterior)
    return {
        "propositor": nodo_nome,
        "evento": evento,
        "hash_anterior": hash_anterior,
        "hash_bloco": hash_bloco,
        "assinaturas": {}
    }


def votar_proposta(proposta, nos, chaves_privadas):
    """Simula votação e assinatura dos nós."""
    for n in nos.keys():
        ultimo_hash = nos[n].iloc[-1]["hash_atual"] if not nos[n].empty else "0"
        if ultimo_hash == proposta["hash_anterior"]:
            proposta["assinaturas"][n] = assinar_bloco(chaves_privadas[n], proposta["hash_bloco"])
        else:
            proposta["assinaturas"][n] = "Recusado"
    return proposta


def aplicar_consenso(proposta, nos, quorum=2):
    """
    Aplica o consenso e adiciona o bloco com o mesmo hash da proposta.
    Mantém o hash_anterior idêntico ao exibido no painel e garante 
    encadeamento consistente em todos os nós.
    """
    votos_validos = sum(1 for a in proposta["assinaturas"].values() if not a.startswith("Recusado"))

    if votos_validos >= quorum:
        for nome, df in nos.items():
            novo_bloco = {
                "bloco_id": len(df) + 1,
                "id_entrega": str(uuid.uuid4())[:8],
                "source_center": "Desconhecido",
                "destination_name": "Desconhecido",
                "etapa": proposta["evento"],
                "timestamp": datetime.now(),
                "risco": "Baixo",
                "hash_anterior": proposta["hash_anterior"],   # 🔗 idêntico ao painel
                "hash_atual": proposta["hash_bloco"]          # ✅ mesmo hash da proposta
            }
            nos[nome] = pd.concat([df, pd.DataFrame([novo_bloco])], ignore_index=True)
        return True
    else:
        return False


# ===========================================================
# 🔹 Exportação do módulo
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
    "aplicar_consenso"
]

