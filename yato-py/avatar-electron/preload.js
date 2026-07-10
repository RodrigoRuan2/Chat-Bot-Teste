// preload.js — a ponte SEGURA entre a página (avatar.js) e o Electron.
// Expõe só o que a página precisa: um jeito de pedir pro Electron fechar a
// janela. (contextBridge é a forma recomendada — a página não ganha acesso
// total ao Node, só a essa funçãozinha.)

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("avatarNativo", {
  fechar: () => ipcRenderer.send("fechar-avatar"),
});
