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

# Teto DURO de tokens por resposta. A personalidade já PEDE respostas curtas,
# mas modelo pequeno às vezes desobedece e dispara um textão. Defesa em
# camadas: a regra vale no pedido (prompt) E na infraestrutura (este número).
MAX_TOKENS_RESPOSTA = 300

# Quantas falas recentes o modelo enxerga (a personalidade não entra na conta).
# Por quê: o modelo só "vê" 4096 tokens por vez. Se mandássemos a conversa
# inteira pra sempre, o excedente seria cortado EM SILÊNCIO pelo Ollama — e o
# corte come do começo, onde mora a PERSONALIDADE. Nós decidimos o corte antes.
LIMITE_HISTORICO = 20


class CerebroError(Exception):
    """Erro já traduzido pra uma mensagem amigável, pronta pra mostrar na tela.

    A ideia: quem usa o cérebro (a janela) não precisa entender de HTTP.
    Aqui dentro descobrimos O QUE deu errado e entregamos o recado pronto.
    """


def _podar(mensagens):
    """Devolve: personalidade (system) + só as últimas N falas da conversa.

    O histórico completo continua guardado na janela (pra, no futuro, salvar
    em arquivo). Aqui a gente só decide o que o MODELO enxerga.
    """
    sistema = [m for m in mensagens if m["role"] == "system"]
    conversa = [m for m in mensagens if m["role"] != "system"]
    return sistema + conversa[-LIMITE_HISTORICO:]


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
    try:
        resposta = requests.post(
            OLLAMA_URL,
            json={
                "model": MODELO,
                "stream": False,   # a resposta inteira de uma vez (sem ser letra a letra)
                "messages": _podar(mensagens),   # o modelo só vê o que cabe na "mesa"
                # Mantém o modelo carregado na memória por 10 min após a última
                # conversa. Sem isso, ele sai da memória rápido e CADA mensagem
                # paga de novo o carregamento (lento). Com isso, só a 1ª demora.
                "keep_alive": "10m",
                # Ajustes passados direto pro MODELO (não pro servidor):
                "options": {
                    "num_predict": MAX_TOKENS_RESPOSTA,  # trava dura de tamanho
                },
            },
            # Generoso de propósito: a PRIMEIRA chamada depois de ligar o PC
            # inclui o carregamento do modelo na placa de vídeo (~20s, e até
            # minutos em casos ruins). As seguintes respondem em segundos.
            timeout=300,
        )
        resposta.raise_for_status()             # erro HTTP vira exceção aqui

    # ----- Tradução de erros: de "tecniquês" pra recado claro -----
    except requests.exceptions.ConnectionError:
        # Nem conseguiu conectar na porta 11434: o Ollama não está aberto.
        raise CerebroError("Meu cérebro tá desligado 💀 (abre o Ollama e tenta de novo)")
    except requests.exceptions.Timeout:
        # Conectou, mas a resposta não veio a tempo (modelo travado/sobrecarregado).
        raise CerebroError("Pensei, pensei... e deu branco 😵 Tenta de novo?")
    except requests.exceptions.HTTPError:
        if resposta.status_code == 404:
            # 404 aqui significa: o Ollama não achou o modelo pedido.
            raise CerebroError(
                f"Cadê meu cérebro?! O modelo '{MODELO}' não está baixado 🤔 "
                f"(no terminal: ollama pull {MODELO})"
            )
        raise CerebroError(f"O Ollama reclamou: erro {resposta.status_code} 😬")

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
