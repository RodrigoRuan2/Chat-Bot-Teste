"""
A IMAGEM — o Yato desenha, gerando arte com o Forge (Stable Diffusion) local.

Sexto módulo do projeto, cada um com sua responsabilidade:
  personalidade.py = quem ele é      voz.py      = como FALA
  cerebro.py       = como pensa      ouvido.py   = como OUVE
  ferramentas.py   = o que faz       avatar2d.py = como aparece
  memoria.py       = o que lembra    imagem.py   = como DESENHA  ← aqui

Como funciona: o Forge (Stable Diffusion WebUI Forge) roda como um programa À
PARTE, aberto com a flag --api — isso expõe um endereço local que este módulo
chama por HTTP, sem chave nenhuma (é local, não é serviço pago). O checkpoint
carregado no Forge (o "Nova Anime XL" no seu caso) é quem desenha de fato.

O PULO DO GATO: modelos de imagem como o Nova Anime XL esperam prompt em
INGLÊS e detalhado — mas você não precisa saber inglês. `melhorar_prompt()`
usa o PRÓPRIO cérebro do Yato (o mesmo Ollama do cerebro.py) pra traduzir sua
descrição em português pra um prompt bom, com as tags de qualidade certas.

A DISPUTA DE VRAM: o Ollama (~5 GB) e o Forge/SDXL (~6-7 GB) NÃO cabem juntos
nos 8 GB da placa. Antes de gerar, `liberar_vram_ollama()` manda o Ollama
SOLTAR o modelo na hora (keep_alive=0) — o mesmo truque que o ver_imagem já
usa em ferramentas.py pra revezar com o olho da visão. Ele recarrega sozinho
na próxima mensagem do chat.
"""

import base64
import logging
import os
import re
import subprocess
import time
from pathlib import Path

import requests

from cerebro import OLLAMA_URL, MODELO

FORGE_URL = "http://127.0.0.1:7860"
PASTA_IMAGENS = Path(__file__).with_name("imagens_geradas")

# ONDE o Forge está instalado NA SUA MÁQUINA. Ele é um app gigante À PARTE, fora
# do repositório do Yato — por isso o caminho é absoluto e mora aqui (não no
# projeto). Dá pra apontar por variável de ambiente YATO_FORGE; se ela não
# existir, cai no caminho padrão abaixo. Mude se o seu Forge estiver noutro lugar.
PASTA_FORGE = Path(os.environ.get(
    "YATO_FORGE", r"C:\Users\ruanc\projetos\Criando o Yato\webui"))
BAT_FORGE = PASTA_FORGE / "webui-user.bat"

_processo_forge = None   # o Popen do Forge, quando foi o Yato que o abriu

# As tags de qualidade recomendadas para o Nova Anime XL (checkpoint
# Illustrious) — confirmadas na página oficial do modelo no Civitai.
TAGS_QUALIDADE = ("masterpiece, best quality, amazing quality, 4k, "
                  "very aesthetic, high resolution, ultra-detailed, absurdres")
# O peso extra "(...):1.3" diz ao Forge "preste 1.3x mais atenção nisso" — o
# guia oficial do Illustrious recomenda reforçar assim justamente as tags de
# TEXTO, porque modelos de imagem são notoriamente ruins em desenhar letras
# (viram garranchos sem sentido). Sem isso, textos/legendas/logos aparecem do
# nada em cenas como "tela de show" ou "outdoor".
NEGATIVO_PADRAO = (
    "worst quality, low quality, blurry, bad anatomy, bad hands, "
    "(text, watermark, signature, username, logo, speech bubble:1.3)"
)

