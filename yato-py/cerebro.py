"""
O CÉREBRO — a parte que conversa com a IA local (Ollama).

Repare que aqui NÃO existe nada de janela/botão. É de propósito: a lógica de
"falar com a IA" fica separada da interface (que está em app.py). Vantagens:
  - dá pra testar o cérebro sozinho, sem abrir a janela (veja o final do arquivo);
  - no futuro, se você trocar o Ollama por outra coisa, mexe só aqui.
"""

import requests

# Endereço do Ollama na SUA máquina. O Ollama abre esse "servidorzinho" local
# enquanto está aberto (ícone perto do relógio do Windows).
OLLAMA_URL = "http://localhost:11434/api/chat"

# Qual modelo usar. Precisa estar baixado antes: `ollama pull gemma3:4b`.
# Trocar de modelo = trocar este nome.
MODELO = "gemma3:4b"


def pensar(mensagens):
    """Manda a conversa pro Ollama e devolve o TEXTO da resposta da IA.

    `mensagens` é uma lista no formato que a IA entende. Exemplo:
        [
            {"role": "system",    "content": "você é a Yato..."},
            {"role": "user",      "content": "oi"},
            {"role": "assistant", "content": "e aí, sumido!"},
            {"role": "user",      "content": "tudo bem?"},
        ]

    Detalhe-chave de como a IA funciona: ela NÃO tem memória entre chamadas.
    Cada chamada é uma folha em branco pra ela. Por isso mandamos a conversa
    INTEIRA toda vez — é isso que cria a ilusão de que ela "lembra".
    """
    resposta = requests.post(
        OLLAMA_URL,
        json={
            "model": MODELO,
            "stream": False,   # a resposta inteira de uma vez (sem ser letra a letra)
            "messages": mensagens,
            # Mantém o modelo carregado na memória por 10 min após a última
            # conversa. Sem isso, ele sai da memória rápido e CADA mensagem
            # paga de novo o carregamento (lento). Com isso, só a 1ª demora.
            "keep_alive": "10m",
        },
        # Generoso de propósito: a PRIMEIRA chamada depois de ligar o PC inclui
        # o carregamento do modelo na placa de vídeo, o que pode levar 1-3 min.
        # As próximas (com o modelo já na memória) respondem em segundos.
        timeout=300,
    )
    resposta.raise_for_status()                 # erro HTTP vira exceção aqui
    return resposta.json()["message"]["content"].strip()


# ---------------------------------------------------------------------------
# TESTE RÁPIDO (sem janela):
#   abra o terminal na pasta e rode  ->  python cerebro.py
# Serve pra confirmar que o Ollama está no ar e respondendo.
# Este bloco só roda quando você executa ESTE arquivo direto.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    # O terminal do Windows usa uma codificação antiga (cp1252) que não imprime
    # emojis. Isto força UTF-8 só na hora de imprimir, pra não quebrar o teste.
    # (Na janela gráfica do app.py isso não é necessário — Tkinter já lida bem.)
    sys.stdout.reconfigure(encoding="utf-8")

    from personalidade import PERSONALIDADE

    conversa = [
        {"role": "system", "content": PERSONALIDADE},
        {"role": "user", "content": "oi, se apresenta rapidinho"},
    ]
    print("Pensando... (a 1ª resposta após ligar o PC demora um pouco)\n")
    print("Yato:", pensar(conversa))
