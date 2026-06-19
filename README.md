# Teste Técnico — Automação e Web Scraping

**Candidato:** Alisson Oliveira  
**Stack:** Python 3.12 · Selenium · BeautifulSoup · openpyxl · Docker

---

## Desafios

| # | Desafio | Site | Abordagem |
|---|---------|------|-----------|
| 1 | Web Scraping com paginação | books.toscrape.com | requests + BeautifulSoup + openpyxl |
| 2 | Automação de login e checkout | saucedemo.com | Selenium + unittest |
| 3 | Automação de formulário com validações | demoqa.com | Selenium + unittest |

---

## Estrutura do Projeto

```
teste-automacao/
├── README.md
├── desafio-1/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── scraper.py
│   └── output/                        # books.xlsx gerado aqui
├── desafio-2/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── automacao_login_saucedemo.py
└── desafio-3/
    ├── Dockerfile
    ├── requirements.txt
    ├── data.json
    ├── test_form.py
    └── output/                        # confirmation.png gerado aqui
```

---

## Desafio 1 — Web Scraping (Books to Scrape)

### O que faz

Navega por todas as páginas da categoria **Mystery** de [books.toscrape.com](https://books.toscrape.com), entra em cada página de detalhe e extrai:

- Título completo, preço, nota em estrelas, disponibilidade
- **Bônus:** UPC e descrição de cada livro

Salva tudo em `books.xlsx` com cabeçalho estilizado, filtros automáticos, zebra striping e primeira linha congelada. Exibe resumo estatístico no terminal ao final.

### Rodar localmente

```bash
cd desafio-1
pip install -r requirements.txt
python scraper.py
```

### Rodar com Docker

```bash
cd desafio-1
docker build -t desafio1-scraper .
docker run --rm -v $(pwd)/output:/app/output desafio1-scraper
```

> O `books.xlsx` será gerado em `desafio-1/output/`

---

## Desafio 2 — Automação de Login (SauceDemo)

### O que faz

Automatiza o fluxo completo de [saucedemo.com](https://www.saucedemo.com) com 5 testes sequenciais e asserções em cada etapa:

| Teste | Etapa | Asserção |
|-------|-------|----------|
| 01 | Login com `standard_user` | URL contém `/inventory.html` |
| 02 | Filtro Price (low to high) | Lista de preços está ordenada |
| 03 | Adicionar 3 produtos ao carrinho | Badge atualiza corretamente a cada item |
| 04 | Checkout completo | URL final contém `/checkout-complete.html` e header = "Thank you for your order!" |
| 05 | Logout | Botão de login visível na tela |

> **Nota:** As credenciais (`standard_user` / `secret_sauce`) foram identificadas diretamente na página de login do site, conforme esperado pelo desafio.

### Decisão técnica — React e campos de formulário

O SauceDemo usa React com estado interno controlado. O `send_keys` padrão do Selenium não dispara o `onChange` do React, fazendo os campos parecerem preenchidos mas enviarem vazio. A solução foi usar o setter nativo do `HTMLInputElement.prototype` via JavaScript, que é exatamente o mecanismo que o React usa internamente:

```python
REACT_SET_VALUE = """
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(arguments[0], arguments[1]);
    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
"""
```

### Rodar localmente (navegador visível)

```bash
cd desafio-2
pip install -r requirements.txt
python automacao_login_saucedemo.py
```

### Rodar com Docker (headless automático)

```bash
cd desafio-2
docker build -t desafio2-selenium .
docker run --rm --shm-size=2g desafio2-selenium
```

> `--shm-size=2g` é obrigatório — o Chrome usa `/dev/shm` para renderizar páginas e o padrão do Docker (64 MB) causa travamento silencioso.  
> A variável `HEADLESS=true` é setada automaticamente pelo Dockerfile.

---

## Desafio 3 — Automação de Formulário (DemoQA)

### O que faz

Automatiza o preenchimento e submissão do [formulário de prática](https://demoqa.com/automation-practice-form) com 2 testes:

**Teste 1 — Formulário completo**
- Preenche todos os campos a partir do `data.json`
- Seleciona gênero via label, hobbies via checkbox, data via datepicker React
- Preenche subjects via autocomplete
- Faz upload de imagem PNG gerada automaticamente (sem dependência externa)
- Seleciona State e City nos dropdowns React-Select
- Verifica modal de confirmação com asserções em nome, email, gênero, telefone, estado e cidade
- Captura screenshot do modal em `output/confirmation.png`

**Teste 2 — Bônus: formulário vazio**
- Submete o formulário sem preencher nada
- Verifica que o modal de confirmação **não aparece**

### Dados de entrada

Os dados de preenchimento ficam em `data.json` e podem ser alterados sem tocar no código:

```json
{
  "first_name": "Alisson",
  "last_name": "Oliveira",
  "email": "alisson.oliveira@email.com",
  "gender": "Male",
  "mobile": "1199999888",
  "date_of_birth": { "day": "15", "month": "March", "year": "1995" },
  "subjects": ["Maths", "Computer Science"],
  "hobbies": ["Sports", "Reading"],
  "current_address": "Rua das Flores, 123 - São Paulo, SP",
  "state": "NCR",
  "city": "Delhi"
}
```

### Decisão técnica — anúncios e React-Select

O DemoQA tem banners fixos que sobrepõem os elementos e bloqueiam cliques. A solução foi removê-los via JavaScript antes de qualquer interação:

```python
def _dismiss_ads(self):
    self.driver.execute_script("""
        ['#fixedban', 'footer', '.google-auto-placed'].forEach(sel => {
            document.querySelectorAll(sel).forEach(el => el.remove());
        });
    """)
```

Para os dropdowns React-Select (State/City), o menu é injetado via portal diretamente no `<body>`, fora do container pai. A solução foi localizar o input pelo ID (`react-select-3-input` / `react-select-4-input`), digitar o valor e confirmar com `Keys.ENTER`.

### Rodar localmente (navegador visível)

```bash
cd desafio-3
pip install -r requirements.txt
python test_form.py
```

### Rodar com Docker (headless automático)

```bash
cd desafio-3
docker build -t desafio3-demoqa .
docker run --rm -v $(pwd)/output:/app/output --shm-size=2g desafio3-demoqa
```

> O screenshot `confirmation.png` será gerado em `desafio-3/output/`

---

## Decisões Gerais

**Por que `webdriver-manager`?**  
Gerencia o ChromeDriver automaticamente, sem necessidade de baixar manualmente ou fixar versão. No Docker, o Chrome é instalado diretamente via repositório oficial do Google.

**Por que `unittest` em vez de `pytest`?**  
O `unittest` é stdlib — zero dependência adicional. A ordenação por prefixo numérico (`test_01_`, `test_02_`) garante execução sequencial e estado compartilhado entre etapas, que é o modelo correto para testes de fluxo E2E com sessão única de browser.

**`execute_script` vs `.click()`**  
O `.click()` nativo falha quando o elemento está coberto por outro elemento ou fora da viewport. O `execute_script("arguments[0].click()")` chama o evento diretamente no DOM, contornando esse problema — especialmente útil em sites com overlays de anúncio e menus animados.