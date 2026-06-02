# JARVIS — AI Stream Assistant

IA adaptável para streams ao vivo na Twitch, com voz, moderação automática, jogos e inteligência que aprende com o streamer.

## Funcionalidades

- **Chat Inteligente** — Responde menções e perguntas usando Claude AI
- **TTS (Voz)** — Fala respostas em tempo real com vozes neurais
- **Moderação Automática** — Detecta spam, caps, linguagem inapropriada
- **Trivia** — Mini-jogo de perguntas e respostas no chat
- **Auto-aprendizado** — Aprende tópicos, preferências e contexto da stream
- **Eventos** — Reage a follows, subs, raids e bits

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/henriqueshoworiginal/jarvis-
cd jarvis-

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure o ambiente
cp .env.example .env
# Edite o .env com suas chaves

# 4. Inicie o JARVIS
python main.py
```

## Configuração (.env)

| Variável | Descrição |
|----------|-----------|
| `ANTHROPIC_API_KEY` | Chave da API do Claude (anthropic.com) |
| `TWITCH_BOT_TOKEN` | Token OAuth do bot (twitchapps.com/tmi) |
| `TWITCH_CLIENT_ID` | Client ID do app Twitch |
| `TWITCH_BOT_NICK` | Nome do bot na Twitch |
| `TWITCH_CHANNELS` | Canal(is) para monitorar |
| `TTS_VOICE` | Voz TTS (padrão: pt-BR-FranciscaNeural) |
| `STREAMER_NAME` | Seu nome |
| `AUTO_MODERATION` | Ativar moderação automática (true/false) |

## Comandos do Chat

| Comando | Descrição |
|---------|-----------|
| `!jarvis <pergunta>` | Faz uma pergunta ao JARVIS |
| `!trivia [categoria]` | Inicia uma rodada de trivia |
| `!resposta <resposta>` | Responde à trivia ativa |
| `!pular` | Pula a trivia atual |
| `!ranking` | Mostra o ranking de trivia |
| `!voz <tipo>` | Muda a voz (mods) |
| `!contexto <texto>` | Define contexto da stream (mods) |
| `!aprenda <info>` | Ensina algo ao JARVIS (broadcaster) |
| `@jarvis <mensagem>` | Menciona o JARVIS diretamente |

## Vozes Disponíveis

- `pt-BR-feminino` — Voz feminina brasileira
- `pt-BR-masculino` — Voz masculina brasileira
- `en-US-feminino` — Voz feminina americana
- `en-US-masculino` — Voz masculina americana
- `jarvis` — Voz estilo JARVIS clássico

## Arquitetura

```
src/
├── ai/           # Cérebro do JARVIS (Claude AI)
├── twitch/       # Bot da Twitch
├── tts/          # Síntese de voz
├── moderation/   # Moderação automática
├── games/        # Trivia e jogos
└── memory/       # Banco de dados e aprendizado
```
