# Yato Mini — o "cérebro" de uma VTuber IA

Uma IA de **personalidade fixa** (a "Yato") rodando 100% no seu PC:
um chat onde você conversa com ela e usa o projeto como **laboratório de
estudo** pra entender, na prática, como esses modelos funcionam por dentro.

> Foco do projeto: aprender. Sem stream, sem avatar — é uma ferramenta
> pessoal pra abrir a "caixa-preta" da IA aos poucos.

## Como funciona (arquitetura)

```
React (você digita)  →  Ollama em http://localhost:11434  →  resposta volta
     (frontend)           (a IA rodando no SEU PC)
```

O cérebro é **100% local e gratuito**: o [Ollama](https://ollama.com) roda
modelos de IA de código aberto direto na sua GPU e abre um servidor HTTP
local. O React faz `fetch` pra ele igual faria pra uma API na internet —
mas nada sai da sua máquina: sem chave de API, sem custo, sem internet
(depois de baixar o modelo).

## Estrutura de pastas

```
yato-mini/
├── index.html              # ponto de entrada do HTML
├── package.json            # dependências e scripts (na raiz, padrão)
├── vite.config.js          # config do Vite
├── .gitignore              # ignora node_modules etc.
└── src/                    # TODO o código-fonte do app
    ├── main.jsx            # liga o React no HTML
    ├── App.jsx             # componente raiz
    ├── personality.js      # a PERSONALIDADE da Yato (system prompt)
    ├── components/
    │   └── Chat.jsx        # o chat (estado, envio, chamada ao Ollama)
    └── styles/             # CSS sempre separado, nunca dentro do .jsx
        ├── App.css
        └── Chat.css
```

> As pastas `supabase/` e o `.env.example` eram da versão antiga (proxy +
> API paga). Não são mais usadas — pode apagar quando quiser.

## Passo 1 — Instalar o cérebro (uma vez só)

1. Instale o [Ollama](https://ollama.com/download) (ou: `winget install Ollama.Ollama`).
2. Baixe o modelo da Yato (~3 GB, uma vez só):
   ```bash
   ollama pull gemma3:4b
   ```

O Ollama fica rodando no ícone perto do relógio do Windows e inicia junto
com o PC. Se fechar ele, a Yato "perde o cérebro" até abrir de novo.

### Trocando o modelo (opcional)

O modelo é uma constante no topo de `src/components/Chat.jsx`. Opções que
cabem bem numa GPU de 8 GB:

| Modelo            | Tamanho | Por que escolher                            |
| ----------------- | ------- | ------------------------------------------- |
| `gemma3:4b`       | ~3 GB   | Ótimo português, rápido — o padrão daqui    |
| `qwen2.5:7b`      | ~4,7 GB | Mais "esperto", um pouco mais lento         |
| `llama3.1:8b`     | ~4,9 GB | Clássico, bom equilíbrio geral              |

Baixe com `ollama pull <nome>` e troque a constante `MODELO`.

## Passo 2 — Rodar o app

```bash
npm install
npm run dev
```

Abre o endereço que aparecer no terminal e conversa com a Yato. Tudo
rodando na sua máquina, de graça. 🎉

## Próximas ideias (rumo: entender como a IA funciona)

- [ ] Salvar a conversa (memória) entre sessões
- [ ] Deslizadores pra mexer nos parâmetros do modelo (temperatura, etc.)
      e ver, ao vivo, o efeito no comportamento
- [ ] Mostrar na tela o que vai "por baixo": os tokens e o contexto enviado
- [ ] Trocar o Ollama por código que roda o modelo direto (ver as engrenagens)
