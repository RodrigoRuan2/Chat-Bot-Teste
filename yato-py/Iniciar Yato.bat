@echo off
REM ==============================================================
REM   Iniciar Yato - de um duplo-clique e a IA local abre.
REM   (arquivo .bat = uma listinha de comandos que o Windows roda)
REM ==============================================================

REM 1) Liga o Ollama (o cerebro). Se ja estiver aberto, ele so ignora.
start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"

REM 2) Entra na pasta do projeto (caminho absoluto = funciona de qualquer lugar).
cd /d "C:\Users\ruanc\projetos\Chat bot\yato-py"

REM 3) Abre a janela da Yato SEM tela preta de terminal (pythonw).
start "" ".venv\Scripts\pythonw.exe" "app.py"
