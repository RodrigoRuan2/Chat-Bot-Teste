"""
O OUVIDO — o Yato te escutando (STT), 100% local com o Whisper.

Par do voz.py: enquanto o voz.py FALA, o ouvido.py ESCUTA. Grava o microfone
(sounddevice) e transcreve o que você disse (faster-whisper — o Whisper da
OpenAI numa versão rápida que roda na CPU, sem brigar com o Ollama pela GPU).

Import PREGUIÇOSO: o faster-whisper e o modelo (~460 MB) só carregam na 1ª vez
que você usa o microfone — quem nunca clica no 🎤 não paga esse custo.
"""

import logging

TAXA = 16000               # o Whisper trabalha em 16 kHz
MODELO_WHISPER = "small"   # equilíbrio precisão × velocidade (bom em pt-BR)

_modelo = None    # WhisperModel, carregado sob demanda (cache)
_stream = None    # o stream de gravação do microfone
_pedacos = []     # os pedaços de áudio capturados enquanto grava


def disponivel():
    """True se as libs de ouvir estão instaladas (pra a UI avisar, não quebrar)."""
    try:
        import faster_whisper  # noqa: F401
        import sounddevice     # noqa: F401
        return True
    except Exception:
        return False


def _carregar():
    global _modelo
    if _modelo is None:
        from faster_whisper import WhisperModel   # import pesado — só agora
        # device=cpu + int8: rápido e leve, sem disputar a VRAM com o Ollama.
        _modelo = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")
    return _modelo


def gravando():
    """True se o microfone está gravando agora."""
    return _stream is not None


def iniciar():
    """Começa a gravar o microfone (até parar_e_transcrever ou parar)."""
    global _stream, _pedacos
    import sounddevice as sd
    _pedacos = []

    def _capturar(indata, frames, tempo, status):
        _pedacos.append(indata.copy())

    _stream = sd.InputStream(samplerate=TAXA, channels=1, dtype="float32",
                             callback=_capturar)
    _stream.start()


def parar_e_transcrever():
    """Para de gravar e devolve o TEXTO do que foi dito (ou '' se não entendeu)."""
    global _stream
    import numpy as np
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None
    if not _pedacos:
        return ""
    audio = np.concatenate(_pedacos, axis=0).flatten()
    modelo = _carregar()
    segmentos, _ = modelo.transcribe(audio, language="pt")
    return " ".join(seg.text.strip() for seg in segmentos).strip()


def parar():
    """Cancela a gravação sem transcrever (ex.: se o usuário desistir)."""
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None
