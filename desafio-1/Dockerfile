# Dockerfile — Desafio 1: Web Scraping (Books to Scrape)

FROM python:3.12-slim

LABEL maintainer="Alisson Oliveira"
LABEL description="Scraping de livros da categoria Mystery — books.toscrape.com"

WORKDIR /app

# Arquivo de dependências
COPY requirements.txt .

# Dependências Python
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper.py .

# Criar diretório de saída para o volume montado
RUN mkdir -p /app/output

# Variável de ambiente para definir onde salvar o arquivo de saída
ENV OUTPUT_DIR=/app/output

# Comando executado ao iniciar o container
CMD ["python", "scraper.py"]
