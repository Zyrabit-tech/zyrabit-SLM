#!/bin/bash

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Iniciando Setup de Ollama para Zyrabit...${NC}"

# 1. Navegar al directorio correcto
cd zyrabit-brain-api || { echo -e "${RED}❌ Error: No encuentro el directorio zyrabit-brain-api${NC}"; exit 1; }

# 2. Levantar el contenedor de Ollama
echo -e "${YELLOW}📦 Levantando contenedor llm-server...${NC}"
docker-compose up -d llm-server

# 3. Esperar a que Ollama esté listo
echo -e "${YELLOW}⏳ Esperando a que Ollama inicie (10s)...${NC}"
sleep 10

# 4. Verificar si el modelo ya existe
echo -e "${YELLOW}🔍 Verificando modelos instalados...${NC}"
if docker-compose exec llm-server ollama list | grep -q "phi3"; then
    echo -e "${GREEN}✅ El modelo 'phi3' ya está instalado.${NC}"
else
    echo -e "${YELLOW}⬇️  Modelo 'phi3' no encontrado. Descargando (esto puede tardar unos minutos)...${NC}"
    docker-compose exec llm-server ollama pull phi3
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Modelo 'phi3' descargado correctamente.${NC}"
    else
        echo -e "${RED}❌ Error al descargar el modelo.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}🎉 Setup Completado. Ollama está listo para recibir peticiones.${NC}"
