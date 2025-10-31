# ============================================================
# 💰 SmartLog Blockchain — Simulador de Consenso e Fraude
# ============================================================
# Interface visual que demonstra consenso Proof-of-Authority
# com simulação de corrupção e recuperação de nós.
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import smartlog_blockchain as sb

from smartlog_blockchain import (
    criar_blockchain_inicial,
    criar_nos,
    validar_consenso,
    simular_chaves_privadas,
    propor_bloco,
    votar_proposta,
    aplicar_consenso,
    detectar_no_corrompido,
    recuperar_no
)

from firebase_utils import (
    salvar_blockchain_firestore,
    carregar_blockchain_firestore,
    limpar_blockchain_firestore
)

# ============================================================
# 🎨 CONFIGURAÇÕES INICIAIS
# ============================================================
st.set_page_config(page_title="SmartLog Blockchain", page_icon="⛓️", layout="wide")

st.title("⛓️ SmartLog Blockchain — Simulador de Consenso (PoA)")
st.markdown("""
O **SmartLog Blockchain** demonstra o funcionamento de um consenso *Proof-of-Authority* 
em redes logísticas. Cada nó valida e assina digitalmente os blocos propostos.  
Se o número de assinaturas atinge o *quorum mínimo*, o bloco é aceito por toda a rede.  
---
""")

# ============================================================
# 🧱 ESTADO INICIAL — Blockchain e Nós
# ============================================================
if "nos" not in st.session_state:
    dados = {
        "id_entrega": [1, 2, 3],
        "source_center": ["Depósito_SP", "Depósito_SP", "Depósito_RJ"],
        "destination_name": ["Centro_MG", "Centro_PR", "Centro_BA"],
        "etapa": ["Saiu do depósito", "Em rota", "Chegou ao destino"],
        "timestamp": [datetime.now()] * 3,
        "risco": ["Baixo", "Médio", "Baixo"]
    }
    eventos_df = pd.DataFrame(dados)

    blockchain_df = criar_blockchain_inicial(eventos_df)
    nos = criar_nos(blockchain_df)
    chaves = simular_chaves_privadas(nos)

    st.session_state.blockchain_df = blockchain_df
    st.session_state.nos = nos
    st.session_state.chaves = chaves
    st.session_state.historico = []

nos = st.session_state.nos
chaves = st.session_state.chaves

# ============================================================
# 🧭 INTERFACE DIVIDIDA EM ABAS
# ============================================================
tab_main, tab_fraude = st.tabs(["🔗 Simulador de Consenso", "🚨 Simulador de Fraude / Ataque"])

# ============================================================
# 🔗 ABA 1 — SIMULADOR DE CONSENSO (PRINCIPAL)
# ============================================================
with tab_main:
    st.header("🔗 Simulação de Consenso Proof-of-Authority")

    # Estado atual dos nós
    st.subheader("📦 Estado Atual dos Nós")
    col1, col2, col3 = st.columns(3)
    for i, (nome, df) in enumerate(nos.items()):
        with [col1, col2, col3][i]:
            st.metric(label=f"{nome}", value=f"Hash final: {df.iloc[-1]['hash_atual'][:12]}")

    # Propor novo bloco
    st.markdown("---")
    st.subheader("🧠 Propor Novo Bloco")
    evento_texto = st.text_input("📝 Descrição do novo evento:", "Entrega #104 — Saiu do depósito — SP → MG")
    propositor = st.selectbox("👤 Selecione o nó propositor:", list(nos.keys()))
    quorum = st.slider("📊 Defina o quorum mínimo:", 1, len(nos), 2)

    if st.button("🚀 Iniciar Simulação de Consenso"):
        st.markdown("### 🧱 Etapa 1: Criação da Proposta")
        st.info(f"📦 {propositor} está propondo o bloco: **'{evento_texto}'**")
        registrar_auditoria("Sistema", "propor_bloco", f"{propositor} propôs '{evento_texto}'")


        # 🔗 Usa o último hash comum da maioria dos nós (não só o Node_A)
        hashes_finais = [df.iloc[-1]["hash_atual"] for df in nos.values()]
        # Escolhe o hash mais frequente (a maioria)
        hash_anterior = max(set(hashes_finais), key=hashes_finais.count)

        proposta = propor_bloco(propositor, evento_texto, hash_anterior)

        st.markdown("### 🔍 Etapa 2: Votação dos Nós")
        proposta = votar_proposta(proposta, nos, chaves)


        st.markdown("#### 📊 Resultado das Assinaturas")
        assinaturas = []
        for no, assinatura in proposta["assinaturas"].items():
            if assinatura.startswith("Recusado"):
                st.error(f"❌ {no} recusou o bloco.")
                assinaturas.append({"Nó": no, "Assinatura": "❌ Rejeitado"})
            else:
                st.success(f"✅ {no} validou e assinou o bloco.")
                assinaturas.append({"Nó": no, "Assinatura": assinatura[:20] + "..."})
        st.dataframe(pd.DataFrame(assinaturas), use_container_width=True)

                st.markdown("### 🧮 Etapa 3: Cálculo do Consenso")
        st.write(f"É necessário **{quorum}** de {len(nos)} nós para aprovar o bloco.")

        sucesso = aplicar_consenso(proposta, nos, quorum=quorum)

        if sucesso:
            st.success("✅ Consenso alcançado! O bloco foi adicionado em todos os nós.")
            registrar_auditoria("Sistema", "consenso_aprovado", f"Bloco '{evento_texto}' aceito com quorum {quorum}")
            st.session_state.historico.append({
                "evento": evento_texto,
                "propositor": propositor,
                "assinaturas": len(proposta["assinaturas"]),
                "status": "Aceito"
            })
            try:
                blockchain_atual = nos["Node_A"]
                salvar_blockchain_firestore(blockchain_atual)
                st.info("☁️ Blockchain sincronizada com o Firestore!")
            except Exception as e:
                st.error(f"Erro ao salvar no Firestore: {e}")
        else:
            st.warning("⚠️ Quorum insuficiente. O bloco foi rejeitado.")
            registrar_auditoria("Sistema", "consenso_rejeitado", f"Bloco '{evento_texto}' rejeitado (quorum {quorum})")
            st.session_state.historico.append({
                "evento": evento_texto,
                "propositor": propositor,
                "assinaturas": len(proposta["assinaturas"]),
                "status": "Rejeitado"
            })

        # Histórico de consenso
        if st.session_state.historico:
            st.markdown("---")
            st.subheader("📜 Histórico de Propostas")
            st.dataframe(pd.DataFrame(st.session_state.historico), use_container_width=True)

  # ============================================================
