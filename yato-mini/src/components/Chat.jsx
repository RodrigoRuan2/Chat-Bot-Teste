import { useState } from "react";
import { PERSONALIDADE } from "../personality";
import "../styles/Chat.css";

// ----- O CÉREBRO LOCAL (Ollama) -----
// O Ollama é um programa que roda modelos de IA no SEU computador e abre um
// pequeno servidor na porta 11434. O React conversa com ele por HTTP, igual
// conversaria com uma API na internet — só que nada sai da sua máquina.
const OLLAMA_URL = "http://localhost:11434/api/chat";

// Qual modelo usar. Precisa estar baixado: `ollama pull gemma3:4b`.
// Trocar de modelo = trocar este nome (veja opções no README).
const MODELO = "gemma3:4b";

export default function Chat() {
  // ----- ESTADO (state): tudo que muda na tela mora aqui -----
  const [mensagens, setMensagens] = useState([]); // histórico da conversa
  const [texto, setTexto] = useState("");          // o que você está digitando
  const [carregando, setCarregando] = useState(false);

  async function enviar() {
    const conteudo = texto.trim();
    if (!conteudo || carregando) return;

    // 1) Adiciona a SUA mensagem na tela
    const novas = [...mensagens, { autor: "user", conteudo }];
    setMensagens(novas);
    setTexto("");
    setCarregando(true);

    try {
      // Manda a conversa inteira pro Ollama. Ele não tem memória entre
      // chamadas, então TODA vez enviamos: a personalidade + o histórico.
      const r = await fetch(OLLAMA_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: MODELO,
          stream: false, // queremos a resposta inteira de uma vez (streaming fica pra depois)
          messages: [
            // A 1ª mensagem é a "system": diz pra IA QUEM ela é
            { role: "system", content: PERSONALIDADE },
            // Depois vem o histórico, no formato que a API entende
            ...novas.map((m) => ({
              role: m.autor === "user" ? "user" : "assistant",
              content: m.conteudo,
            })),
          ],
        }),
      });
      if (!r.ok) throw new Error(`Ollama respondeu com erro ${r.status}`);

      const dados = await r.json();
      const resposta =
        dados.message?.content?.trim() || "Deu ruim aqui, tenta de novo 😅";

      // 2) Adiciona a resposta da Yato na tela
      setMensagens((prev) => [...prev, { autor: "yato", conteudo: resposta }]);
    } catch (erro) {
      console.error(erro);
      // Se o fetch nem conectou (TypeError), o Ollama não está aberto.
      const cerebroDesligado = erro instanceof TypeError;
      setMensagens((prev) => [
        ...prev,
        {
          autor: "yato",
          conteudo: cerebroDesligado
            ? "Meu cérebro tá desligado 💀 (abre o Ollama e tenta de novo)"
            : "Buguei feio aqui, tenta de novo 😅",
        },
      ]);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="chat">
      <header className="chat__header">
        <span className="chat__avatar">⚔️</span>
        <div>
          <h1 className="chat__nome">Yato</h1>
          <p className="chat__status">VTuber IA · cérebro local ({MODELO})</p>
        </div>
      </header>

      <div className="chat__mensagens">
        {mensagens.length === 0 && (
          <p className="chat__vazio">Manda um "oi" pra Yato…</p>
        )}
        {mensagens.map((m, i) => (
          <div key={i} className={`bolha bolha--${m.autor}`}>
            {m.conteudo}
          </div>
        ))}
        {carregando && <div className="bolha bolha--yato">digitando…</div>}
      </div>

      <div className="chat__entrada">
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && enviar()}
          placeholder="Fala com a Yato..."
        />
        <button onClick={enviar} disabled={carregando}>
          Enviar
        </button>
      </div>
    </div>
  );
}
