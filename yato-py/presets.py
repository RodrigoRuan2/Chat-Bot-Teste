"""
OS PRESETS — a biblioteca de prompts prontos do Yato.

Sétimo módulo do projeto, cada um com sua responsabilidade:
  personalidade.py = quem ele é      voz.py      = como FALA
  cerebro.py       = como pensa      ouvido.py   = como OUVE
  ferramentas.py   = o que faz       avatar2d.py = como aparece
  memoria.py       = o que lembra    imagem.py   = como DESENHA
  presets.py       = prompts prontos ← aqui

A IDEIA: em vez de o Yato traduzir um prompt inteiro do zero toda vez (lento e
imprevisível), ele parte de um PRESET — um prompt bom, já testado, que "congela"
a cena + o estilo + as tags de qualidade. O único trabalho que sobra pro cérebro
é encaixar um personagem no lugar certo (o slot "{personagem}"). Menos trabalho
pro Yato = resultado mais confiável.

DE ONDE VÊM OS PRESETS: o pulo do gato é que toda imagem que o Forge gera guarda
o prompt EMBUTIDO no próprio PNG (num campo de texto chamado "parameters", padrão
A1111/Forge). Então dá pra transformar os seus melhores resultados em presets
automaticamente — sem digitar nada. É o que `parametros_de_png()` faz.

DOIS ARQUIVOS, DE PROPÓSITO (mesma lógica da memória e da conversa):
  - embutidos.json → os presets CURADOS que acompanham o Yato (podem ir pro git).
  - meus.json      → os que VOCÊ salva. Dado pessoal → fica no .gitignore.
Ao carregar, os dois viram uma lista só. Ao salvar, só o meus.json muda.
"""

import json
import logging
import re
import shutil
import unicodedata
from pathlib import Path

PASTA_PRESETS = Path(__file__).with_name("presets")
PASTA_REFS = PASTA_PRESETS / "refs"
_ARQ_EMBUTIDOS = PASTA_PRESETS / "embutidos.json"
_ARQ_MEUS = PASTA_PRESETS / "meus.json"

# O "molde" de um preset. Ao carregar um preset salvo, a gente faz
# {**PRESET_PADRAO, **salvo} — assim um preset antigo, salvo antes de a gente
# inventar um campo novo, GANHA esse campo com o valor padrão em vez de quebrar.
# É a "migração leve por spread" que a memória e a conversa já usam.
PRESET_PADRAO = {
    "id": "",              # slug único (ex.: "sala-de-aula") — serve de chave
    "nome": "Sem nome",    # nome amigável que aparece na galeria
    "prompt_base": "",     # o prompt em inglês; pode conter o slot {personagem}
    "negativo": None,      # None = usa o NEGATIVO_PADRAO do imagem.py
    "referencia": None,    # nome do arquivo de miniatura dentro de refs/ (ou None)
    "tamanho": [768, 768], # [largura, altura] com que a imagem foi/será feita
    "modelo": "",          # o checkpoint (Forge) com que a referência foi feita
}

# O SLOT: onde o personagem entra no prompt. Se o preset tiver "{personagem}"
# em algum lugar, a injeção troca isso pela tag do personagem; se não pedir
# personagem nenhum, a gente apaga o slot e gera a cena pura.
SLOT_PERSONAGEM = "{personagem}"


# ─────────────────────────── LER / GRAVAR ───────────────────────────

def _ler_json(caminho):
    """Lê um arquivo JSON com LEITURA SEGURA: se não existir, estiver vazio ou
    corrompido, devolve lista vazia em vez de estourar. (Regra do projeto: dado
    corrompido nunca pode quebrar o app.)"""
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, list) else []
    except (OSError, ValueError):
        return []


def _normalizar(preset):
    """Garante que todo preset tenha todos os campos (migração leve por spread).
    Preset de terceiros/antigo ganha os campos novos sem perder o que já tinha."""
    return {**PRESET_PADRAO, **preset}


def carregar():
    """Devolve TODOS os presets (embutidos + meus) numa lista só, cada um já
    normalizado. Os 'meus' vêm depois — se um id se repetir, o seu vence."""
    todos = _ler_json(_ARQ_EMBUTIDOS) + _ler_json(_ARQ_MEUS)
    # de-duplica por id, mantendo a ÚLTIMA ocorrência (a sua, pessoal)
    por_id = {}
    for p in todos:
        p = _normalizar(p)
        if p["id"]:
            por_id[p["id"]] = p
    return list(por_id.values())


