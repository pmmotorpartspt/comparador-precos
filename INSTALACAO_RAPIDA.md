# ⚡ INSTALAÇÃO RÁPIDA - 3 PASSOS

## 1️⃣ INSTALAR PYTHON & DEPENDÊNCIAS

### **Verifica Python:**
```powershell
python --version
```
Precisa ser 3.8 ou superior.

### **Instala dependências:**
```powershell
pip install selenium openpyxl beautifulsoup4 lxml webdriver-manager
```

---

## 2️⃣ CONFIGURAR FEED

### **Opção A: Feed na mesma pasta**
Coloca `feed.xml` na pasta do projeto. Pronto!

### **Opção B: Feed noutro sítio**
Edita `config.py` linha 11:
```python
BASE_DIR = Path(r"C:\TUA_PASTA")
```

---

## 3️⃣ EXECUTAR

### **Teste rápido (5 produtos, ver Chrome):**
```powershell
python main.py --stores wrs --max 5 --headful
```

### **Execução completa:**
```powershell
python main.py
```

### **Resultado:**
Excel gerado em: `output/comparador_todas_lojas.xlsx`

---

## ✅ PRONTO!

**Deu erro?** Ver README.md secção "Resolução de Problemas"

**Funciona?** 🎉 Analisa o Excel:
- 🟢 VERDE = Estás a ganhar (loja mais cara)
- 🔴 VERMELHO = Atenção (loja mais barata)
- ⚫ CINZA = Produto não encontrado

---

## 🔧 COMANDOS ÚTEIS

```powershell
# Ver opções
python main.py --help

# Só algumas lojas
python main.py --stores wrs omniaracing --max 10

# Limpar cache
python main.py --refresh

# Ver todas as lojas
python main.py --stores wrs omniaracing genialmotor jbsmotos mmgracingstore
```

---

**Dúvidas?** Lê o README.md completo!
