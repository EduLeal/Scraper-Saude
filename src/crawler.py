import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright
from seleniumbase import sb_cdp
from dotenv import load_dotenv
from src.db import db_manager

load_dotenv()

async def extrair_dados_da_pagina(pagina, empresa):
    novos_links = 0
    erros = 0

    print(f"[{empresa.upper()}] Analisando página...")
    try:
        seletor_card_reclamacao = f'a[href^="/{empresa}/"]'
        await pagina.wait_for_selector(seletor_card_reclamacao, timeout=15000)
        
        elementos_links = await pagina.locator(seletor_card_reclamacao).all()
        endereco_base = os.getenv("ENDERECO_BASE_CRAWLER", "https://www.reclameaqui.com.br")
        
        for elemento in elementos_links:
            href = await elemento.get_attribute('href')
            if not href or '_' not in href:
                continue
            
            url_reclamacao = f"{endereco_base.rstrip('/')}/{href.lstrip('/')}"
            
            try:
                hash_url = href.strip('/').split('_', 1)[1]
                if len(hash_url) < 10: 
                    continue
            except Exception:
                continue
            
            status = "Pendente" 
            try:
                texto_elemento = await elemento.locator('xpath=../../..').inner_text()
                texto_elemento = texto_elemento.lower()
            except:
                texto_elemento = (await elemento.inner_text()).lower()
            
            if "não respondida" in texto_elemento:
                status = "Não Respondida"
            elif "respondida" in texto_elemento:
                status = "Respondida"
            elif "não resolvido" in texto_elemento: 
                status = "Não Resolvido"    
            elif "resolvido" in texto_elemento:
                status = "Resolvido"
                
            inserido = await db_manager.inserir_ou_atualizar_fila(hash_url, empresa, url_reclamacao, status)
            novos_links += inserido
            
    except Exception as e:
        print(f"[{empresa.upper()}] Falha ao extrair a página: {e}")
        erros += 1

    return novos_links, erros

async def processar_empresa(browser, url_base, total_paginas):
    """Processa todas as páginas de uma empresa específica em uma aba isolada"""
    # extrai o nome da empresa da URL
    partes_url = url_base.strip('/').split('/')
    empresa = partes_url[4] if len(partes_url) > 4 else "desconhecida"
    
    print(f"\n=== [CRAWLER] Iniciando empresa: {empresa.upper()} ===")
    
    # cria uma nova aba isolada dentro do mesmo navegador
    pagina = await browser.new_page()
    estatisticas = {"novos": 0, "erros": 0}
    
    try:
        for numero_pagina in range(1, total_paginas + 1):
            url_paginada = f"{url_base}?pagina={numero_pagina}"
            print(f"[{empresa.upper()}] Página {numero_pagina}/{total_paginas} acessando...")
            
            try:
                await pagina.goto(url_paginada, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3) # pausa leve anti-bloqueio
                
                qtd_novos, qtd_erros = await extrair_dados_da_pagina(pagina, empresa)
                estatisticas["novos"] += qtd_novos
                estatisticas["erros"] += qtd_erros
                
            except Exception as e:
                print(f"[{empresa.upper()}] Erro ao processar a página {numero_pagina}: {e}")
                estatisticas["erros"] += 1
            
            # pausa aleatória entre páginas da mesma empresa
            if numero_pagina < total_paginas:
                tempo_espera = asyncio.get_running_loop().time() # placeholder ou random uniform
                await asyncio.sleep(5)
                
    finally:
        await pagina.close()
        print(f"=== [CRAWLER] Finalizado: {empresa.upper()} ===")
        
    return estatisticas

async def varrer_txt_async(caminho_txt, paginas_por_empresa=1):
    """Lê o arquivo de URLs e dispara o Crawler de todas as empresas EM PARALELO"""
    total_estatisticas = {"novos": 0, "erros": 0}
    
    if not os.path.exists(caminho_txt):
        print("Arquivo de URLs inexistente.")
        return total_estatisticas
        
    with open(caminho_txt, "r", encoding="utf-8") as arquivo:
        urls_alvo = [linha.strip() for linha in arquivo.readlines() if linha.strip()]
        
    if not urls_alvo:
        return total_estatisticas

    # inicia o SeleniumBase CDP para camuflagem contra o Cloudflare
    sb = sb_cdp.Chrome(locale="pt-BR", headless=False) 
    endpoint_url = sb.get_endpoint_url()
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(endpoint_url)
            
            # cria uma lista de tarefas assíncronas para rodar todas as empresas juntas
            tarefas = [
                processar_empresa(browser, url, paginas_por_empresa) 
                for url in urls_alvo
            ]
            
            resultados = await asyncio.gather(*tarefas)
            
            for res in resultados:
                total_estatisticas["novos"] += res["novos"]
                total_estatisticas["erros"] += res["erros"]
                
            await browser.close()
    finally:
        try:
            sb.driver.quit()
        except:
            pass
            
    return total_estatisticas