# ☁️ FIRESTORE — SINCRONIZAÇÃO MANUAL
# ============================================================
st.markdown("---")
st.subheader("☁️ Firestore — Sincronização Manual")

col1, col2, col3 = st.columns(3)

# --- Botão: Carregar blockchain da nuvem ---
with col1:
    if st.button("📥 Carregar da Nuvem"):
        df = carregar_blockchain_firestore()
        if df is not None:
            st.dataframe(df, use_container_width=True)
            st.success("✅ Blockchain carregada com sucesso da nuvem!")
        else:
            st.warning("⚠️ Nenhum dado encontrado no Firestore.")

# --- Botão: Salvar blockchain manualmente ---
with col2:
    if st.button("💾 Salvar Manualmente"):
        try:
            salvar_blockchain_firestore(nos["Node_A"])
            st.success("✅ Blockchain salva manualmente no Firestore!")
        except Exception as e:
            st.error(f"❌ Erro ao salvar blockchain: {e}")

# --- Botão: Resetar Firestore e limpar sessão ---
with col3:
    if st.button("🧹 Resetar Firestore e Sessão"):
        try:
            # Limpa dados do Firestore
            limpar_blockchain_firestore()
            
            # Limpa sessão local
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.warning("⚠️ Blockchain removida do Firestore e sessão reiniciada. Clique em **Rerun** acima.")
            st.stop()
        except Exception as e:
            st.error(f"❌ Erro ao limpar Firestore: {e}")



# ============================================================
# 🔍 STATUS DE CONSENSO / REDE
# ============================================================
st.markdown("---")
st.subheader("🔍 Status da Rede")

# Centraliza visualmente (mantém no eixo principal, não em colunas)
st.markdown("Verificação automática de integridade entre os nós da rede blockchain:")

# Verifica se há divergências
if validar_consenso(nos):
    st.success("🟢 Todos os nós estão sincronizados e íntegros.")
else:
    st.warning("🟠 Divergência detectada entre os nós!")

# Mostra hash final de cada nó lado a lado
st.markdown("### 📊 Hash Final por Nó")
hashes_finais = {nome: df.iloc[-1]["hash_atual"][:16] for nome, df in nos.items()}
st.dataframe(
    pd.DataFrame(list(hashes_finais.items()), columns=["Nó", "Hash Final"]),
    use_container_width=True
)


