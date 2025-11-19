# 🌐 Comparador de Preços - VERSÃO WEB

**Interface Web Bonita + Deploy Gratuito**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)

---

## 🎯 DUAS VERSÕES DISPONÍVEIS

### **1. Versão Desktop** (main.py)
- Executa no teu PC
- Precisa Python instalado
- Mais controlo e configuração
- Ideal para uso local

### **2. Versão Web** ⭐ (app_streamlit.py)
- Interface web bonita
- **Zero instalação**
- Acesso de qualquer lugar
- **100% GRATUITO** (Streamlit Cloud)
- Ideal para partilhar com equipa

---

## 🚀 QUICK START - VERSÃO WEB

### **Opção A: Usar Localmente** (testar)

```bash
# Instalar Streamlit
pip install streamlit

# Executar
streamlit run app_streamlit.py
```

Abre automaticamente em: `http://localhost:8501`

### **Opção B: Deploy Online** (recomendado)

1. **GitHub:** Upload do código
2. **Streamlit Cloud:** Deploy automático (5 min)
3. **Pronto!** URL tipo: `comparador-pm.streamlit.app`

**Guia completo:** Ver `DEPLOY_STREAMLIT.md` 📖

---

## 🎨 INTERFACE WEB

### **Características:**

✅ **Upload Drag & Drop**
- Arrasta feed.xml para interface

✅ **Seleção Visual de Lojas**
- Checkboxes bonitos
- 6 lojas disponíveis

✅ **Barra de Progresso**
- Vê progresso em tempo real
- Status por loja

✅ **Estatísticas Visuais**
- Métricas coloridas
- Taxas de sucesso
- Performance do cache

✅ **Download Direto**
- Botão de download
- Excel gerado na hora

---

## 📱 FUNCIONA EM

- 💻 **Desktop:** Windows, Mac, Linux
- 📱 **Mobile:** iPhone, Android
- 📲 **Tablet:** iPad, etc
- 🌐 **Qualquer Browser:** Chrome, Firefox, Safari, Edge

---

## 💡 VANTAGENS DA VERSÃO WEB

| Feature | Desktop | Web |
|---------|---------|-----|
| **Instalação** | Python + deps | Zero |
| **Interface** | Terminal | Bonita GUI |
| **Acesso** | Local | Qualquer lugar |
| **Partilhar** | Difícil | Simples (URL) |
| **Atualizar** | Manual | Automático |
| **Custo** | €0 | €0 |
| **Mobile** | ❌ | ✅ |

---

## 🆚 QUANDO USAR CADA VERSÃO

### **Use Desktop (main.py) se:**
- ✅ Queres controlo total
- ✅ Processas feeds gigantes (1000+ produtos)
- ✅ Preferes linha de comandos
- ✅ Não tens internet estável

### **Use Web (app_streamlit.py) se:**
- ✅ Queres interface bonita
- ✅ Precisas aceder de vários locais
- ✅ Vais partilhar com equipa
- ✅ Não queres instalar nada
- ✅ Feeds médios (até ~500 produtos)

---

## 📦 FICHEIROS IMPORTANTES

### **Para Versão Web:**
```
app_streamlit.py       ← Aplicação web
requirements.txt       ← Dependências Python
packages.txt          ← Dependências sistema
.streamlit/config.toml ← Config Streamlit
DEPLOY_STREAMLIT.md   ← Guia de deploy
```

### **Para Versão Desktop:**
```
main.py               ← Aplicação terminal
config.py            ← Configurações
test_emmoto.py       ← Testes
README.md            ← Guia geral
```

### **Comuns (ambas usam):**
```
core/                ← Lógica principal
scrapers/           ← Scrapers das lojas
```

---

## 🎓 TUTORIAIS

### **1. Testar Localmente**

```bash
# Clonar/Download do projeto
cd comparador_v45_completo_final

# Instalar dependências
pip install -r requirements.txt

# Executar versão web
streamlit run app_streamlit.py

# Executar versão desktop
python main.py
```

### **2. Deploy Online**

Ver guia completo: **`DEPLOY_STREAMLIT.md`**

Resumo:
1. Conta GitHub (5 min)
2. Upload código (5 min)
3. Streamlit Cloud (5 min)
4. **Pronto!** 🎉

---

## ⚙️ CONFIGURAÇÕES

### **Versão Web:**

Configurações na **Sidebar** da interface:
- 🏪 Lojas a comparar
- 📊 Limite de produtos
- 💾 Usar cache
- 👁️ Modo invisível

### **Versão Desktop:**

Configurações em `config.py`:
- Paths de ficheiros
- Timeouts
- Rate limiting
- Cache TTL

---

## 🔧 DEPENDÊNCIAS

### **Python (requirements.txt):**
```
streamlit==1.29.0        # Framework web
selenium==4.15.0         # Scraping
beautifulsoup4==4.12.2   # Parsing HTML
openpyxl==3.1.2         # Excel
webdriver-manager==4.0.1 # Chrome driver
```

### **Sistema (packages.txt):**
```
chromium         # Browser
chromium-driver  # WebDriver
```

---

## 💰 CUSTOS

### **Streamlit Cloud (Grátis):**
- ✅ 1 app pública
- ✅ 1GB RAM
- ✅ 1GB storage
- ✅ Unlimited users
- ✅ Community support

**Suficiente para 95% dos casos!**

### **Se precisares mais:**
- Starter: $20/mês (apps privadas)
- Business: Custom (enterprise)

**Mas começa com grátis!**

---

## 📊 PERFORMANCE

### **Versão Desktop:**
- ⚡ Mais rápida
- 💪 Sem limites de recursos
- 🎯 Ideal para feeds grandes

### **Versão Web:**
- 🌐 Acessível de qualquer lugar
- 📱 Mobile-friendly
- ⏱️ Timeout 30 min (Streamlit)
- 💾 1GB RAM (grátis)

**Para 100-200 produtos: ambas iguais!**

---

## 🐛 TROUBLESHOOTING

### **"ModuleNotFoundError"**
```bash
# Instalar dependências
pip install -r requirements.txt
```

### **"Chrome not found"**
```bash
# Streamlit Cloud: adiciona packages.txt (já incluído)
# Local: instala Chrome
```

### **App lenta**
```
# Usa cache (ativa por defeito)
# Limita produtos (~100)
# Horários menos movimentados
```

---

## 🔗 LINKS ÚTEIS

- **Streamlit:** https://streamlit.io/
- **Documentação:** https://docs.streamlit.io/
- **Galeria:** https://streamlit.io/gallery
- **Comunidade:** https://discuss.streamlit.io/

---

## 📞 SUPORTE

**Versão Desktop:** Ver `README.md` principal

**Versão Web:** Ver `DEPLOY_STREAMLIT.md`

**Ambas:** Ver `CONTEXT_FOR_CLAUDE.md` (para Claude)

---

## 🎉 PRÓXIMOS PASSOS

1. ✅ Testa localmente: `streamlit run app_streamlit.py`
2. ✅ Se gostar, faz deploy (guia em `DEPLOY_STREAMLIT.md`)
3. ✅ Partilha URL com equipa
4. ✅ Usa regularmente

---

**Versão:** 4.6 Web  
**Data:** Novembro 2025  
**Autor:** PM Motorparts  
**Licença:** Privado

---

**Pronto para começar?** 🚀

Escolhe versão:
- **Desktop:** `python main.py`
- **Web:** `streamlit run app_streamlit.py`
