import aiosqlite
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CAMINHO_DB = os.getenv("CAMINHO_DB", "./src/db/controle_fila.db")

async def configurar_banco():
    async with aiosqlite.connect(CAMINHO_DB, timeout=30.0) as conexao:
        await conexao.execute("PRAGMA journal_mode=WAL;")
        await conexao.commit()

async def inserir_ou_atualizar_fila(hash_url, empresa, url_completa, status):
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        async with aiosqlite.connect(CAMINHO_DB, timeout=30.0) as conexao:
            cursor = await conexao.execute('''
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
            await conexao.commit()
            
            if inseridos > 0:
                print(f"[{empresa}] reclamação na fila: {hash_url} | status: {status}")
                return 1
            return 0
            
    except Exception as e:
        print(f"erro ao processar no banco url {hash_url}: {e}")
        return 0

async def obter_pendentes():
    """retorna todas as reclamações com precisa_baixar = 1"""
    async with aiosqlite.connect(CAMINHO_DB, timeout=30.0) as conexao:
        cursor = await conexao.execute(
            "SELECT hash_url, empresa, url_completa FROM fila_reclamacoes WHERE precisa_baixar = 1"
        )
        return await cursor.fetchall()

async def atualizar_status_baixado(hash_url):
    async with aiosqlite.connect(CAMINHO_DB, timeout=30.0) as conexao:
        await conexao.execute(
            "UPDATE fila_reclamacoes SET precisa_baixar = 0 WHERE hash_url = ?", 
            (hash_url,)
        )
        await conexao.commit()

async def marcar_como_desativada(hash_url):
    async with aiosqlite.connect(CAMINHO_DB, timeout=30.0) as conexao:
        await conexao.execute(
            "UPDATE fila_reclamacoes SET status_reclamacao = 'Desativada', precisa_baixar = 0 WHERE hash_url = ?", 
            (hash_url,)
        )
        await conexao.commit()

async def resetar_falsos_desativados():
    async with aiosqlite.connect(CAMINHO_DB, timeout=30.0) as conexao:
        cursor = await conexao.execute(
            "UPDATE fila_reclamacoes SET status_reclamacao = 'Pendente', precisa_baixar = 1 WHERE status_reclamacao = 'Desativada'"
        )
        afetados = cursor.rowcount
        await conexao.commit()
        print(f"Limpeza concluída: {afetados} reclamações 'Desativadas' voltaram para a fila.")