"""
AS FERRAMENTAS — as "mãos" do Yato.

Conceito central de agentes de IA: o modelo NÃO executa nada. Ele só
DECIDE ("preciso buscar X") e devolve um pedido estruturado; quem executa
é este código Python comum. O modelo pensa; o Python age.

Cada ferramenta tem duas partes:
  1. A função Python de verdade (que faz o trabalho);
  2. A "ficha técnica" (schema) que o MODELO lê pra decidir quando usar.
     A description é a parte mais importante: é ela que ensina o modelo a
     usar a ferramenta na hora certa — nem demais, nem de menos.
"""

import logging

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

# Teto de texto devolvido por página lida. Por quê: a "mesa" do modelo tem
# 8192 tokens no total — uma página inteira de portal facilmente passa disso
# sozinha e expulsaria a conversa. ~6000 caracteres ≈ 1500-2000 tokens: cabe
# a leitura E sobra mesa pro resto.
MAX_CARACTERES_PAGINA = 6000


def buscar_web(termo, max_resultados=4):
    """Busca no DuckDuckGo e devolve os melhores resultados como texto.

    Se a busca FALHAR (sem internet, limite de uso), devolvemos o erro COMO
    TEXTO pro modelo — assim ele avisa o usuário com jeito, em vez de o app
    quebrar. Falha de ferramenta não é falha do cérebro.
    """
    try:
        resultados = DDGS().text(termo, region="br-pt", max_results=max_resultados)
        if not resultados:
            return "(A busca não retornou nenhum resultado.)"
        return "\n\n".join(
            f"[{r['title']}]\n{r['body']}\nFonte: {r['href']}"
            for r in resultados
        )
    except Exception as erro:
        logging.warning("Busca na web falhou: %s", erro)
        return (
            "(A busca na web FALHOU — provavelmente falta de internet ou "
            "limite de uso. Avise o usuário disso e responda com o que "
            "você já souber, deixando claro que pode estar desatualizado.)"
        )


def ler_pagina(url):
    """Abre uma página da web e devolve só o TEXTO legível dela.

    O trabalho de verdade aqui é a LIMPEZA: uma página crua é 90% HTML de
    layout (menus, scripts, propaganda). O BeautifulSoup tira o código e
    sobra o conteúdo — que ainda é cortado no teto pra caber na "mesa".
    """
    try:
        resposta = requests.get(
            url,
            timeout=15,
            # Alguns sites recusam pedidos "sem identidade"; este cabeçalho
            # nos apresenta como um navegador comum.
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        resposta.raise_for_status()
        sopa = BeautifulSoup(resposta.text, "html.parser")
        # scripts/estilos não são conteúdo — fora antes de extrair o texto
        for lixo in sopa(["script", "style", "noscript"]):
            lixo.decompose()
        texto = " ".join(sopa.get_text(separator=" ").split())
        if not texto:
            return "(A página abriu mas não tem texto legível.)"
        if len(texto) > MAX_CARACTERES_PAGINA:
            texto = texto[:MAX_CARACTERES_PAGINA] + " (...página cortada aqui...)"
        return texto
    except Exception as erro:
        logging.warning("Leitura de página falhou (%s): %s", url, erro)
        return (f"(Não consegui abrir a página {url} — site fora do ar, "
                "bloqueio ou endereço inválido. Tente outra fonte ou avise "
                "o usuário.)")


# A ficha técnica, no formato padrão (JSON Schema) que a API entende.
# É ISTO que o modelo lê a cada mensagem pra decidir se busca ou não.
FERRAMENTAS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_web",
            "description": (
                "Busca informações ATUAIS na internet: notícias, preços, "
                "cotações, resultados de jogos, lançamentos e eventos "
                "recentes — qualquer fato que pode ter mudado depois do seu "
                "treino. NÃO use para conversa casual nem para conhecimento "
                "estável (conceitos, história, programação)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "O que buscar, direto e em poucas palavras",
                    }
                },
                "required": ["termo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ler_pagina",
            "description": (
                "Abre uma página da web (URL) e devolve o texto dela. Use "
                "DEPOIS de buscar_web, quando os resuminhos da busca não "
                "contêm a resposta e ela deve estar DENTRO de uma das "
                "páginas (listas, tabelas, artigos). Escolha a URL mais "
                "promissora dos resultados da busca."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "O endereço completo da página (http...)",
                    }
                },
                "required": ["url"],
            },
        },
    },
]

# Mapa nome -> função. Ferramenta nova = escrever a função, a ficha
# técnica acima, e ligar aqui. Três passos, sempre.
_EXECUTORES = {
    "buscar_web": buscar_web,
    "ler_pagina": ler_pagina,
}


def descrever(nome, argumentos):
    """Frase curta do que a ferramenta está fazendo — pro aviso na tela."""
    if nome == "buscar_web":
        return f"buscando na web: {argumentos.get('termo', '?')}"
    if nome == "ler_pagina":
        return f"lendo a página: {argumentos.get('url', '?')[:60]}"
    return f"usando {nome}"


def executar(nome, argumentos):
    """Executa a ferramenta que o modelo pediu — com rede de proteção.

    O modelo pode alucinar um nome de ferramenta que não existe ou mandar
    argumentos errados. Nunca confie cegamente: devolvemos o problema como
    texto pra ele se corrigir, em vez de deixar o app explodir.
    """
    funcao = _EXECUTORES.get(nome)
    if funcao is None:
        return f"(Ferramenta desconhecida: {nome})"
    try:
        return funcao(**argumentos)
    except TypeError:
        return f"(Argumentos inválidos para {nome}: {argumentos})"