def salvar_meus(lista):
    """Grava a lista de presets pessoais no meus.json (cria a pasta se faltar)."""
    PASTA_PRESETS.mkdir(exist_ok=True)
    with open(_ARQ_MEUS, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def adicionar(preset):
    """Acrescenta um preset à sua biblioteca pessoal (meus.json). Se já existir
    um com o mesmo id, SUBSTITUI (pra você poder reeditar sem duplicar)."""
    preset = _normalizar(preset)
    meus = [_normalizar(p) for p in _ler_json(_ARQ_MEUS)]
    meus = [p for p in meus if p["id"] != preset["id"]]   # tira o antigo, se houver
    meus.append(preset)
    salvar_meus(meus)
    return preset


def renomear(id_, novo_nome):
    """Troca só o nome de um favorito (o id e a miniatura ficam iguais). Devolve
    True se achou e renomeou."""
    meus = [_normalizar(p) for p in _ler_json(_ARQ_MEUS)]
    achou = False
    for p in meus:
        if p["id"] == id_:
            p["nome"] = novo_nome
            achou = True
    if achou:
        salvar_meus(meus)
    return achou


def remover(id_):
    """Apaga um favorito (do meus.json) e a miniatura dele. Devolve True se
    apagou. Presets embutidos não saem por aqui (não estão no meus.json)."""
    meus = [_normalizar(p) for p in _ler_json(_ARQ_MEUS)]
    alvo = next((p for p in meus if p["id"] == id_), None)
    if alvo is None:
        return False
    salvar_meus([p for p in meus if p["id"] != id_])
    ref = alvo.get("referencia")
    if ref:
        try:
            (PASTA_REFS / ref).unlink(missing_ok=True)   # apaga a miniatura junto
        except OSError:
            pass
    return True


# ─────────────────────── IMPORTAR DE UM PNG ───────────────────────

def _slug(texto):
    """Transforma um nome em um id-slug (ex.: 'Sala de Aula!' -> 'sala-de-aula').
    Tira acentos, deixa minúsculo e troca o resto por hífen."""
    # NFKD separa a letra do acento; ascii/ignore joga o acento fora
    sem_acento = (unicodedata.normalize("NFKD", texto)
                  .encode("ascii", "ignore").decode("ascii"))
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-") or "preset"


def _parsear_parametros(texto):
    """Quebra o campo 'parameters' de um PNG (formato A1111/Forge) em prompt,
    negativo e tamanho. O formato é:

        <prompt positivo, pode ter várias linhas>
        Negative prompt: <negativo>
        Steps: 25, Sampler: ..., CFG scale: 5, Size: 768x768, Model: ...

    A linha de parâmetros é sempre a ÚLTIMA e começa com 'Steps:' — é assim que
    a gente a separa do negativo (que pode ter várias linhas antes dela)."""
    prompt = texto.strip()
    negativo = ""
    linha_param = ""

    if "Negative prompt:" in texto:
        antes, resto = texto.split("Negative prompt:", 1)
        prompt = antes.strip()
        linhas = resto.strip().split("\n")
        if linhas and "Steps:" in linhas[-1]:
            linha_param = linhas[-1]
            negativo = "\n".join(linhas[:-1]).strip()
        else:
            negativo = resto.strip()
    else:
        linhas = texto.strip().split("\n")
        if len(linhas) > 1 and "Steps:" in linhas[-1]:
            linha_param = linhas[-1]
            prompt = "\n".join(linhas[:-1]).strip()

    # Tamanho: procura "Size: 768x768" na linha de parâmetros.
    tamanho = list(PRESET_PADRAO["tamanho"])
    m = re.search(r"Size:\s*(\d+)\s*x\s*(\d+)", linha_param)
    if m:
        tamanho = [int(m.group(1)), int(m.group(2))]

    # Modelo: o "Model: xxx" que o Forge grava — qual checkpoint desenhou.
    mm = re.search(r"Model:\s*([^,]+)", linha_param)
    modelo = mm.group(1).strip() if mm else ""

    return {"prompt": prompt, "negativo": negativo, "tamanho": tamanho,
            "modelo": modelo}


def parametros_de_png(caminho):
    """Lê o prompt embutido num PNG gerado pelo Forge. Devolve um dict com
    {prompt, negativo, tamanho}, ou None se o PNG não tiver esses dados (ex.:
    uma imagem que não veio do Forge)."""
    try:
        from PIL import Image   # import tardio: só quem importa PNG paga por ele
        with Image.open(caminho) as img:
            texto = img.info.get("parameters")
    except (OSError, ValueError) as erro:
        logging.warning("parametros_de_png falhou em %s: %s", caminho, erro)
        return None
    if not texto:
        return None
    return _parsear_parametros(texto)


def id_unico(nome):
    """Gera um id-slug que ainda NÃO existe na biblioteca — assim favoritar duas
    imagens com o mesmo nome não faz uma sobrescrever a outra."""
    base = _slug(nome)
    existentes = {p["id"] for p in carregar()}
    if base not in existentes:
        return base
    n = 2
    while f"{base}-{n}" in existentes:
        n += 1
    return f"{base}-{n}"


def importar_de_png(caminho, nome=None, id_=None):
    """Transforma um PNG gerado pelo Forge num PRESET pronto: lê o prompt
    embutido e COPIA a imagem pra refs/ (vira a miniatura). Devolve o dict do
    preset — quem chama decide se salva (adicionar) ou só mostra. Devolve None
    se o PNG não tiver prompt embutido. Aceita um id_ pronto (pra garantir
    unicidade); se não vier, deriva do nome."""
    caminho = Path(caminho)
    dados = parametros_de_png(caminho)
    if dados is None:
        return None

    nome = nome or caminho.stem
    id_ = id_ or _slug(nome)

    # Copia o PNG pra refs/ com o nome do id (a miniatura do preset).
    PASTA_REFS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_REFS / f"{id_}.png"
    shutil.copy2(caminho, destino)

    return _normalizar({
        "id": id_,
        "nome": nome,
        "prompt_base": dados["prompt"],
        "negativo": dados["negativo"] or None,
        "referencia": destino.name,
        "tamanho": dados["tamanho"],
        "modelo": dados.get("modelo", ""),
    })


def preencher_modelos_faltando():
    """Backfill: pros favoritos que já existem SEM o campo 'modelo', lê a
    miniatura deles (que também guarda o prompt/Model embutido) e preenche.
    Assim os favoritos antigos ganham o modelo sem você refazer nada."""
    meus = [_normalizar(p) for p in _ler_json(_ARQ_MEUS)]
    mudou = False
    for p in meus:
        if not p.get("modelo") and p.get("referencia"):
            ref = PASTA_REFS / p["referencia"]
            if ref.exists():
                dados = parametros_de_png(ref)
                if dados and dados.get("modelo"):
                    p["modelo"] = dados["modelo"]
                    mudou = True
    if mudou:
        salvar_meus(meus)


# ─────────────────────── INJETAR O PERSONAGEM ───────────────────────
# (Fase 1 — a inteligência de traduzir "gojo" -> "gojo satoru, jujutsu kaisen"
#  mora no imagem.py/cerebro; AQUI fica só a mecânica de encaixar no slot.)

def injetar(prompt_base, tag_personagem=""):
    """Encaixa a tag do personagem no slot de um TEXTO de prompt e devolve o
    prompt final. Se não houver personagem, o slot some limpo (sem deixar
    vírgula solta). Trabalha numa string crua — serve tanto pra um preset quanto
    pro que o Ruan digitou/editou no campo da tela."""
    if SLOT_PERSONAGEM not in prompt_base:
        # Sem slot: se veio personagem, joga na frente; senão, usa cru.
        if tag_personagem:
            return f"{tag_personagem}, {prompt_base}".strip().strip(",")
        return prompt_base
    if tag_personagem:
        return prompt_base.replace(SLOT_PERSONAGEM, tag_personagem)
    # Sem personagem: apaga o slot e limpa a vírgula/espaço que sobra ao lado.
    limpo = prompt_base.replace(SLOT_PERSONAGEM, "")
    return re.sub(r"\s*,\s*,", ",", limpo).strip().strip(",").strip()


def montar_prompt(preset, tag_personagem=""):
    """Atalho: injeta o personagem no prompt_base de um preset (dict)."""
    return injetar(preset.get("prompt_base", ""), tag_personagem)
