"""
A VOZ — o Yato falando em voz alta (TTS), 100% local com o Piper.

Quinto módulo do projeto, cada um com sua responsabilidade:
  personalidade.py = quem ele é      cerebro.py     = como pensa
  ferramentas.py   = o que faz       memoria.py     = o que lembra
  fundo.py         = recorta imagem  voz.py         = como FALA  ← aqui

Como funciona: o Piper transforma texto em áudio (um modelo de voz .onnx que
roda na CPU). A gente gera o WAV na memória e toca com o winsound (embutido
no Windows — zero dependência a mais).

Import PREGUIÇOSO de novo: o `from piper import PiperVoice` e o carregamento
do modelo de voz (~60 MB) só acontecem na PRIMEIRA fala — quem nunca liga a
voz não paga esse custo ao abrir o app.
"""

import io
import logging
import re
import wave
from pathlib import Path

PASTA_VOZES = Path(__file__).with_name("vozes")
MODELO_VOZ = "pt_BR-faber-medium.onnx"   # a voz escolhida (masculina, pt-BR)

_voz = None   # PiperVoice, carregada sob demanda (cache)

# Tira emojis e símbolos que a voz falaria de forma estranha ("carinha
# piscando"...). Fala só o que é texto de verdade.
_SO_FALA = re.compile(
    "[\U0001F000-\U0001FAFF"   # emojis e pictogramas suplementares
    "\U00002600-\U000026FF"    # símbolos diversos
    "\U00002700-\U000027BF"    # dingbats
    "\U0001F1E6-\U0001F1FF"    # bandeiras
    "\U00002190-\U000021FF"    # setas
    "\U00002B00-\U00002BFF]",  # setas/símbolos suplementares
    flags=re.UNICODE,
)


def disponivel():
    """True se o modelo de voz está baixado (pra a UI avisar em vez de quebrar)."""
    return (PASTA_VOZES / MODELO_VOZ).exists()


def _carregar():
    global _voz
    if _voz is None:
        from piper import PiperVoice   # import pesado — só agora
        _voz = PiperVoice.load(str(PASTA_VOZES / MODELO_VOZ))
    return _voz


def _limpar(texto):
    """Deixa o texto pronto pra fala: sem emojis, espaços normalizados."""
    return " ".join(_SO_FALA.sub("", texto).split())


def falar(texto):
    """Gera o áudio da fala e TOCA — SÍNCRONO (bloqueia até o fim).

    Por que síncrono: o winsound não toca da memória de forma assíncrona.
    Como a janela chama isto numa THREAD de fundo, bloquear tudo bem — e
    de brinde a gente sabe que a fala acabou quando a função retorna (aí o
    avatar volta de 'falando' pra 'ociosa'). Para qualquer fala anterior.
    """
    import winsound
    parar()
    texto = _limpar(texto)
    if not texto:
        return
    voz = _carregar()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        voz.synthesize_wav(texto, wav)
    # SND_MEMORY toca da memória; sem SND_ASYNC = espera terminar.
    winsound.PlaySound(buffer.getvalue(), winsound.SND_MEMORY)


def parar():
    """Silencia qualquer fala em andamento (interrompe até a síncrona,
    chamada de outra thread — é como a janela corta a voz numa nova mensagem)."""
    import winsound
    winsound.PlaySound(None, winsound.SND_PURGE)
