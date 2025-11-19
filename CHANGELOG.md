# 📋 CHANGELOG - Histórico de Versões

## v4.6 (Novembro 2025) - NOVA LOJA: EM MOTO 🆕

### **Adições:**
- ✅ **NOVA LOJA:** EM Moto (em-moto.com)
  - Site Magento com pesquisa direta por URL
  - Extração robusta de preços (5 métodos)
  - Validação por SKU e códigos na página
  - Suporte completo para preços promocionais

### **Ficheiros criados:**
- `scrapers/emmoto.py` - Scraper completo para EM Moto
- `test_emmoto.py` - Script de teste rápido
- `EM_MOTO_INTEGRACAO.md` - Documentação da integração

### **Ficheiros modificados:**
- `config.py` - Adicionada URL da EM Moto
- `main.py` - Registado novo scraper

### **Como usar:**
```bash
# Só EM Moto
python main.py --stores emmoto

# EM Moto + outras lojas
python main.py --stores emmoto wrs omniaracing

# Todas (incluindo EM Moto)
python main.py
```

### **Total de Lojas:**
6 lojas funcionais: WRS, OmniaRacing, GenialMotor, JBS Motos, MMG Racing, **EM Moto**

---

## v4.5 (Novembro 2025) - CORREÇÕES CRÍTICAS ✅

### **Correções:**
- ✅ **EXCEL:** Cálculo de diferença % corrigido
  - **ANTES:** `(teu_preço - loja) / loja` → cores invertidas
  - **AGORA:** `(loja - teu_preço) / teu_preço` → cores corretas
  - Verde = loja mais cara (ganhas)
  - Vermelho = loja mais barata (perdes)

- ✅ **FEED PARSING:** Sistema de extração de refs completo
  - Lê refs do campo `<g:description>`
  - Padrões: "Ref Fabricante:", "Ref. Fabricante:", "Ref do Fabricante:"
  - Suporte para refs simples e compostas (com +)

- ✅ **NORMALIZATION:** Módulo completo
  - `extract_ref_from_description()` - extrai refs da description
  - `normalize_ref()` - normaliza referências
  - `norm_token()` - remove caracteres especiais
  - Suporte para refs com hífens, pontos, espaços

### **Ficheiros modificados:**
- `core/excel.py` - Linha 124: cálculo corrigido
- `core/feed.py` - Sistema completo de parsing
- `core/normalization.py` - Todas as funções necessárias

### **Teste de verificação:**
```python
# Exemplo: Teu preço €100, Loja €120
# Cálculo: (120 - 100) / 100 = 0.20 = +20%
# Resultado: VERDE ✅ (loja mais cara, ganhas)

# Exemplo: Teu preço €100, Loja €80
# Cálculo: (80 - 100) / 100 = -0.20 = -20%
# Resultado: VERMELHO ⚠️ (loja mais barata, perdes)
```

---

## v4.4 (Novembro 2025)
- Adicionada loja MMG Racing Store
- 5 lojas funcionais

---

## v4.3 (Novembro 2025)
- Adicionada loja JBS Motos
- 4 lojas funcionais
- Sistema de cache com TTL

---

## v4.2 (Novembro 2025)
- Correção WRS (sistema SniperFast)
- Refs com hífens mantidos na pesquisa
- Cache TTL implementado:
  - Encontrado: 10 dias
  - Não encontrado: 4 dias

---

## v4.1 (Outubro 2025)
- Sistema base estável
- 3 lojas: WRS, OmniaRacing, GenialMotor
- Validação de produtos
- Excel com cores condicionais

---

## 🐛 BUGS CORRIGIDOS

### **v4.5:**
1. ❌ **Cores invertidas no Excel**
   - **Problema:** Verde aparecia quando loja era mais barata (errado!)
   - **Solução:** Invertido cálculo da diferença %

2. ❌ **Feed não encontrava refs**
   - **Problema:** Procurava em `<mpn>`, `<sku>` que não existem
   - **Solução:** Sistema de extração do campo `<g:description>`

3. ❌ **Ficheiros core/ em falta**
   - **Problema:** v4.4 não tinha feed.py completo
   - **Solução:** Todos os ficheiros incluídos e testados

---

## 📊 COMPARAÇÃO DE VERSÕES

| Feature | v4.1 | v4.2 | v4.3 | v4.4 | v4.5 | v4.6 |
|---------|------|------|------|------|------|------|
| Lojas | 3 | 3 | 4 | 5 | 5 | 6 |
| Cache TTL | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Refs com hífen | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Extrai refs description | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Excel cores corretas | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ |
| Completo e portátil | ❌ | ❌ | ❌ | ⚠️ | ✅ | ✅ |
| EM Moto | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 🎯 PRÓXIMAS MELHORIAS (Futuro)

- [ ] Interface gráfica (GUI)
- [ ] Mais lojas europeias
- [ ] Alertas de preço por email
- [ ] Dashboard web
- [ ] API REST

---

**Para mais info:** Ver README.md
