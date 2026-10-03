import time
import random
import os
import gzip
from datetime import datetime
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp 
from src.db import db_manager


def aguardar_exec():
    tempo_espera = random.uniform(7.0,13.5)
    time.sleep(tempo_espera)

def salvar_camada_bronze(html, empresa, hash_url):
    hoje = datetime.now()
    caminho_base = os.getenv("CAMINHO_DRIVE_BRONZE")
    caminho_pasta = os.path.join(caminho_base, hoje.strftime("%Y"), hoje.strftime("%m"), hoje.strftime("%d"))
    os.makedirs(caminho_pasta, exist_ok=True)
    nome_arquivo = f"{empresa}_{hash_url}.html.gz"
    caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
    
    with gzip.open(caminho_completo, 'wt', encoding='utf-8') as f:
        f.write(html)
    print(f"arquivo salvo: {caminho_completo}")

def consumir_fila():
    estatisticas = {"baixados": 0, "erros": 0}

    reclamacoes_pendentes = db_manager.obter_pendentes()    
    if not reclamacoes_pendentes:
        print('fila vazia')
        return estatisticas

    print(f"encontradas {len(reclamacoes_pendentes)} reclamações na fila, scrapper iniciando")

    tamanho_batch = 15

    for i in range(0, len(reclamacoes_pendentes), tamanho_batch):
        lote_atual = reclamacoes_pendentes[i:i + tamanho_batch]
        numero_lote = (i // tamanho_batch) + 1
        print(f"\nbatch {numero_lote} (fila {i+1} a {i+len(lote_atual)})")
        
        sb = sb_cdp.Chrome(locale="pt-BR", headless=True)
        endpoint_url = sb.get_endpoint_url()
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(endpoint_url)
                context = browser.contexts[0]
                pagina = context.pages[0]

                for hash_url, empresa, url_completa in lote_atual:
                    try:
                        print(f"\nurl acessada: {url_completa}")
                        pagina.goto(url_completa)
                        
                        try: 
                            seletor_anuncio = 'button[data-ra-ads-interstitial-close]' 
                            pagina.wait_for_selector(seletor_anuncio, timeout=3000)
                            pagina.click(seletor_anuncio)
                            print("anuncio fechado")
                            time.sleep(1)
                        except:
                            pass
                        
                        try:
                            pagina.wait_for_selector('p[data-testid="complaint-description"]', timeout=15000)
                            html_bruto = pagina.content()
                            salvar_camada_bronze(html_bruto, empresa, hash_url)
                            
                            db_manager.atualizar_status_baixado(hash_url)
                            
                        except:
                            print(f"aviso: reclamação inativa/deletada. Atualizando status no banco.")
                            html_bruto = pagina.content()
                            salvar_camada_bronze(html_bruto, empresa, hash_url)
                            
                            db_manager.marcar_como_desativada(hash_url)
                                                    
                        estatisticas["baixados"] += 1
                        
                    except Exception as e:
                        print(f"falha ao processar {url_completa}. erro: {e}")
                        estatisticas["erros"] += 1
                    
                    aguardar_exec()

                browser.close()
                
        finally:
            sb.driver.quit()
            
        if i + tamanho_batch < len(reclamacoes_pendentes):
            tempo_descanso = random.uniform(20.0, 30.0)
            print(f"\nbatch {numero_lote} concluído. aguardando {tempo_descanso:.1f} segundos...")
            time.sleep(tempo_descanso)
            
    return estatisticas