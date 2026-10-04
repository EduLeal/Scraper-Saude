# 🏥 Scraper Saúde - Monitoramento de Reclamações

## ⚠️ Aviso Legal e Conformidade com a LGPD

Este projeto tem fins estritamente analíticos e acadêmicos/estatísticos. Os dados coletados são públicos e anonimizados na fonte pelo próprio site das reclamações (que oculta dados sensíveis dos consumidores). O objetivo não é perfilar indivíduos, mas sim analisar o comportamento corporativo. O armazenamento segue as diretrizes da Lei Geral de Proteção de Dados (LGPD), garantindo a segurança dos arquivos (Camada Bronze restrita) e a extração apenas de métricas de atendimento ao cliente.

## 🎯 Objetivo do Estudo

O objetivo central deste projeto é **coletar, monitorar e analisar o histórico de reclamações de operadoras de saúde** (como Amil, Bradesco Saúde, Prevent Senior, entre outras).

Através da extração contínua e automatizada desses dados, o estudo visa:

*   **Mapear a jornada de atendimento** ao cliente no setor de saúde suplementar.
*   **Analisar a agilidade** das empresas (tempo de resposta) e a eficácia na resolução de problemas (taxas de "Resolvido" vs "Não Resolvido").
*   **Criar uma base de dados histórica robusta** que permita identificar padrões e falhas sistêmicas.

## 🗂️ Estrutura do Projeto

Abaixo está a árvore de diretórios do projeto baseada na nossa arquitetura de extração:

```text
Scraper-Saude/
├── .venv/                   # ambiente virtual
├── src/                     
│   ├── aux_scripts/         # scrips auxiliares de apoio
│   │   ├── gerador_relatorio.py
│   │   └── testar_banco.py
│   ├── db/                  # camada de banco de dados e gerenciamento do db
│   │   ├── controle_fila.db
│   │   ├── db_creator.py
│   │   └── db_manager.py
│   ├── crawler.py           # módulo de extração de links
│   └── scraper.py           # Módulo de extração e download do html (Camada Bronze)
├── .env                     # variáveis de ambientes (não versionadas)
├── .gitignore
├── main.py                  # orquestrador
├── README.md                
├── requirements.txt         
└── urls.txt                 # arquivo base com as URLs alvo para raspagem
```

## 📂 Função dos Arquivos

*   `urls.txt`: Arquivo de texto simples contendo a base das URLs das empresas que serão varridas.
*   `main.py`: O orquestrador da pipeline. Executa o Crawler, depois o Scraper e, por fim, chama o gerador de relatórios.
*   `src/db/db_creator.py`: Script auxiliar para inicializar a tabela no SQLite, caso o banco ainda não exista.
*   `src/db/db_manager.py`: **O Gerenciador.** Centraliza todas as operações SQL. Isola o Crawler e o Scraper de saberem como os dados são guardados.
*   `src/crawler.py`: Responsável por navegar nas páginas de listagem, extrair o hash da reclamação, verificar o status real e enviar para o `db_manager` processar a inserção ou atualização (UPSERT) na fila.
*   `src/scraper.py`: Consome a fila pendente do banco. Contém lógicas avançadas anti-bloqueio, tratamento de "links zumbis" e salva os arquivos HTML compactados em `.gz` direto no Google Drive.
*   `src/aux_scripts/gerador_relatorio.py`: Utiliza SMTP para formatar e disparar um e-mail automático com o resumo da rodada (novos links, baixados, erros).

## 🏗️️ Como a Pipeline Funciona (Fluxo de Execução)

O projeto utiliza o conceito de **Arquitetura medalhão (Camada Bronze)**, separando o mapeamento do download pesado. O fluxo diário ocorre em 3 grandes etapas:

1.  **Parte 1 - Crawler:** Lê o `urls.txt`. Abre a página de listagem de reclamações e mapeia os links e seus status atuais. Se houver um link novo ou uma mudança de status (ex: passou de "Não Respondida" para "Respondida"), ele atualiza o banco de dados e levanta a flag `precisa_baixar = 1`.
2.  **Parte 2 - Scraper:** Consulta o banco (`db_manager`) buscando todas as pendências. Acessa cada link de forma cadenciada (em lotes), extrai o código HTML bruto da página e salva compactado no disco virtual do Google Drive. Em seguida, atualiza o banco retirando o link da fila.
3.  **Parte 3 - Report:** Compila as estatísticas globais e envia o e-mail automático de prestação de contas.

## 🗄️️ Estrutura do Banco de Dados (SQLite)

O banco central `controle_fila.db` possui a tabela `fila_reclamacoes` com a seguinte modelagem:

*   `hash_url` (TEXT - Primary Key): Identificador único da reclamação.
*   `empresa` (TEXT): Nome da empresa (ex: 'amil').
*   `url_completa` (TEXT): Link completo para acesso.
*   `status_reclamacao` (TEXT): A regra de negócio observada na tela (Pendente, Respondida, Resolvido, Não Resolvido, Desativada).
*   `precisa_baixar` (INTEGER): A regra de máquina (1 = Scraper precisa baixar; 0 = Ignorar).
*   `data_ultima_verificacao` (TEXT): Timestamp do último Crawler que atualizou a linha.

## 🚧 Desafios Enfrentados e Soluções

1.  **Bloqueios Antibot (Cloudflare):** O site de reclamações utiliza forte proteção anti-raspagem. A solução foi migrar para o `SeleniumBase (sb_cdp)` integrado ao Playwright, operando via protocolo CDP para mascarar o robô como um humano navegando.
2.  **Concorrência e Locks de Banco de Dados:** Para evitar o erro `database is locked` típico do SQLite, a responsabilidade de conexão foi totalmente extraída para o `db_manager.py`, preparando a base para inserções controladas (Single-Thread Writer).
3.  **Links Zumbis e Falsos Positivos:** O site de reclamações desativa links mas mantém a URL viva sem a descrição. Para evitar que o robô confunda um simples *Timeout* de conexão com um "Link Deletado", implementamos que Scraper só classifica a reclamação como inativa no banco se encontrar literalmente as palavras "desativada" ou "inativa" no HTML da página de falha.
4.  **Extração de Status Ocultos:** A estrutura HTML dissociava o título do link da tag de status. O Crawler precisou ser refinado com seletores `xpath=../../..` para englobar o Card Completo da reclamação, corrigindo a taxonomia no banco.

## 🚀 Próximos Passos (Roadmap)

1.  **Implementar Paralelismo (Async/Multithreading):** Evoluir a execução sequencial para um modelo de Fila "Produtor-Consumidor". A ideia é rodar navegadores simultâneos com janelas restritas para acelerar a fase do Scraper nas madrugadas.
3.  **Camada Silver (ETL):** Criar a esteira de processamento secundária com Pandas/Polars. Essa esteira lerá os GZIPs da camada Bronze, extrairá os metadados finais (Datas, Textos, Replicas) e cuidará da desduplicação (mantendo sempre o HTML mais recente salvo pelo Scraper).

## 📚 Fontes Úteis e Materiais de Apoio

*   [Stealthy Playwright Mode: Bypass CAPTCHAs and Bot-Detection!](https://www.youtube.com/watch?v=PnFD_gSmGUc)