_PROMPT_SISTEMA_MELHORAR = f"""Você traduz descrições em português para prompts de
geração de imagem em INGLÊS, no estilo de tags separadas por vírgula (padrão
Danbooru/Illustrious), como usado no checkpoint Nova Anime XL.

Regras:
- TODA palavra do prompt final deve estar em INGLÊS — sem NENHUMA palavra em
  português sobrando (nem "cantando", nem "palco", nem nada). Um prompt com
  mistura de idiomas confunde o modelo e gera texto embaralhado na imagem —
  isso é PROIBIDO. Releia sua resposta antes de entregar e troque qualquer
  palavra em português que tiver escapado.
- REGRA DE OURO sobre PERSONAGEM/OBRA CONHECIDA (anime, jogo, etc.): o modelo
  de imagem JÁ FOI TREINADO nesses personagens e sabe a aparência deles PERFEITAMENTE
  — melhor que você. Qualquer descrição física que você adicionar só vai ATRAPALHAR.
  Então, se a pessoa citar um personagem conhecido, seja MINIMALISTA e escreva
  APENAS, nesta ordem:
    <nome do personagem em inglês>, <nome da obra se souber>, <a cena/pose/cenário pedidos>
  PROIBIDO adicionar cabelo, cor dos olhos, roupa ou qualquer traço físico do
  personagem — mesmo que você ache que sabe. Exemplo do jeito CERTO:
    entrada: "satoru gojo em uma sala de aula"
    saída:   "gojo satoru, jujutsu kaisen, classroom, sitting, {TAGS_QUALIDADE}"
  (repare: NENHUMA tag de cabelo/olhos/roupa — o modelo de imagem cuida disso).
- Se NÃO for personagem conhecido (algo genérico, tipo "uma garota qualquer"),
  aí SIM traduza e EXPANDA em tags visuais concretas (aparência, roupas, pose,
  expressão, cenário, luz, cores).
- Termine SEMPRE com: {TAGS_QUALIDADE}
- Responda APENAS com o prompt final, sem explicações, sem aspas, sem markdown.
- Nunca inclua conteúdo adulto/explícito."""

# A instrução da INJEÇÃO (Rodada 12): tarefa MENOR que o melhorar_prompt. Aqui o
# Yato NÃO monta a cena nem as tags de qualidade — isso já vem pronto do preset.
# Ele só traduz UM personagem pra a tag booru canônica, pra encaixar no slot.
_PROMPT_SISTEMA_PERSONAGEM = """Você recebe o nome ou a descrição de UM personagem
(em português) e devolve APENAS as tags em INGLÊS que identificam esse personagem
— NADA de cena, pose, cenário ou qualidade.

Regras:
- Personagem CONHECIDO (anime, jogo, etc.): o modelo de imagem já sabe a
  aparência dele. Devolva SÓ, nesta ordem:
    <nome do personagem em inglês>, <nome da obra>, <1girl ou 1boy>
  Exemplos:
    "gojo"          -> gojo satoru, jujutsu kaisen, 1boy
    "rias gremory"  -> rias gremory, high school dxd, 1girl
  PROIBIDO adicionar cabelo, olhos, roupa ou qualquer traço físico — só ATRAPALHA.
- Descrição GENÉRICA (ex.: "uma garota de cabelo azul"): aí sim traduza pras
  tags visuais concretas. Ex.: "1girl, blue hair, short hair".
- Responda SÓ com as tags, em inglês, separadas por vírgula. Sem explicação, sem
  aspas, sem markdown, sem tags de qualidade, sem ponto final."""

