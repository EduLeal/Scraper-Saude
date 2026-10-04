import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def obter_conexao():
    caminho_db = os.getenv("CAMINHO_DB", "./src/db/controle_fila.db")
    return sqlite3.connect(caminho_db)

def inserir_ou_atualizar_fila(hash_url, empresa, url_completa, status):
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conexao = obter_conexao()
    
    try:
        cursor = conexao.cursor()
        cursor.execute('''
            INSERT INTO fila_reclamacoes 
            (hash_url, empresa, url_completa, status_reclamacao, precisa_baixar, data_ultima_verificacao)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(hash_url) DO UPDATE SET
                precisa_baixar = CASE WHEN status_reclamacao != excluded.status_reclamacao THEN 1 ELSE precisa_baixar END,
                status_reclamacao = excluded.status_reclamacao,
                data_ultima_verificacao = excluded.data_ultima_verificacao
            WHERE status_reclamacao != excluded.status_reclamacao
        ''', (hash_url, empresa, url_completa, status, data_atual))
        
        inseridos = cursor.rowcount
        conexao.commit()
        
        if inseridos > 0:
            print(f"reclamação inserida na fila: {hash_url}, status: {status}")
            return 1
        return 0
        
    except Exception as e:
        print(f"erro ao processar no banco url: {hash_url}: {e}")
        return 0
    finally:
        conexao.close()

def obter_pendentes():
    #retorna todas as reclamações com precisa_baixar = 1
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute("SELECT hash_url, empresa, url_completa FROM fila_reclamacoes WHERE precisa_baixar = 1")
        return cursor.fetchall()
    finally:
        conexao.close()

def atualizar_status_baixado(hash_url):
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute("UPDATE fila_reclamacoes SET precisa_baixar = 0 WHERE hash_url = ?", (hash_url,))
        conexao.commit()
    finally:
        conexao.close()

def marcar_como_desativada(hash_url):
    conexao = obter_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute("UPDATE fila_reclamacoes SET status_reclamacao = 'Desativada', precisa_baixar = 0 WHERE hash_url = ?", (hash_url,))
        conexao.commit()
    finally:
        conexao.close()