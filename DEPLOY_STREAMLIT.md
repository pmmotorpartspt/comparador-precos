# 🚀 GUIA COMPLETO - Deploy no Streamlit Cloud

**Versão Web do Comparador de Preços**  
**Tempo estimado:** 15-20 minutos (só primeira vez)  
**Custo:** €0 (100% gratuito para sempre)

---

## 📋 O QUE VAIS TER

Uma aplicação web bonita acessível em qualquer lugar:
- 🌐 URL tipo: `https://comparador-precos.streamlit.app`
- 📱 Funciona em PC, tablet, telemóvel
- 🎨 Interface moderna e intuitiva
- ☁️ Hospedada gratuitamente
- 🔄 Atualiza automaticamente quando mudas código

---

## ✅ PRÉ-REQUISITOS

1. ✅ Conta Gmail/Google (que já tens)
2. ✅ Este projeto (já tens!)
3. ✅ 15 minutos de tempo

**Não precisas de:**
- ❌ Instalar Python
- ❌ Instalar nada no teu PC
- ❌ Saber programação web
- ❌ Pagar nada

---

## 📍 PASSO A PASSO

### **PASSO 1: Criar Conta GitHub** (5 min)

#### 1.1 Ir para GitHub
```
https://github.com
```

#### 1.2 Clicar "Sign up" (canto superior direito)

#### 1.3 Preencher:
- **Email:** O teu email
- **Password:** Senha segura
- **Username:** Escolhe um nome (ex: pmmotorparts)

#### 1.4 Verificar email
- GitHub envia email de confirmação
- Clica no link para verificar

✅ **Pronto!** Tens conta GitHub

---

### **PASSO 2: Upload do Código** (5 min)

#### 2.1 Criar novo repositório

1. Depois de fazer login, clica no "**+**" (canto superior direito)
2. Seleciona "**New repository**"

#### 2.2 Configurar repositório

Preenche:
- **Repository name:** `comparador-precos` (ou outro nome)
- **Description:** `Comparador de preços multi-loja` (opcional)
- **Visibilidade:** 
  - ✅ **Public** (recomendado - funciona com Streamlit grátis)
  - ⚠️ Private (precisa Streamlit pago)
- **Initialize:** ☐ Não marcar nada

3. Clica "**Create repository**"

#### 2.3 Upload dos ficheiros

**Opção A: Interface Web (FÁCIL)**

1. Na página do repositório criado, clica "**uploading an existing file**"
2. Arrasta TODOS os ficheiros do projeto:
   ```
   app_streamlit.py
   requirements.txt
   config.py
   main.py
   test_emmoto.py
   feed_EXEMPLO.xml
   + pastas: core/, scrapers/, .streamlit/
   + docs: README.md, CHANGELOG.md, etc
   ```
3. Escreve uma mensagem: "Upload inicial"
4. Clica "**Commit changes**"

**Opção B: GitHub Desktop (SE PREFERIRES)**

1. Download GitHub Desktop: https://desktop.github.com/
2. Login com tua conta
3. Clone o repositório
4. Copia ficheiros para a pasta
5. Commit and Push

✅ **Pronto!** Código está no GitHub

---

### **PASSO 3: Deploy no Streamlit Cloud** (5 min)

#### 3.1 Ir para Streamlit Cloud
```
https://streamlit.io/cloud
```

#### 3.2 Login

- Clica "**Sign up**" ou "**Sign in**"
- Escolhe "**Continue with GitHub**"
- Autoriza Streamlit a aceder ao GitHub

#### 3.3 Criar nova app

1. Clica "**New app**" (botão grande no centro ou canto superior direito)

2. Preenche:
   - **Repository:** Seleciona `teu-username/comparador-precos`
   - **Branch:** `main` (ou `master`)
   - **Main file path:** `app_streamlit.py` ⚠️ IMPORTANTE
   - **App URL (optional):** Escolhe URL personalizado
     - Ex: `comparador-pm` → `comparador-pm.streamlit.app`

3. Clica "**Advanced settings**" (opcional):
   - **Python version:** 3.11
   - **Secrets:** Deixar vazio (não precisas)

4. Clica "**Deploy!**"

#### 3.4 Aguardar deploy

- Streamlit vai:
  1. ✅ Ler o código do GitHub
  2. ✅ Instalar dependências (requirements.txt)
  3. ✅ Iniciar a aplicação
  
- **Tempo:** 2-5 minutos
- **Progresso:** Vês os logs em tempo real

#### 3.5 Pronto! 🎉

Quando terminar, vês a tua aplicação live:
```
https://comparador-pm.streamlit.app
```

✅ **Funcionou!** Aplicação web está online!

---

## 🎨 COMO USAR A APLICAÇÃO WEB

### **Interface Principal:**

1. **📁 Upload Feed XML**
   - Arrasta ficheiro feed.xml
   - Ou clica para selecionar

2. **⚙️ Sidebar (esquerda):**
   - 🏪 Seleciona lojas (por defeito: todas)
   - 📊 Limitar produtos (0 = todos)
   - 💾 Usar cache (recomendado)
   - 👁️ Modo invisível (recomendado)

3. **🚀 Botão "Comparar Preços"**
   - Clica e aguarda
   - Vês progresso em tempo real