# A instrução do VIRAR MOLDE (generalizar): pega um prompt cheio dos traços de UM
# personagem e devolve um MOLDE reutilizável — mesmo estilo/cena, mas com o slot
# {personagem} no lugar da aparência. Resolve o "quero o estilo, mas com OUTRO
# personagem" (senão o cabelo/olhos do original brigam com o novo).
_PROMPT_SISTEMA_GENERALIZAR = """Você recebe um prompt de imagem em INGLÊS (tags
booru, estilo Illustrious/Nova Anime XL) e transforma ele num MOLDE reutilizável:
mantém o ESTILO e a CENA, mas tira o que é do PERSONAGEM, pra outro personagem
poder entrar no lugar.

Faça assim:
- REMOVA as tags de APARÊNCIA/IDENTIDADE do personagem: nome de personagem;
  cabelo (cor e estilo, ex.: "blue hair", "long hair", "blunt bangs"); olhos
  (cor, ex.: "red eyes"); pele; corpo; chifres/orelhas/cauda de raça; e a
  contagem de gênero ("1girl", "1boy", "2girls"). O personagem novo traz isso.
- MANTENHA tudo que é ESTILO e CENA: qualidade (masterpiece, best quality...);
  tags de artista (ex.: "@sw33t"); enquadramento e pose (upper body, from behind,
  looking back); ângulo de câmera; luz; cenário/fundo; efeitos; clima; roupa
  genérica.
- Comece a resposta com "{personagem}, " e depois as tags mantidas.
- Responda SÓ com o prompt final, em inglês, sem explicação, sem aspas.

Exemplo:
entrada: "masterpiece, best quality, 1girl, solo, @sw33t, upper body, from behind, (white hair:1.2), blue hair, blunt bangs, (blue eyes:1.3), glowing eyes, kimono, snowflakes, dark background"
saída: "{personagem}, masterpiece, best quality, solo, @sw33t, upper body, from behind, glowing eyes, kimono, snowflakes, dark background\""""


class ImagemError(Exception):
    """Erro já traduzido pra mensagem amigável — quem chama não precisa
    entender de HTTP nem de Forge."""


def disponivel():
    """True se o Forge está aberto e respondendo (pra a UI avisar, não travar)."""
    try:
        r = requests.get(f"{FORGE_URL}/sdapi/v1/sd-models", timeout=3)
        return r.ok
    except requests.exceptions.RequestException:
        return False


def forge_instalado():
    """True se dá pra achar o webui-user.bat — ou seja, se o Yato consegue
    abrir o Forge sozinho. (Se der False, o caminho PASTA_FORGE está errado.)"""
    return BAT_FORGE.exists()


def abrir_forge():
    """Abre o Forge (webui-user.bat) numa JANELA DE TERMINAL PRÓPRIA, pra você
    acompanhar o boot (~40s no 1º boot) e os logs. NÃO espera ficar pronto —
    quem chama usa o esperar_disponivel() pra isso. Não abre de novo se já
    estiver no ar ou já estiver abrindo. Retorna False se não achou o .bat."""
    global _processo_forge
    if disponivel():
        return True   # já está no ar — nada a fazer
    if _processo_forge is not None and _processo_forge.poll() is None:
        return True   # já estamos abrindo — não abre uma segunda instância
    if not BAT_FORGE.exists():
        return False
    # Alguns ambientes definem NoDefaultCurrentDirectoryInExePath=1 (um
    # endurecimento de segurança) — isso faz o cmd NÃO procurar comandos na
    # pasta atual, e o webui-user.bat quebra logo no "call webui.bat". Tiramos
    # essa variável SÓ pro processo do Forge, pra ele sempre achar o webui.bat.
    ambiente = {k: v for k, v in os.environ.items()
                if k.lower() != "nodefaultcurrentdirectoryinexepath"}
    # cmd /c <bat> numa CONSOLE NOVA: o Forge ganha o próprio terminal (mostra o
    # boot e os logs) e NÃO morre junto se o Yato fechar. CREATE_NEW_CONSOLE só
    # existe no Windows — o getattr deixa o código não quebrar noutro sistema.
    nova_console = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    _processo_forge = subprocess.Popen(
        ["cmd", "/c", str(BAT_FORGE)],
        cwd=str(PASTA_FORGE),
        env=ambiente,
        creationflags=nova_console,
    )
    return True


