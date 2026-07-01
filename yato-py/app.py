"""
A JANELA — a interface gráfica do chat (CustomTkinter).

Aqui mora só a TELA e o que o usuário faz nela. Toda a parte de "falar com a
IA" está em cerebro.py. Essa separação (tela de um lado, lógica do outro) é o
que mantém o projeto organizado quando ele cresce.

Conceitos novos que aparecem aqui e valem estudar:
  - CLASSE: 'App' é um molde que junta os dados (o histórico) com as funções
    que mexem na tela. 'self' é "este objeto / esta janela".
  - THREAD: pedir a resposta da IA pode demorar segundos. Se a gente esperasse
    na thread principal, a janela CONGELARIA. Então a chamada roda numa thread
    separada (de fundo) e devolve o resultado pra tela quando termina.
"""

import logging
import threading
from pathlib import Path

import customtkinter as ctk

from personalidade import PERSONALIDADE
from cerebro import pensar, CerebroError, MODELO

# ---- Diário de bordo (yato.log, criado ao lado deste arquivo) ----
# Por que existe: aberto pelo atalho (pythonw), o app NÃO tem terminal —
# qualquer erro sumiria sem deixar rastro. Aqui, tudo fica registrado.
logging.basicConfig(
    filename=Path(__file__).with_name("yato.log"),
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    encoding="utf-8",
)

# Aparência geral: tema escuro e cor de destaque.
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Yato — IA local")
        self.geometry("520x660")
        self.minsize(420, 480)

        # ---- ESTADO: o histórico da conversa mora aqui ----
        # Começa só com a personalidade (a 1ª mensagem, de papel "system").
        # É a MESMA lista que mandamos pro cérebro a cada envio.
        self.mensagens = [{"role": "system", "content": PERSONALIDADE}]
        self.bolha_pensando = None  # referência ao balão "digitando…"

        self._montar_tela()

    # ----------------------------------------------------------------- tela
    def _montar_tela(self):
        cabecalho = ctk.CTkLabel(
            self,
            text=f"⚔️  Yato  ·  cérebro local ({MODELO})",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        cabecalho.pack(pady=12)

        # Área das mensagens: um quadro que ROLA sozinho quando enche.
        self.area = ctk.CTkScrollableFrame(self)
        self.area.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Linha de baixo: campo de digitar + botão enviar.
        baixo = ctk.CTkFrame(self, fg_color="transparent")
        baixo.pack(fill="x", padx=12, pady=(0, 12))

        self.entrada = ctk.CTkEntry(baixo, placeholder_text="Fala com a Yato...")
        self.entrada.pack(side="left", fill="x", expand=True)
        self.entrada.bind("<Return>", lambda evento: self.enviar())  # Enter envia

        self.botao = ctk.CTkButton(baixo, text="Enviar", width=90, command=self.enviar)
        self.botao.pack(side="left", padx=(8, 0))

        self._bolha('Manda um "oi" pra Yato…', autor="dica")
        self.entrada.focus()

    def _bolha(self, texto, autor):
        """Desenha um balão na área de mensagens. O 'autor' muda cor e lado."""
        estilos = {
            "user":   {"cor": "#6c5ce7", "lado": "e"},      # roxo, direita
            "yato": {"cor": "#2a2a3a", "lado": "w"},      # cinza, esquerda
            "dica":   {"cor": "transparent", "lado": "center"},
        }
        est = estilos[autor]

        balao = ctk.CTkFrame(self.area, fg_color=est["cor"], corner_radius=12)
        balao.pack(anchor=est["lado"], pady=4, padx=4)

        rotulo = ctk.CTkLabel(balao, text=texto, wraplength=360, justify="left")
        rotulo.pack(padx=12, pady=8)

        self._rolar_pro_fim()
        return balao

    def _rolar_pro_fim(self):
        """Rola a área de mensagens até o fim (pra ver a mensagem mais nova)."""
        try:
            self.update_idletasks()
            self.area._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass  # se a API interna mudar, melhor não derrubar o app por isso

    # --------------------------------------------------------------- ações
    def enviar(self):
        texto = self.entrada.get().strip()
        if not texto or self.bolha_pensando is not None:
            return  # vazio, ou já estamos esperando uma resposta

        # 1) mostra sua fala e guarda no histórico
        self._bolha(texto, autor="user")
        self.mensagens.append({"role": "user", "content": texto})
        self.entrada.delete(0, "end")

        # 2) trava o botão e mostra o "digitando…"
        self.botao.configure(state="disabled", text="...")
        self.bolha_pensando = self._bolha("digitando…", autor="yato")

        # 3) chama a IA numa THREAD de fundo, pra a janela não congelar.
        threading.Thread(target=self._buscar_resposta, daemon=True).start()

    def _buscar_resposta(self):
        """Roda NA THREAD DE FUNDO. Daqui NÃO se mexe na tela direto."""
        try:
            resposta = pensar(self.mensagens)
        except CerebroError as erro:
            # Falha CONHECIDA (Ollama fechado, modelo faltando, timeout...):
            # o cérebro já mandou a mensagem pronta e amigável — só mostrar.
            logging.warning("Falha conhecida: %s", erro)
            resposta = str(erro)
        except Exception:
            # Falha DESCONHECIDA: grava o rastro completo no yato.log
            # (logging.exception anexa o traceback inteiro sozinho).
            logging.exception("Erro inesperado ao falar com o cérebro")
            resposta = "Buguei feio aqui 😵 (anotei os detalhes no yato.log)"

        # Volta pra thread principal pra mexer na tela com segurança.
        self.after(0, self._mostrar_resposta, resposta)

    def _mostrar_resposta(self, resposta):
        self.bolha_pensando.destroy()        # tira o balão "digitando…"
        self.bolha_pensando = None
        self._bolha(resposta, autor="yato")
        self.mensagens.append({"role": "assistant", "content": resposta})
        self.botao.configure(state="normal", text="Enviar")
        self.entrada.focus()


if __name__ == "__main__":
    logging.info("Yato abriu (modelo: %s)", MODELO)
    App().mainloop()
    logging.info("Yato fechou")
