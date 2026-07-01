# Yato — uma IA local com personalidade

Projeto de estudo: uma IA de personalidade fixa (a **Yato**) rodando **100%
no meu PC**, de graça — sem API paga, sem nuvem, sem internet depois de
instalada. O "cérebro" é um modelo aberto (`gemma3:4b`) servido pelo
[Ollama](https://ollama.com) na GPU.

O objetivo não é só usar IA: é **abrir a caixa-preta aos poucos** e entender,
na prática, como esses modelos funcionam (tokens, contexto, temperatura,
geração palavra a palavra).

## Os dois projetos deste repositório

Mesma ideia, duas interfaces — na ordem em que foram construídas:

| Pasta        | O que é                                                       |
| ------------ | ------------------------------------------------------------- |
| `yato-mini/` | A primeira versão: chat **web** em React + Vite                |
| `yato-py/`   | A versão atual: **app de desktop** em Python + CustomTkinter   |

Cada pasta tem seu próprio README com instruções de instalação e uso.

## Arquitetura (igual nas duas versões)

```
interface (React ou janela Python)
        │ HTTP local
        ▼
Ollama em http://localhost:11434
        ▼
modelo gemma3:4b rodando na GPU
```

A interface conversa com o Ollama como conversaria com uma API na internet —
só que tudo acontece dentro da máquina.

## Requisitos

- [Ollama](https://ollama.com/download) instalado e aberto
- Modelo baixado: `ollama pull gemma3:4b` (~3 GB, uma vez só)
- GPU com ~4 GB+ de VRAM livres (testado numa RTX 4060 Ti 8 GB)