def esperar_disponivel(timeout=150, intervalo=2):
    """Fica checando até o Forge responder (ou estourar o timeout). Serve pra
    usar DEPOIS do abrir_forge(), porque o boot demora. Retorna True se ficou
    pronto a tempo. Chame numa thread — ela dorme entre as tentativas."""
    limite = time.time() + timeout
    while time.time() < limite:
        if disponivel():
            return True
        time.sleep(intervalo)
    return False


def listar_modelos():
    """Os checkpoints (modelos de imagem) instalados no Forge — cada um com um
    ponto forte diferente (anime, realismo…). Devolve uma lista de títulos
    (vazia se o Forge estiver fechado ou não tiver nenhum)."""
    try:
        r = requests.get(f"{FORGE_URL}/sdapi/v1/sd-models", timeout=10)
        r.raise_for_status()
        return [m["title"] for m in r.json()]
    except requests.exceptions.RequestException as erro:
        logging.warning("listar_modelos falhou: %s", erro)
        return []


def modelo_atual():
    """O checkpoint carregado agora no Forge (None se não der pra saber)."""
    try:
        r = requests.get(f"{FORGE_URL}/sdapi/v1/options", timeout=10)
        r.raise_for_status()
        return r.json().get("sd_model_checkpoint")
    except requests.exceptions.RequestException:
        return None


def trocar_modelo(titulo):
    """Troca o checkpoint ativo no Forge. DEMORA (~10-40s: descarrega o atual
    e carrega o novo do disco) — chame numa thread. Levanta ImagemError se
    o Forge recusar ou estiver fechado."""
    try:
        r = requests.post(f"{FORGE_URL}/sdapi/v1/options",
                          json={"sd_model_checkpoint": titulo}, timeout=120)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ImagemError("O Forge está fechado — não dá pra trocar de modelo.")
    except requests.exceptions.RequestException as erro:
        logging.warning("trocar_modelo falhou: %s", erro)
        raise ImagemError("Não consegui trocar o modelo — confira o terminal do Forge.")


def liberar_vram_ollama():
    """Manda o Ollama soltar o modelo da GPU AGORA (sem gerar nada) — o Forge
    precisa da placa inteira. Truque: keep_alive=0 sem mensagens = descarrega
    na hora, em vez de esperar os minutos normais de ociosidade. Se o Ollama
    nem estiver aberto, não tem problema — ignora e segue."""
    try:
        requests.post(OLLAMA_URL, json={"model": MODELO, "messages": [],
                                        "keep_alive": 0}, timeout=10)
    except requests.exceptions.RequestException:
        pass   # Ollama fechado ou ocupado — a geração tenta mesmo assim


def melhorar_prompt(descricao_pt):
    """Usa o cérebro (qwen2.5) pra traduzir sua descrição em português pra um
    prompt em inglês, com as tags de qualidade do Nova Anime XL. Devolve o
    prompt pronto — você ainda pode editar antes de gerar."""
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODELO,
                "stream": False,
                "keep_alive": "10m",   # ele segue disponível pro chat depois
                "messages": [
                    {"role": "system", "content": _PROMPT_SISTEMA_MELHORAR},
                    {"role": "user", "content": descricao_pt},
                ],
                "options": {"num_predict": 250, "temperature": 0.6},
            },
            timeout=120,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ImagemError("Meu cérebro tá desligado 💀 (abre o Ollama e tenta de novo)")
    except requests.exceptions.RequestException as erro:
        logging.warning("melhorar_prompt falhou: %s", erro)
        raise ImagemError("Não consegui melhorar o prompt — tenta de novo?")

    texto = r.json().get("message", {}).get("content", "").strip()
    if not texto:
        raise ImagemError("O cérebro não devolveu nada — tenta descrever de outro jeito?")
    return texto


