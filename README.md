# Yato — uma IA local com personalidade

Projeto de estudo: uma IA de personalidade fixa (o **Yato**) rodando **100%
no meu PC**, de graça — sem API paga, sem nuvem, sem internet depois de
instalada. O "cérebro" é um modelo aberto servido pelo
[Ollama](https://ollama.com) na GPU.

O objetivo não é só usar IA: é **abrir a caixa-preta aos poucos** e entender,
na prática, como esses modelos funcionam — tokens, contexto, temperatura e a
geração palavra a palavra (que dá pra *ver*, porque as respostas chegam em
streaming).

## Os dois projetos deste repositório

Mesma ideia, duas interfaces — na ordem em que foram construídas:

| Pasta        | O que é                                                    | Cérebro |
| ------------ | ---------------------------------------------------------- | ------- |
| `yato-mini/` | A primeira versão: chat **web** em React + Vite             | `gemma3:4b` |
| `yato-py/`   | A versão atual: **app de desktop** em Python + CustomTkinter — com laboratório de ML (temperatura e métricas), streaming e conversa salva entre sessões | `qwen2.5:7b` |

Cada pasta tem seu próprio README com instruções de instalação e uso.

## Arquitetura (igual nas duas versões)

```
interface (React ou janela Python)
        │ HTTP local
        ▼
Ollama em http://localhost:11434
        ▼
modelo aberto rodando na GPU
```

A interface conversa com o Ollama como conversaria com uma API na internet —
só que tudo acontece dentro da máquina.

## Requisitos

- [Ollama](https://ollama.com/download) instalado e aberto
- Modelo baixado (uma vez só):
  - `ollama pull qwen2.5:7b` (~4,7 GB) para o `yato-py`
  - `ollama pull gemma3:4b` (~3 GB) para o `yato-mini`
- GPU com ~6 GB+ de VRAM livres (testado numa RTX 4060 Ti de 8 GB)
