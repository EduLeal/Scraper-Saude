# src/aux-scripts/email.py
import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

def enviar_resumo_diario(qtd_novos_links, qtd_baixados, qtd_erros):
    
    texto_resumo = (
        f"resumo da execução do Scraper:\n"
        f"novos links encontrados pelo Crawler: {qtd_novos_links}\n"
        f"reclamações baixadas: {qtd_baixados}\n"
        f"erros durante o processo: {qtd_erros}\n\n"
    )

    remetente = os.getenv("EMAIL_ENVIO")
    senha = os.getenv("EMAIL_SENHA")
    destinatario = os.getenv("EMAIL_DESTINO")
    
    msg = EmailMessage()
    msg.set_content(texto_resumo)
    msg['Subject'] = "relatório do scraper - execução diária"
    msg['From'] = remetente
    msg['To'] = destinatario
    
    try: 
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remetente, senha)
        servidor.send_message(msg)
        servidor.quit()
    except Exception as e:
        print(f"erro: {e}")
