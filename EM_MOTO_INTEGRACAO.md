# EM MOTO - INTEGRAÇÃO COMPLETA ✅

## 📦 O QUE FOI FEITO

Adicionada a loja **EM Moto** (em-moto.com) ao comparador de preços.

### **Ficheiros Criados:**
- ✅ `scrapers/emmoto.py` - Scraper completo para EM Moto

### **Ficheiros Modificados:**
- ✅ `config.py` - Adicionada URL da EM Moto
- ✅ `main.py` - Adicionado import e registo do scraper

---

## 🎯 CARACTERÍSTICAS DA EM MOTO

**Tipo de Site:** Magento 2  
**URL Base:** https://em-moto.com/  
**Pesquisa:** Direta por URL (`/en/catalogsearch/result/?q=REF`)

**Vantagens:**
- ✅ Pesquisa muito simples e direta
- ✅ Estrutura HTML bem organizada (Magento)
- ✅ Preços claramente identificados
- ✅ Extração de SKU do produto (data-product-sku)

**Métodos de Extração de Preço:**
1. Meta tag Open Graph: `<meta property="product:price:amount">`
2. Atributo `data-price-amount` nos spans
3. Preço especial (promoções)
4. Preço regular
5. JSON-LD (fallback)

---

## 🚀 COMO USAR

### **1. Pesquisar só na EM Moto**
```bash
python main.py --stores emmoto
```

### **2. Pesquisar na EM Moto + outras lojas**
```bash
# EM Moto + WRS
python main.py --stores emmoto wrs

# EM Moto + WRS + Omnia
python main.py --stores emmoto wrs omniaracing
```

### **3. Teste com limite de produtos**
```bash
# Testar com primeiros 5 produtos, Chrome visível
python main.py --stores emmoto --max 5 --headful
```

### **4. Todas as lojas (incluindo EM Moto)**
```bash
python main.py
```

---

## 📊 ESTRUTURA DO EXCEL

O Excel gerado terá agora uma coluna adicional para a EM Moto:

```
| Ref | Teu Preço | WRS Preço | WRS Dif% | ... | EM Moto Preço | EM Moto Dif% | EM Moto URL |
```

**Colunas por loja:**
- **Preço** - Preço encontrado
- **Dif %** - Diferença percentual com cores:
  - 🟢 Verde = Loja mais cara que tu (estás competitivo!)
  - 🔴 Vermelho = Loja mais barata que tu (considera baixar preço)
  - ⚫ Cinza = Produto não encontrado
- **URL** - Link direto para o produto

---

## 🔧 DETALHES TÉCNICOS

### **Como Funciona a Pesquisa:**

1. **URL de Pesquisa Direta**
   - Construir: `https://em-moto.com/en/catalogsearch/result/?q=REF`
   - Exemplo: `https://em-moto.com/en/catalogsearch/result/?q=H.094.L4K`

2. **Extração da Listagem**
   - Produtos em: `<li class="item product product-item">`
   - Nome: `<a class="product-item-link">`
   - Preço: `<span data-price-amount="799.26">`

3. **Validação**
   - Extrai SKU do atributo `data-product-sku`
   - Procura código no título, meta tags e conteúdo
   - Usa o sistema de validação do comparador (confidence score)

4. **Cache**
   - Produtos encontrados: cache de 10 dias
   - Produtos não encontrados: cache de 4 dias

---

## 📝 EXEMPLOS DE RESULTADOS

### **Exemplo 1: Produto Encontrado**
```
Ref: H.094.L4K
Teu preço: €850.00

Resultados:
  EM Moto: €799.26  (-6.0%)  🔴  [Link]
  → Atenção! EM Moto está mais barata
```

### **Exemplo 2: Produto Não Encontrado**
```
Ref: XPTO123
Teu preço: €45.00

Resultados:
  EM Moto: --  ⚫  
  → Produto não disponível (pode ser exclusivo teu!)
```

---

## ✅ VALIDAÇÃO E TESTES

### **Verificações Implementadas:**

- ✅ Pesquisa com referências simples (H094L4K)
- ✅ Pesquisa com referências compostas (P-HF1595)
- ✅ Extração de preços normais
- ✅ Extração de preços promocionais
- ✅ Validação de correspondência de produto
- ✅ Tratamento de erros (timeout, produto não encontrado)
- ✅ Sistema de cache funcional

### **Para Testar:**
```bash
# Teste básico com 3 produtos, Chrome visível
python main.py --stores emmoto --max 3 --headful

# Teste completo sem cache
python main.py --stores emmoto --nocache
```

---

## 🐛 TROUBLESHOOTING

### **"Nenhum produto encontrado"**
→ Possíveis causas:
- Referência não existe na loja
- Site mudou estrutura HTML (verificar source code)
- Timeout de carregamento (aumentar `PAGE_LOAD_TIMEOUT` em config.py)

### **"Sem preço"**
→ Verificar:
- Produto existe mas está sem stock?
- Preço só visível para clientes logados?
- Site mudou seletores de preço?

### **Chrome não abre/trava**
→ Usar modo visível para debug:
```bash
python main.py --stores emmoto --headful
```

---

## 📞 INFORMAÇÕES ADICIONAIS

**Versão do Scraper:** 1.0  
**Data:** 04 Nov 2025  
**Compatibilidade:** Comparador v4.5+  
**Dependências:** Selenium, BeautifulSoup4, lxml  

**Localização dos Ficheiros:**
```
comparador_v45_completo_final/
├── config.py              (URL da EM Moto)
├── main.py                (Import do scraper)
└── scrapers/
    └── emmoto.py          (Lógica de scraping)
```

---

## 🎓 PRÓXIMOS PASSOS

1. **Testar** com o teu feed real:
   ```bash
   python main.py --stores emmoto --max 10 --headful
   ```

2. **Validar** os resultados no Excel gerado

3. **Ajustar** se necessário:
   - Timeouts em `config.py`
   - Seletores no scraper se o site mudar

4. **Executar** comparação completa:
   ```bash
   python main.py
   ```

---

**Tudo pronto para usar! 🚀**