def personagem_para_tags(pedido_pt):
    """Traduz UM personagem (em português) pra a tag booru canônica que entra no
    slot {personagem} de um preset. Ex.: "gojo" -> "gojo satoru, jujutsu kaisen,
    1boy". Tarefa pequena e focada — o preset já cuida da cena e da qualidade.
    Devolve a tag (string). Levanta ImagemError se o cérebro estiver fora."""
    if not pedido_pt or not pedido_pt.strip():
        return ""
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODELO,
                "stream": False,
                "keep_alive": "10m",
                "messages": [
                    {"role": "system", "content": _PROMPT_SISTEMA_PERSONAGEM},
                    {"role": "user", "content": pedido_pt},
                ],
                # Tarefa curta e determinística: poucos tokens, temperatura baixa
                # (queremos SEMPRE a mesma tag pro mesmo personagem, sem invenção).
                "options": {"num_predict": 60, "temperature": 0.3},
            },
            timeout=60,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ImagemError("Meu cérebro tá desligado 💀 (abre o Ollama e tenta de novo)")
    except requests.exceptions.RequestException as erro:
        logging.warning("personagem_para_tags falhou: %s", erro)
        raise ImagemError("Não consegui traduzir o personagem — tenta de novo?")

    # Limpa sujeira comum: aspas, ponto final, quebras de linha.
    return r.json().get("message", {}).get("content", "").strip().strip('".').replace("\n", " ")


# O FILTRO DE APARÊNCIA (determinístico): o cérebro é bom em RECONHECER o nome do
# personagem, mas ruim em APAGAR tags de um prompt longo (modelo pequeno tende a
# copiar tudo). Como tag booru é texto separado por vírgula, a gente apaga as de
# aparência por REGRA — confiável, sem depender do cérebro. Tudo que casar aqui
# sai do molde (o personagem novo traz os traços dele).
_APARENCIA_SUBSTR = ("hair", "eyes", "breasts", "skin")   # casa por pedaço no meio
# Tags que FORÇAM a paleta da imagem inteira — num molde elas pintam até a pele
# do novo personagem (ex.: "(blue theme:1.3)" deixou a Rias azul). Fora todas.
# (Qualquer "<cor> theme" também é pego pela regra endswith(" theme").)
_COR_FORCADA = {
    "monochrome", "greyscale", "grayscale", "limited palette", "spot color",
    "muted colors", "muted color", "sepia", "colored skin",
}
_APARENCIA_EXATAS = {
    "1girl", "1boy", "2girls", "2boys", "3girls", "3boys", "1other",
    "multiple girls", "multiple boys", "6+girls",
    "bangs", "blunt bangs", "swept bangs", "sidelocks", "ponytail", "twintails",
    "twin tails", "braid", "braids", "ahoge", "hime cut", "bob cut",
    "horns", "oni horns", "dragon horns", "pointy ears", "animal ears",
    "cat ears", "fox ears", "dog ears", "rabbit ears", "elf ears",
    "tail", "cat tail", "fox tail", "wings", "angel wings", "demon wings",
    "halo", "fang", "fangs", "heterochromia",
    "pale skin", "dark skin", "tan", "tanlines", "curvy", "flat chest",
    "thick thighs", "wide hips", "petite", "muscular", "slim",
}


def _tag_limpa(tag):
    """Tira peso e parênteses de uma tag: '(white hair:1.2)' -> 'white hair'."""
    t = tag.strip().strip("()")
    t = re.sub(r":[\d.]+$", "", t)   # o peso ":1.2" no fim
    return t.strip("() ").lower()


def _e_aparencia(tag):
    """True se a tag descreve a aparência/identidade do personagem OU força a
    paleta de cor da imagem (que num molde acaba pintando o personagem novo)."""
    limpo = _tag_limpa(tag)
    if limpo in _APARENCIA_EXATAS or limpo in _COR_FORCADA:
        return True
    if limpo.endswith(" theme"):   # "blue theme", "red theme", "dark theme"…
        return True
    return any(p in limpo for p in _APARENCIA_SUBSTR)