4. **📥 Download Excel**
   - Quando terminar, clica "Download Excel"
   - Ficheiro pronto com comparação!

---

## 🔧 CONFIGURAÇÕES AVANÇADAS

### **Alterar Configurações**

Se quiseres mudar algo (ex: timeouts, URLs):

1. Edita `config.py` no GitHub:
   - Vai ao repositório
   - Clica em `config.py`
   - Clica no ✏️ (Edit)
   - Faz mudanças
   - Commit changes

2. **Streamlit atualiza automaticamente!**
   - Em 1-2 minutos, mudanças estão live
   - Não precisas fazer nada

### **Ver Logs (Debug)**

Se algo der errado:

1. Vai ao dashboard Streamlit Cloud
2. Clica na tua app
3. Clica "**Manage app**"
4. Vê logs completos
5. "**Reboot app**" se necessário

---

## 💡 DICAS IMPORTANTES

### **✅ Fazer:**
- Usa para comparar até ~100 produtos por vez
- Deixa cache ativado (muito mais rápido)
- Partilha URL com colegas/equipa

### **⚠️ Atenção:**
- Chrome tem de estar instalado no servidor Streamlit (já está ✅)
- Primeira execução é lenta (cache vazio)
- Streamlit pode adormecer se não usar (acorda automático)

### **🚫 Limitações:**
- **Timeout:** Streamlit limita execução a ~30 min
  - Para feeds grandes (500+ produtos), fazer em partes
- **Memória:** 1GB RAM grátis
  - Suficiente para maioria dos casos
- **Uptime:** App pode adormecer após 7 dias sem uso
  - Acorda automaticamente quando acedes

---

## 🔄 ATUALIZAR A APLICAÇÃO

Quando quiseres atualizar código:

### **Método 1: GitHub Web**

1. Vai ao repositório GitHub
2. Clica no ficheiro que queres editar
3. Clica ✏️ (Edit)
4. Faz mudanças
5. "Commit changes"
6. **Streamlit atualiza sozinho em 1-2 min!**

### **Método 2: GitHub Desktop**

1. Edita ficheiros localmente
2. Commit no GitHub Desktop
3. Push
4. **Streamlit atualiza automático!**

---

## 📊 MONITORIZAÇÃO

### **Ver Estatísticas:**

Streamlit Cloud mostra:
- 👥 Quantas pessoas usaram
- 📈 Quando foi usado
- 🕐 Tempo de execução
- 💾 Uso de recursos

Acede em: https://share.streamlit.io/

---

## 🆘 TROUBLESHOOTING

### **App não abre**
```
Solução:
1. Verifica se deploy terminou (logs)
2. Aguarda 5 minutos
3. Reboot app no dashboard
```

### **"ModuleNotFoundError"**
```
Solução:
1. Verifica requirements.txt
2. Tem todas as dependências?
3. Faz commit de novo
```

### **TimeoutError no scraping**
```
Solução:
1. Reduz número de produtos
2. Usa cache
3. Tenta em horário diferente
```

### **App adormeceu**
```
Solução:
- Normal! Acorda automaticamente quando acedes
- Primeiro acesso pode demorar 30s
```

---

## 💰 CUSTOS

### **Streamlit Cloud (Gratuito):**
- ✅ 1 app pública
- ✅ 1GB RAM
- ✅ 1GB storage
- ✅ Community support

**Para ti é suficiente!**

### **Se precisares mais (futuro):**
- **Starter:** $20/mês
  - 3 apps privadas
  - 2GB RAM
  - Email support

**Mas começa com grátis!**

---

## 🎯 PRÓXIMOS PASSOS

Depois de deploy:

1. ✅ **Testa** a aplicação
2. ✅ **Partilha** URL com equipa
3. ✅ **Usa** regularmente para comparações
4. ✅ **Ajusta** conforme necessário

---

## 📱 ACESSO MÓVEL

A app funciona perfeitamente em:
- 📱 iPhone/Android
- 💻 PC/Mac
- 📲 Tablet

Só aceder ao URL!

---

## 🔗 LINKS ÚTEIS

- **Streamlit Cloud:** https://streamlit.io/cloud
- **Documentação:** https://docs.streamlit.io/
- **Comunidade:** https://discuss.streamlit.io/
- **GitHub:** https://github.com/

---

## ✅ CHECKLIST FINAL

Antes de começar, confirma:

- [ ] Conta Google/GitHub criada
- [ ] Código no GitHub
- [ ] Streamlit Cloud conectado
- [ ] App deployed com sucesso
- [ ] Feed XML testado
- [ ] Resultado Excel download OK

---

## 🎉 PARABÉNS!

Tens agora uma **aplicação web profissional** para comparação de preços!

**URL exemplo:** `https://comparador-pm.streamlit.app`

**Características:**
- ✅ Interface bonita
- ✅ 100% gratuito
- ✅ Funciona em qualquer dispositivo
- ✅ Zero manutenção
- ✅ Atualiza automaticamente

---

**Dúvidas?** Consulta a documentação ou pergunta! 😊

**Versão:** 4.6 Web  
**Data:** Novembro 2025  
**Status:** ✅ Pronto para deploy
