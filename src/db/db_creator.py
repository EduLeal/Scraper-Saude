# banco_controle.py
import sqlite3

def inicializar_banco():
    conexao = sqlite3.connect('./src/db/controle_fila.db')
    cursor = conexao.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fila_reclamacoes (
            hash_url TEXT PRIMARY KEY,
            empresa TEXT NOT NULL,
            url_completa TEXT NOT NULL,
            status_reclamacao TEXT,
            precisa_baixar INTEGER DEFAULT 1,
            data_ultima_verificacao TEXT
        )
    ''')


    conexao.commit()
    conexao.close()
    print("db no ar")

if __name__ == '__main__':
    inicializar_banco()