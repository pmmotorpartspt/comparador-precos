# 🚀 QUICK START - EM MOTO

## ✅ RESUMO RÁPIDO

A loja **EM Moto** foi integrada com sucesso!

### **Como usar:**

```bash
# Testar só EM Moto (5 produtos, Chrome visível)
python main.py --stores emmoto --max 5 --headful

# EM Moto + outras lojas
python main.py --stores emmoto wrs omniaracing

# Todas as lojas (incluindo EM Moto)
python main.py
```

---

## 📋 CHECKLIST

Antes de executar:

- [x] ✅ Scraper criado (`scrapers/emmoto.py`)
- [x] ✅ Config atualizado (`config.py`)
- [x] ✅ Main.py atualizado
- [x] ✅ Documentação criada
- [x] ✅ Script de teste criado

---

## 🧪 TESTAR RAPIDAMENTE

```bash
# Teste individual de uma referência
python test_emmoto.py H.094.L4K

# Teste com o feed completo (primeiros 3)
python main.py --stores emmoto --max 3 --headful
```

---

## 📚 DOCUMENTAÇÃO

- `EM_MOTO_INTEGRACAO.md` - Guia completo da integração
- `README.md` - Guia geral do comparador
- `CHANGELOG.md` - Histórico de versões (v4.6)

---

## ⚡ DIFERENÇAS DA EM MOTO

**Vantagens:**
- ✅ Pesquisa super rápida (URL direta)
- ✅ Site Magento bem estruturado
- ✅ Preços claros e fáceis de extrair
- ✅ Suporta preços promocionais

**Particularidades:**
- Usa `/en/catalogsearch/result/?q=REF` para pesquisar
- Extrai SKU do atributo `data-product-sku`
- Preços em euros (€)

---

**Tudo pronto! Bom trabalho! 🎉**
