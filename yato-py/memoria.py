"""
A MEMÓRIA — salvar e carregar a conversa em arquivo (persistência).

Terceira responsabilidade do projeto, no seu próprio arquivo:
  personalidade.py = quem a Yato é
  cerebro.py       = como ela pensa
  memoria.py       = o que ela lembra  ← você está aqui

Regras de ouro de persistência (valem pra qualquer projeto):
  1. LEITURA SEGURA: arquivo corrompido/ausente NUNCA derruba o app —
     na dúvida, devolve o padrão (lista vazia) e a vida segue.
  2. Validar o que veio do disco antes de usar (não confiar cegamente).
"""

import json
import logging
from pathlib import Path

# A conversa fica ao lado do código, em JSON legível (abra e olhe!).
# Este arquivo está no .gitignore: conversa é dado pessoal, não código.
ARQUIVO_CONVERSA = Path(__file__).with_name("conversa.json")


def salvar_conversa(mensagens):
    """Grava a conversa em disco — SEM a personalidade.

    Por que sem? A personalidade mora no personalidade.py (código). Se ela
    fosse salva junto e você editasse o arquivo depois, a Yato "antiga"
    voltaria do disco. Salvando só as falas, a personalidade atual sempre
    vale. (Princípio: cada dado tem UM dono — nada de cópias.)
    """
    falas = [m for m in mensagens if m["role"] != "system"]
    try:
        ARQUIVO_CONVERSA.write_text(
            json.dumps(falas, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        # Disco cheio, sem permissão... anota no diário e segue o baile:
        # perder o "salvar" é chato; derrubar o app por isso seria pior.
        logging.exception("Não consegui salvar a conversa")


def carregar_conversa():
    """Lê a conversa salva. QUALQUER problema → lista vazia (nunca quebra).

    Este é o padrão 'leitura segura': try/except em volta do parse, e
    validação item a item — se alguém editou o JSON na mão e estragou uma
    fala, as outras ainda são aproveitadas.
    """
    try:
        dados = json.loads(ARQUIVO_CONVERSA.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []          # primeira vez que o app roda: normal não existir
    except (OSError, json.JSONDecodeError):
        logging.exception("conversa.json ilegível — começando do zero")
        return []

    if not isinstance(dados, list):
        return []
    return [
        m for m in dados
        if isinstance(m, dict)
        and m.get("role") in ("user", "assistant")
        and isinstance(m.get("content"), str)
    ]


# ===========================================================================
#  MEMÓRIA DE FATOS — o que o Yato sabe sobre VOCÊ, entre sessões.
#
#  Diferença crucial pro conversa.json: conversa é o PAPO (o 🧹 apaga);
#  fatos são CONHECIMENTO duradouro ("estuda React", "tem RTX 4060 Ti") —
#  sobrevivem à limpeza e entram no system prompt de toda conversa.
#  É o mesmo mecanismo de qualquer assistente com "memória": um amnésico
#  com um caderno — anota, relê, parece que lembra.
# ===========================================================================

ARQUIVO_FATOS = Path(__file__).with_name("fatos.json")

# Teto de fatos. Por quê: TODOS entram no prompt a cada mensagem — memória
# grande demais devora a "mesa" de contexto. 20 fatos curtos ≈ baratíssimo.
MAX_FATOS = 20


def carregar_fatos():
    """Lê os fatos salvos. Qualquer problema → lista vazia (leitura segura)."""
    try:
        dados = json.loads(ARQUIVO_FATOS.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError):
        logging.exception("fatos.json ilegível — seguindo sem fatos")
        return []
    if not isinstance(dados, list):
        return []
    return [f.strip() for f in dados if isinstance(f, str) and f.strip()][:MAX_FATOS]


def salvar_fatos(fatos):
    try:
        ARQUIVO_FATOS.write_text(
            json.dumps(fatos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        logging.exception("Não consegui salvar os fatos")


def anotar_fato(fato):
    """Anota um fato novo. Devolve um recado (vai pro modelo, como ferramenta).

    Proteções: fato vazio, repetido (ignorando maiúsculas) e memória cheia —
    o modelo recebe o motivo em texto e se explica pro usuário.
    """
    fato = " ".join(str(fato).split())
    if not fato:
        return "(Fato vazio — nada anotado.)"
    fatos = carregar_fatos()
    if any(fato.lower() == f.lower() for f in fatos):
        return "(Esse fato já estava anotado.)"
    if len(fatos) >= MAX_FATOS:
        return (f"(Memória cheia: já são {MAX_FATOS} fatos. "
                "Peça ao usuário qual esquecer antes de anotar outro.)")
    fatos.append(fato)
    salvar_fatos(fatos)
    return f"(Anotado na memória permanente: {fato})"


def esquecer_fato(trecho):
    """Apaga fatos que contenham o trecho. Devolve o resultado como recado."""
    trecho = str(trecho).strip().lower()
    if not trecho:
        return "(Diga qual fato esquecer.)"
    fatos = carregar_fatos()
    restantes = [f for f in fatos if trecho not in f.lower()]
    removidos = len(fatos) - len(restantes)
    if removidos == 0:
        return "(Não achei nenhum fato com esse trecho.)"
    salvar_fatos(restantes)
    return f"({removidos} fato(s) esquecido(s).)"
