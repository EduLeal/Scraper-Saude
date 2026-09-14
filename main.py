import os
from src.crawler import varrer_txt
from src.scraper import consumir_fila
from src.aux_scripts.gerador_relatorio import enviar_resumo_diario

def pipeline_diario():
    print("pipeline iniciada")
    
   
    print("parte 1 - crawler")
    stats_crawler = varrer_txt("urls.txt", paginas_por_empresa=2)
    
    print("\nparte 2 - scraper")
    stats_scraper = consumir_fila()
    
    total_erros = stats_crawler["erros"] + stats_scraper["erros"]
    
    print("\nparte 3 - report")
    enviar_resumo_diario(
        qtd_novos_links=stats_crawler["novos"],
        qtd_baixados=stats_scraper["baixados"],
        qtd_erros=total_erros
    )
    
    print("\npipeline finalizada")

if __name__ == "__main__":
    pipeline_diario()