"""
O AVATAR 2D — Live2D numa janela flutuante (o "chefão", ainda POR CONSTRUIR).

╔════════════════════════════════════════════════════════════════════════╗
║  ESTE ARQUIVO É UM ESQUELETO / PLANO — NADA AQUI FUNCIONA AINDA.        ║
║  Ninguém importa este módulo por enquanto (app.py não depende dele),    ║
║  então ele não quebra o Yato. É o rascunho pra quando a gente encarar   ║
║  o avatar de verdade.                                                    ║
╚════════════════════════════════════════════════════════════════════════╝

A VISÃO
-------
Um personagem Live2D (que respira, pisca e mexe a boca) numa janelinha
própria, por cima da tela — estilo VTuber / mascote de desktop. Ele "fica
fora" da janela do chat e reage ao Yato: pensa quando o Yato pensa, fala
(boca mexendo) quando o Yato fala.

POR QUE ISSO É O "CHEFÃO" (a parte honesta)
-------------------------------------------
Live2D não tem um bom renderizador em Python puro. O jeito consolidado é
WEB: o SDK Cubism roda em JavaScript. Então o plano realista é:

  1. Uma página HTML local desenha o modelo Live2D com a lib JS
     `pixi-live2d-display` (em cima do PIXI.js).
  2. O Python abre essa página numa JANELA FLUTUANTE usando `pywebview`
     (uma janela de navegador enxuta, sem barra, sempre-no-topo).
  3. Python ↔ JavaScript conversam: o Python manda "expressão = falando"
     e a página aplica no modelo.

Ou seja: aqui o projeto deixa de ser "100% Python sem web". É uma escolha
consciente — o resultado (um avatar de verdade) vale o custo. Enquanto isso
não existe, o modo Avatar usa o PNGTuber de imagens (reserva) que já temos.

O QUE PRECISA (quando for a hora)
---------------------------------
  • Um modelo Live2D (.model3.json + texturas + physics). Fontes: a loja
    oficial da Live2D, ou modelos gratuitos "for personal use". (O nosso
    Yato hoje é uma imagem única — pra Live2D ele precisaria ser RIGGADO,
    separado em camadas: cabelo, olhos, boca… Isso é um trabalho de arte à
    parte, feito em softwares como o Live2D Cubism.)
  • pip install pywebview            (a janela flutuante)
  • pixi-live2d-display + pixi.js    (no lado da página HTML)
  • Cubism Core (runtime oficial da Live2D pra web)

O CONTRATO (o que o app.py vai chamar)
--------------------------------------
O motor de estados JÁ existe no app: _expressao(nome) é disparado com
'ociosa' | 'pensando' | 'falando' | 'feliz', cravado no tempo da voz. Este
módulo só precisa expor as funções abaixo e reagir a esses estados.
"""

import logging

# Estados que o avatar entende — os MESMOS que o app.py já usa em _expressao().
# Manter em sincronia com IMAGENS_EXPRESSAO lá. Cada um vira uma expressão/motion
# Live2D (ou, no lip-sync, o estado 'falando' liga a boca).
EXPRESSOES = ("ociosa", "pensando", "falando", "feliz")


def disponivel():
    """True quando o modelo Live2D e as dependências estão instalados.

    Enquanto o avatar não existe, devolve False — assim, se alguém plugar
    isto no app cedo demais, o Yato só cai no PNGTuber de reserva em vez de
    quebrar. (Defesa em camadas.)"""
    return False   # TODO: checar pywebview + arquivos do modelo Live2D


def mostrar():
    """Abre a janela flutuante com o avatar por cima da tela.

    TODO: criar a webview (pywebview) apontando pra uma página HTML local
    que renderiza o modelo Live2D com pixi-live2d-display. Janela sem
    moldura, sempre-no-topo, fundo transparente."""
    raise NotImplementedError("Avatar Live2D ainda não construído — ver o plano no topo.")


def esconder():
    """Fecha/oculta a janela flutuante do avatar."""
    raise NotImplementedError("Avatar Live2D ainda não construído.")


def definir_expressao(nome):
    """Reage a uma mudança de estado do Yato (é o que o _expressao do app
    vai repassar pra cá).

    TODO: mandar pro JavaScript da página aplicar a expressão/motion Live2D
    correspondente (ex.: window.evaluate_js(f"setExpressao('{nome}')"))."""
    if nome not in EXPRESSOES:
        logging.warning("Expressão desconhecida pro avatar: %s", nome)
    # TODO: repassar 'nome' pra webview.


def lip_sync(amplitude):
    """Abre a boca do avatar conforme o VOLUME do áudio (0.0 a 1.0).

    A ideia: no voz.py, além de tocar o WAV, calcular a 'força' do som em
    janelinhas de tempo e chamar isto — a boca acompanha a fala de verdade.
    TODO: mapear amplitude → parâmetro ParamMouthOpenY do modelo Live2D."""
    # TODO: window.evaluate_js(f"setBoca({amplitude})")
