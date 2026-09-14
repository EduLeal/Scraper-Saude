import sqlite3

conexao = sqlite3.connect('./src/db/controle_fila.db')
cursor = conexao.cursor()
cursor.execute("SELECT status_reclamacao, url_completa FROM fila_reclamacoes")
links = cursor.fetchall()

print(f"reclamações na fila: {len(links)} ---")

for status, url in links:
    print(f"[{status}] {url}")

conexao.close()