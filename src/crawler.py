import sqlite3
import time
import random
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp
from dotenv import load_dotenv

def inserir_fila_banco(hash_url, empresa, url_completa, status):
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        conexao = sqlite3.connect('./src/db/controle_fila.db')
        cursor = conexao.cursor()

        #do update set lida com a mudança de status e manda baixar de novo, caso o status mude
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
        if inseridos == 1: #1 = link novo, 0 = link velho a ser ignorado
            print(f"reclamação inserida na fila: {hash_url}, status: {status}")
            
        conexao.commit()
        return 1 if inseridos > 0 else 0 # retorna 1 se inserido, 0 se ignorado
        
    except Exception as e:
        print(f"erro url: {hash_url}: {e}")
        return 0
    finally:
        conexao.close()

def extrair_dados_da_pagina(pagina, empresa):
    novos_links = 0
    erros = 0

    print(f"empresa: {empresa}...")
    try:
        seletor_card_reclamacao = f'a[href^="/{empresa}/"]'
        pagina.wait_for_selector(seletor_card_reclamacao, timeout=10000)
        
        elementos_links = pagina.locator(seletor_card_reclamacao).all()

        endereco_base = os.getenv("ENDERECO_BASE_CRAWLER")
        
        for elemento in elementos_links:
            href = elemento.get_attribute('href')
            if not href or '_' not in href:
                continue
            
            
            url_reclamacao = f"{endereco_base.rstrip('/')}/{href.lstrip('/')}"
            
            try:
                hash_url = href.strip('/').split('_', 1)[1]
                
                if len(hash_url) < 10: #filtro de hashs muito curtos
                    print(f"link filtrado: {url_reclamacao}")
                    continue
                    
            except Exception:
                continue
            
            status = "Pendente" 
            texto_elemento = elemento.inner_text().lower()
            if "não respondida" in texto_elemento:
                status = "Não Respondida"
            elif "respondida" in texto_elemento:
                status = "Respondida"
            elif "não resolvido" in texto_elemento: 
                status = "Não Resolvido"    
            elif "resolvido" in texto_elemento:
                status = "Resolvido"
            novos_links += inserir_fila_banco(hash_url, empresa, url_reclamacao, status)
            
    except Exception as e:
        print(f"falha ao extrair a página: {e}")
        erros += 1

    return novos_links, erros

def aguardar_exec():
    tempo_espera = random.uniform(7.0, 13.5)
    print(f"Aguardando {tempo_espera:.2f} segundos antes da próxima página...")
    time.sleep(tempo_espera)

def iniciar_crawler(empresa, url_base, total_paginas):
    sb = sb_cdp.Chrome(locale="pt-BR", headless=True) #navegador camuflado do cloudflare
    endpoint_url = sb.get_endpoint_url()

    estatisticas = {"novos": 0, "erros": 0}
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            context = browser.contexts[0]
            pagina = context.pages[0]

            for numero_pagina in range(1, total_paginas + 1):
                url_paginada = f"{url_base}?pagina={numero_pagina}"
                print(f"\npágina {numero_pagina}/{total_paginas} acessando: {url_paginada}")
                
                try:
                    pagina.goto(url_paginada)
                    time.sleep(5) 

                    qtd_novos, qtd_erros = extrair_dados_da_pagina(pagina, empresa)
                    estatisticas["novos"] += qtd_novos
                    estatisticas["erros"] += qtd_erros

                except Exception as e:
                    print(f"erro ao processar a página {numero_pagina}: {e}")
                    estatisticas["erros"] += 1
                
                if numero_pagina < total_paginas:
                    aguardar_exec()

            browser.close()
    finally:
        sb.driver.quit()

    return estatisticas

def varrer_txt(caminho_txt, paginas_por_empresa=2):
    total_estatisticas = {"novos": 0, "erros": 0}
    
    if not os.path.exists(caminho_txt):
        print("arquivo de urls inexistente")
        return total_estatisticas
        
    with open(caminho_txt, "r", encoding="utf-8") as arquivo:
        urls_alvo = arquivo.readlines()
        
    for url in urls_alvo:
        url = url.strip()
        if not url: continue
        
        partes_url = url.strip('/').split('/')
        empresa = partes_url[4] if len(partes_url) > 4 else "desconhecida"
        
        print(f"\n=== crawler apontado pra empresa: {empresa.upper()} ===")
        resultado = iniciar_crawler(empresa, url, paginas_por_empresa)
        
        total_estatisticas["novos"] += resultado["novos"]
        total_estatisticas["erros"] += resultado["erros"]
        
    return total_estatisticas