# ============================================================
# 🚨 ABA 2 — SIMULADOR DE FRAUDE / NÓ MALICIOSO
# ============================================================
with tab_fraude:
    st.header("🚨 Simulador de Fraude / Nó Malicioso")
    st.markdown("""
Demonstração **didática** de corrupção proposital em um nó.  
Permite observar como a integridade dos dados é quebrada e como o sistema detecta e recupera divergências.
---
""")

    colA, colB, colC = st.columns(3)
    with colA:
        node_to_corrupt = st.selectbox("🧩 Escolha o nó para corromper:", list(nos.keys()), key="fraude_node")
        corrupt_type = st.radio("💥 Tipo de corrupção:", ["Alterar último bloco (dados)", "Alterar hash final"])

    # ============================
    # 🧨 Simular Ataque
    # ============================
    with colB:
        if st.button("💣 Corromper nó (simular ataque)", key="fraude_attack"):
            df = nos[node_to_corrupt].copy()
            if len(df) > 0:
                idx = len(df) - 1
                # Salva o estado original do último bloco
                original = df.iloc[idx].to_dict()

                # --- Aplica corrupção ---
                if corrupt_type == "Alterar último bloco (dados)":
                    df.at[idx, "etapa"] = str(df.at[idx, "etapa"]) + " (ALTERADO MALICIOSAMENTE)"
                    conteudo = f"{df.at[idx,'id_entrega']}-{df.at[idx,'source_center']}-{df.at[idx,'destination_name']}-{df.at[idx,'etapa']}-{df.at[idx,'timestamp']}-{df.at[idx,'risco']}"
                    df.at[idx, "hash_atual"] = sb.gerar_hash(conteudo, df.at[idx, "hash_anterior"])
                else:
                    df.at[idx, "hash_atual"] = sb.gerar_hash("ATAQUE_MALICIOSO", df.at[idx, "hash_anterior"])

                # Atualiza nó
                nos[node_to_corrupt] = df
                modificado = df.iloc[idx].to_dict()

                # --- Mostra comparação didática ---
                st.error(f"⚠️ {node_to_corrupt} corrompido (simulado).")
                registrar_auditoria("Sistema", "no_corrompido", f"{node_to_corrupt} corrompido ({corrupt_type})")

                comparacao = pd.DataFrame([
                    {"Campo": "Etapa", "Antes": original["etapa"], "Depois": modificado["etapa"]},
                    {"Campo": "Hash Atual", "Antes": original["hash_atual"][:16], "Depois": modificado["hash_atual"][:16]},
                    {"Campo": "Hash Anterior", "Antes": original["hash_anterior"][:16], "Depois": modificado["hash_anterior"][:16]},
                ])
                st.dataframe(comparacao, use_container_width=True)

            else:
                st.warning("⚠️ Este nó não contém blocos para corromper.")

    # ============================
    # 🔍 Detectar divergências
    # ============================
    with colC:
        if st.button("🔍 Detectar divergência", key="fraude_detect"):
            if validar_consenso(nos):
                st.success("🟢 Todos os nós estão íntegros e sincronizados.")
            else:
                st.warning("🟠 Divergência detectada entre os nós!")
                corrompidos = detectar_no_corrompido(nos)
                st.write("Nós corrompidos identificados:", corrompidos)
                ultimos = {n: df.iloc[-1]["hash_atual"][:16] for n, df in nos.items()}
                st.dataframe(pd.DataFrame(list(ultimos.items()), columns=["Nó", "Hash final"]), use_container_width=True)

    # ============================
    # 🔁 Recuperação e Resumo
    # ============================
    st.markdown("---")
    if st.button("🧹 Recuperar nós corrompidos (copiar da maioria)", key="fraude_recover"):
        try:
            ultimos = {n: df.iloc[-1]["hash_atual"] for n, df in nos.items()}
            freq = {h: list(ultimos.values()).count(h) for h in ultimos.values()}
            hash_ok = max(freq, key=freq.get)
            nos = recuperar_no(nos, hash_ok)
            st.success("✅ Nós corrompidos restaurados com sucesso usando a blockchain da maioria.")
        except Exception as e:
            st.error(f"❌ Erro ao restaurar nós: {e}")
            st.success("✅ Nós corrompidos restaurados com sucesso usando a blockchain da maioria.")
        registrar_auditoria("Sistema", "no_recuperado", "Nós restaurados com base no hash majoritário.")


    if st.button("📊 Mostrar resumo das blockchains (por nó)", key="fraude_summary"):
        for nome, df in nos.items():
            st.markdown(f"**{nome}** — {len(df)} blocos — hash final `{df.iloc[-1]['hash_atual'][:16]}...`")
            st.dataframe(
                df[["bloco_id", "id_entrega", "source_center", "destination_name", "etapa", "hash_atual"]].tail(2),
                use_container_width=True
            )
from audit_logger import registrar_auditoria

if st.button("🧾 Testar auditoria Firestore"):
    registrar_auditoria("Claudio", "teste_streamlit", "Rodando direto pelo Streamlit Cloud")
    st.success("✅ Log enviado para o Firestore!")

