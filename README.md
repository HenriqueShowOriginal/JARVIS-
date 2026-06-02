# JARVIS — Assistente Pessoal de IA

Pressione **Alt+Space** (ou fale "Jarvis") — a janela aparece. Peça qualquer coisa. O JARVIS executa.

## O que ele faz

| Capacidade | Exemplos |
|------------|----------|
| **Abre apps** | "Abre o Spotify", "Abre o VS Code" |
| **Navega na web** | "Pesquisa X no Google", "Abre o YouTube" |
| **Controla o PC** | "Volume 50%", "Tira um print da tela" |
| **Cria arquivos** | "Cria um arquivo de ideias no desktop" |
| **Lê arquivos** | "Lê o arquivo config.txt" |
| **Executa comandos** | "Quanto espaço tem no disco?" |
| **Lembra coisas** | "Lembra que minha pasta de projetos é C:\Projetos" |
| **Se auto-atualiza** | Baixa melhorias automaticamente do GitHub |

## Instalação

```bash
# 1. Clone
git clone https://github.com/HenriqueShowOriginal/JARVIS-
cd JARVIS-

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edite o .env — só precisa da ANTHROPIC_API_KEY obrigatoriamente

# 4. Inicie
python main.py
```

## Configuração mínima (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...   # obrigatório — anthropic.com
USER_NAME=SeuNome              # como o JARVIS te chama
```

## Atalhos e ativação

- **Alt+Space** — abre/fecha a janela
- **"Jarvis"** (falar) — abre e já começa a ouvir
- **Enter** — envia mensagem
- **Shift+Enter** — nova linha
- **🎤** — gravar por voz manualmente

## Memória inteligente (economia de espaço)

O banco de dados é **SQLite ultra-leve**:
- Máximo 500 mensagens guardadas
- Mensagens antigas são comprimidas em resumos automaticamente
- Só os últimos 50 comportamentos aprendidos ficam guardados
- **Tamanho esperado: < 5MB mesmo após meses de uso**

## Estrutura

```
jarvis/
├── brain/ai.py          ← Claude AI com tools (loop agente)
├── gui/window.py        ← Janela flutuante moderna
├── voice/listener.py    ← Wake word + STT
├── voice/tts.py         ← Voz sintetizada (edge-tts)
├── tools/pc_tools.py    ← Controle do PC
├── memory/db.py         ← SQLite leve + auto-compressão
└── updater/updater.py   ← Auto-atualização via GitHub
```

## Auto-atualização

O JARVIS verifica automaticamente por novas versões a cada hora. Quando encontrar, avisa no chat:

> "Nova versão disponível. Digite 'atualizar' para instalar."

O processo baixa o código mais recente, instala dependências e reinicia sozinho.
