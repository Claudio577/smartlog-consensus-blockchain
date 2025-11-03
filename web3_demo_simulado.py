import streamlit as st
import random
import time
import hashlib
from datetime import datetime

# Funções auxiliares para gerar dados realistas e simulados
def gerar_hash_tx():
    """Gera um hash de transação simulado (64 caracteres hexadecimais)."""
    # Generate a simulated transaction hash (64 hexadecimal characters).
    return '0x' + ''.join(random.choices('0123456789abcdef', k=64))

def gerar_endereco_contrato():
    """Gera um endereço de contrato simulado (40 caracteres hexadecimais)."""
    # Generate a simulated contract address (40 hexadecimal characters).
    return '0x' + ''.join(random.choices('0123456789ABCDEF', k=40))

# Endereços e IDs fixos para dar um senso de persistência na simulação
# Endereço de Contrato Simulado que armazena o Ledger
SMART_CONTRACT_ADDRESS = gerar_endereco_contrato()
# Endereço do Propositor (simulado) - O nó que iniciou a transação
SENDER_ADDRESS = gerar_endereco_contrato() 


def mostrar_demo_web3(evento_texto, hash_bloco_confirmado):
    """
    Função que simula a interação com um Smart Contract na Web3 
    após a confirmação do bloco no consenso PoA.
    
    Args:
        evento_texto (str): O dado logístico que foi escrito no bloco.
        hash_bloco_confirmado (str): O hash do bloco confirmado pelo PoA.
    """
    st.subheader("Integração Web3 (Simulada)")
    
    st.markdown("✅ **Transação do Contrato Inteligente Enviada com Sucesso**")
    
    # Simula um breve tempo de espera para confirmação
    with st.spinner("Aguardando confirmação e indexação do evento no Contrato Inteligente..."):
        # Simulate a brief waiting time for confirmation
        time.sleep(1.5)

    # Geração de dados Web3 simulados
    tx_hash = gerar_hash_tx()
    gas_used = random.randint(21000, 50000)
    
    col1, col2 = st.columns(2)

    with col1:
        st.metric(label="Endereço do Contrato (Ledger)", value=f"{SMART_CONTRACT_ADDRESS[:16]}...")
        st.metric(label="Hash da Transação (TX)", value=f"{tx_hash[:16]}...")
        st.metric(label="Bloco na Rede (Simulado)", value=random.randint(5000000, 9000000))
        
    with col2:
        st.metric(label="Remetente da Transação (Propositor)", value=f"{SENDER_ADDRESS[:16]}...")
        st.metric(label="Gás Consumido (Simulado)", value=f"{gas_used} Gwei")
        st.metric(label="Status", value="Sucesso", delta_color="normal")
        
    st.markdown("---")
    st.markdown(f"""
    <p style='font-size: 14px;'>
    **Dados Persistidos no Contrato:** O <code>hash_bloco_confirmado</code> 
    (<code>{hash_bloco_confirmado[:24]}...</code>) e o dado logístico 
    foram registrados no Smart Contract em uma plataforma DLT permissionada (como Ethereum, Hyperledger Fabric ou Quorum). O registro deste hash garante a imutabilidade do dado logístico, funcionando como a prova de autenticidade (Proof-of-Existence) na DLT.
    </p>
    """, unsafe_allow_html=True)