def _remover_aparencia(prompt):
    """Filtra as tags de aparência de um prompt, preservando o slot {personagem}
    na frente. É a rede de segurança confiável por cima do cérebro."""
    tem_slot = "{personagem}" in prompt
    tags = [t.strip() for t in prompt.split(",")]
    mantidas = [t for t in tags
                if t and t != "{personagem}" and not _e_aparencia(t)]
    corpo = ", ".join(mantidas)
    return f"{{personagem}}, {corpo}" if tem_slot else corpo


def generalizar_prompt(prompt_en):
    """Transforma um prompt cheio dos traços de UM personagem num MOLDE com o
    slot {personagem} — mantém estilo/cena, tira a aparência. Serve pra reusar o
    mesmo estilo com outro personagem. Devolve o prompt-molde (string).

    Duas camadas: o cérebro tira o NOME do personagem (o que ele faz bem) e um
    filtro no código tira as tags de APARÊNCIA (o que o cérebro faz mal)."""
    if not prompt_en or not prompt_en.strip():
        raise ImagemError("Sem prompt pra virar molde — escolha ou gere algo antes.")
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODELO,
                "stream": False,
                "keep_alive": "10m",
                "messages": [
                    {"role": "system", "content": _PROMPT_SISTEMA_GENERALIZAR},
                    {"role": "user", "content": prompt_en},
                ],
                "options": {"num_predict": 300, "temperature": 0.4},
            },
            timeout=90,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ImagemError("Meu cérebro tá desligado 💀 (abre o Ollama e tenta de novo)")
    except requests.exceptions.RequestException as erro:
        logging.warning("generalizar_prompt falhou: %s", erro)
        raise ImagemError("Não consegui virar molde — tenta de novo?")

    texto = r.json().get("message", {}).get("content", "").strip().strip('"')
    if not texto:
        raise ImagemError("O cérebro não devolveu o molde — tenta de novo?")
    # Rede de segurança: se o cérebro esquecer o slot, põe na frente.
    if "{personagem}" not in texto:
        texto = "{personagem}, " + texto
    # A CAMADA CONFIÁVEL: apaga as tags de aparência que o cérebro deixou passar.
    return _remover_aparencia(texto)


def gerar(prompt, negativo=None, passos=25, largura=768, altura=768):
    """Gera a imagem: libera a VRAM do Ollama, chama o Forge, salva o PNG em
    imagens_geradas/ e devolve o Path do arquivo."""
    if not prompt or not prompt.strip():
        raise ImagemError("Sem prompt pra gerar — escreva ou melhore uma descrição antes.")

    liberar_vram_ollama()

    try:
        r = requests.post(
            f"{FORGE_URL}/sdapi/v1/txt2img",
            json={
                "prompt": prompt,
                "negative_prompt": negativo or NEGATIVO_PADRAO,
                "steps": passos,
                "width": largura,
                "height": altura,
                "cfg_scale": 5,
            },
            # A geração de imagem demora (~15-30s no SDXL); generoso de propósito.
            timeout=180,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ImagemError(
            "O Forge está fechado 🎨💤 (abra o webui-user.bat com --api e tenta de novo)")
    except requests.exceptions.Timeout:
        raise ImagemError("Demorou demais pra desenhar 😵 Tenta de novo?")
    except requests.exceptions.RequestException as erro:
        logging.warning("gerar (Forge) falhou: %s", erro)
        raise ImagemError("O Forge reclamou de alguma coisa — confira o terminal dele.")

    dados = r.json()
    imagens = dados.get("images") or []
    if not imagens:
        raise ImagemError("O Forge respondeu mas não veio nenhuma imagem — estranho.")

    PASTA_IMAGENS.mkdir(exist_ok=True)
    caminho = PASTA_IMAGENS / f"yato_{int(time.time())}.png"
    caminho.write_bytes(base64.b64decode(imagens[0]))
    return caminho
