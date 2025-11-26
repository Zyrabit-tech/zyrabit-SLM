#!/bin/bash

# setup_ollama.sh
# Script para configurar Ollama y descargar los modelos necesarios

echo "--- Zyrabit LLM Setup ---"

# 1. Verificar si Ollama está instalado
if ! command -v ollama &> /dev/null; then
    echo "[INFO] Ollama no encontrado. Instalando..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "[INFO] Ollama ya está instalado."
fi

# 2. Iniciar el servidor Ollama (en segundo plano si es necesario)
if ! pgrep -x "ollama" > /dev/null; then
    echo "[INFO] Iniciando servidor Ollama..."
    ollama serve &
    sleep 5 # Esperar a que inicie
else
    echo "[INFO] Servidor Ollama ya está corriendo."
fi

# 3. Descargar modelos
echo "[INFO] Descargando modelo LLM 'phi3'..."
ollama pull phi3

echo "[INFO] Descargando modelo de Embeddings 'mxbai-embed-large'..."
ollama pull mxbai-embed-large

echo "--- Setup Completado ---"
echo "Ejecuta 'python3 secure_agent.py' para probar el agente."
