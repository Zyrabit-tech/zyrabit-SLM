---
sidebar_position: 2
title: Bare-Metal AI Server Setup
description: Guía técnica completa para desplegar Zyrabit SLM en hardware bare-metal con aceleradores de IA (Tenstorrent, NVIDIA, Apple Silicon). Incluye Ubuntu, Docker, certificados TLS opcionales y flujo de contribución open source.
---

# 🖥️ Bare-Metal AI Server Setup

> **Audiencia**: Ingenieros de infraestructura, DevOps y agentes de IA que necesitan desplegar Zyrabit SLM sobre hardware físico con aceleradores de IA especializados.

Esta guía cubre el ciclo completo: desde hardware sin configurar hasta un servidor de IA soberano corriendo en producción local — y cómo contribuir esa experiencia de vuelta al proyecto.

---

## Prerequisitos de hardware

| Componente | Mínimo recomendado | Notas |
|---|---|---|
| CPU | x86_64, 8+ cores | AMD Ryzen / Intel Core moderno |
| RAM | 16 GB | 32 GB para modelos 13B+ |
| Disco | 500 GB SSD | 2TB+ para modelos grandes |
| Acelerador | Tenstorrent / NVIDIA / Apple M-series | CPU-only también funciona |
| Red | Ethernet (recomendado) | WiFi funciona pero no ideal |

### Aceleradores soportados

| Acelerador | Detección automática | URL interna |
|---|---|---|
| NVIDIA GPU | `nvidia-smi` disponible | Ollama en Docker |
| Tenstorrent (P150 Blackhole, etc.) | `/dev/tenstorrent` o `tt-smi` | `http://zyrabit-tt-bridge:8000` |
| Apple Silicon (M1/M2/M3) | macOS + arm64 | `http://host.docker.internal:11434` |
| CPU only | Fallback automático | Ollama en Docker |

:::note Detección automática
`zyra-up.sh` detecta el hardware al arrancar y configura los servicios correctamente. No necesitas especificar el acelerador manualmente.
:::

---

## Fase 1 — Instalar Ubuntu Server/Desktop

### 1.1 Descargar Ubuntu

Desde otra computadora descarga **Ubuntu 24.04 LTS** (la versión más estable):
- Desktop (con interfaz gráfica): [ubuntu.com/download/desktop](https://ubuntu.com/download/desktop)
- Server (sin interfaz, más ligero): [ubuntu.com/download/server](https://ubuntu.com/download/server)

### 1.2 Crear USB de arranque

**En macOS:**
```bash
# Descarga BalenaEtcher
# https://etcher.balena.io/
# Selecciona el .iso de Ubuntu y tu USB (mínimo 8 GB)
```

**En Windows:**
```
Descarga Rufus desde: https://rufus.ie/
Selecciona el .iso de Ubuntu y tu USB
Modo: GPT + UEFI (recomendado para hardware moderno)
```

### 1.3 Arrancar desde USB

1. Conecta el USB a tu servidor
2. Enciende la máquina y presiona repetidamente **F2** o **F8** (ASUS ROG, MSI) o **DEL** (otras tarjetas)
3. En el menú de arranque (Boot Menu), selecciona tu USB
4. Elige **"Install Ubuntu"** en el asistente

### 1.4 Configuración de instalación recomendada

| Opción | Recomendado |
|---|---|
| Tipo de instalación | Minimal (para servidores) |
| Partición | Usar todo el disco (LVM recomendado) |
| Usuario | Crear usuario con contraseña fuerte |
| SSH | ✅ Activar OpenSSH Server |
| Actualizaciones automáticas | A criterio (desactivar en servidores de producción) |

---

## Fase 2 — Preparar el sistema

### 2.1 Actualizar el sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.2 Instalar Docker

Docker es el motor que corre todos los servicios de Zyrabit:

```bash
# Instalación oficial (un solo comando)
curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh

# Agregar tu usuario al grupo docker (evita usar sudo en cada comando)
sudo usermod -aG docker $USER

# Aplicar cambios de grupo sin cerrar sesión
newgrp docker

# Verificar que funciona
docker run hello-world
```

### 2.3 Instalar `uv` (gestor de Python)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Recargar el PATH
source $HOME/.local/bin/env

# Verificar
uv --version
```

### 2.4 Instalar drivers del acelerador

:::info Tenstorrent (P150 Blackhole y otros)
Consulta la documentación oficial de Tenstorrent para instalar los drivers de kernel y `tt-smi`:
- [Tenstorrent TT-Metalium Setup](https://github.com/tenstorrent/tt-metal)
- [TT-SMI (System Management Interface)](https://github.com/tenstorrent/tt-smi)

```bash
# Verificar que el hardware es detectado
tt-smi

# El dispositivo debe aparecer en:
ls /dev/tenstorrent
```
:::

:::info NVIDIA GPU
```bash
# Ubuntu detecta NVIDIA automáticamente. Para instalar drivers:
sudo apt install nvidia-driver-535  # o la versión más reciente

# Verificar
nvidia-smi
```
:::

---

## Fase 3 — Desplegar Zyrabit SLM

### 3.1 Clonar el repositorio

```bash
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
```

### 3.2 Configurar el entorno

```bash
# Copiar el archivo de configuración de ejemplo
cp zyrabit-slm/example.env zyrabit-slm/.env

# Editar con tus valores (mínimo requerido para modo local):
nano zyrabit-slm/.env
```

Variables clave en `.env`:

```bash
# Modo de operación
APP_ENV=local

# Autenticación básica para Prometheus y Grafana
# Formato: usuario:contraseña (texto plano en modo local)
PROMETHEUS_BASIC_AUTH=admin:changeme
GRAFANA_BASIC_AUTH=admin:changeme

# Paralelismo del motor de inferencia
OLLAMA_NUM_PARALLEL=2

# Para Tenstorrent — descomenta si usas P150 u otro chip TT
# SLM_URL=http://zyrabit-tt-bridge:8000
```

### 3.3 Arrancar el stack (modo local por defecto)

```bash
# Sin argumentos = modo local (HTTP, puerto 8080, sin SSL)
./zyra-up.sh

# Equivalente explícito:
./zyra-up.sh install --local
```

El script realiza automáticamente:
1. Detecta tu hardware (RAM, CPU, acelerador)
2. Selecciona el modelo de IA apropiado según tu RAM
3. Construye las imágenes Docker
4. Levanta todos los contenedores
5. Descarga los modelos de IA
6. Verifica la salud del stack

### 3.4 Verificar que todo funciona

```bash
./zyra-up.sh verify
```

Accede a los servicios desde tu navegador:

| Servicio | URL (modo local) |
|---|---|
| Web UI | http://localhost:3000 |
| API | http://localhost:8080/v1 |
| Grafana | http://localhost:3001 |
| DB Admin | http://localhost:8000 |

### 3.5 Comandos útiles del día a día

```bash
# Detener el stack
./zyra-up.sh stop

# Solo levantar (sin descargar modelos de nuevo)
./zyra-up.sh start

# Diagnóstico del entorno
./zyra-up.sh doctor

# Ejecutar validación soberana (PII + Air-Gap)
./zyra-up.sh validate --e2e-security

# Desarrollo nativo con hot-reload
./zyra-up.sh dev
```

---

## Fase 4 — Modo producción con HTTPS (opcional)

:::caution Requiere dominio y certificados
El modo producción usa Traefik como reverse proxy con SSL. Solo actívalo si tienes un dominio apuntando a tu servidor o si generas certificados autofirmados.
:::

### 4.1 Opción A — Certificados autofirmados (desarrollo seguro)

```bash
# Crear directorio para certificados
mkdir -p zyrabit-slm/certs

# Generar certificado autofirmado (válido 365 días)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout zyrabit-slm/certs/key.pem \
  -out zyrabit-slm/certs/cert.pem \
  -subj "/C=US/ST=Local/L=Local/O=Zyrabit/CN=localhost"

# Arrancar en modo producción con tu certificado
./zyra-up.sh install --production
```

Los servicios estarán disponibles en `https://localhost`. El navegador mostrará una advertencia de certificado no confiable — esto es normal para certificados autofirmados. Puedes ignorarla en desarrollo local.

### 4.2 Opción B — Certificados reales con Let's Encrypt

Requiere un dominio público apuntando a tu servidor:

```bash
# Instalar certbot
sudo apt install certbot

# Obtener certificado (detén temporalmente cualquier servicio en puerto 80)
sudo certbot certonly --standalone -d tu-dominio.com

# Los certificados quedan en:
# /etc/letsencrypt/live/tu-dominio.com/fullchain.pem
# /etc/letsencrypt/live/tu-dominio.com/privkey.pem

# Copiar al directorio de Zyrabit
sudo cp /etc/letsencrypt/live/tu-dominio.com/fullchain.pem zyrabit-slm/certs/cert.pem
sudo cp /etc/letsencrypt/live/tu-dominio.com/privkey.pem zyrabit-slm/certs/key.pem

# Arrancar en modo producción
./zyra-up.sh install --production --domain tu-dominio.com
```

### 4.3 Verificar HTTPS

```bash
./zyra-up.sh verify
# La verificación de API usa https://localhost/v1/health automáticamente en modo producción
```

---

## Fase 5 — Contribuir al proyecto (Open Source)

Si instalaste Zyrabit en hardware especializado (Tenstorrent, NVIDIA, arquitecturas ARM), tu experiencia es valiosa para la comunidad.

### 5.1 Flujo de contribución (branching versionado)

Zyrabit usa un sistema de **ramas beta versionadas**. Cada ciclo de release tiene su propia rama:

```
main  ──────────────── ◉ v2.2.3
         ▲
    beta-2.3.0  ← rama de staging del release
         ▲
    feature/tu-mejora
```

**Pasos para contribuir:**

```bash
# 1. Fork del repositorio en GitHub (botón "Fork" arriba a la derecha)

# 2. Clonar tu fork
git clone https://github.com/TU-USUARIO/zyrabit-SLM.git
cd zyrabit-SLM

# 3. Identificar la beta activa (mira las ramas en GitHub)
git fetch --all
git branch -r | grep beta

# 4. Crear tu rama desde la beta activa
git checkout -b feature/guia-tenstorrent-p150 origin/beta-2.3.0

# 5. Hacer tus cambios, commits, etc.
git add .
git commit -m "docs: add Tenstorrent P150 setup guide"

# 6. Push de tu rama
git push origin feature/guia-tenstorrent-p150
```

### 5.2 Abrir el Pull Request

En GitHub, abre un PR desde `feature/guia-tenstorrent-p150` → `beta-2.3.0` (no directamente a `main`).

:::important Regla de branching
Los PRs **directos a `main`** son rechazados automáticamente por el CI.  
El flujo correcto es: `feature/*` → `beta-X.Y.Z` → `main`
:::

### 5.3 Qué documentar en tu contribución

Si instalaste en hardware nuevo, crea un archivo en `docs-portal/docs/hardware/`:

```markdown
# Guía: Tenstorrent P150 Blackhole en Ubuntu 24.04

## Hardware del entorno
- CPU: ...
- RAM: ...
- Acelerador: Tenstorrent P150 Blackhole

## Errores encontrados y soluciones
1. Error: `tt-smi: command not found`
   Solución: ...

## Resultado final
- Modelo: qwen2.5:7b
- TTFT promedio: ~X segundos
- Estabilidad: X horas sin errores
```

---

## Solución de problemas comunes

### Docker no arranca

```bash
# Verificar que el daemon está corriendo
sudo systemctl status docker

# Iniciarlo si está detenido
sudo systemctl start docker
sudo systemctl enable docker  # Para que arranque con el sistema
```

### Puerto 8080 ocupado

```bash
# Ver qué proceso usa el puerto
sudo lsof -i :8080

# Matar el proceso (reemplaza PID)
sudo kill -9 <PID>
```

### El modelo de IA es muy lento

```bash
# Verificar que el acelerador es detectado
./zyra-up.sh doctor

# Si tienes NVIDIA y no se detecta:
nvidia-smi  # Debe mostrar info de la GPU

# Si tienes Tenstorrent:
ls /dev/tenstorrent  # Debe existir el dispositivo
tt-smi               # Debe mostrar el chip
```

### Memoria insuficiente

El script selecciona automáticamente el modelo según tu RAM:

| RAM disponible | Modelo seleccionado |
|---|---|
| < 12 GB | `qwen2.5:1.5b` |
| ≥ 12 GB | `qwen2.5:7b` (por defecto) |

Para usar un modelo diferente:
```bash
./zyra-up.sh install --model llama3.2:3b
```

---

## Referencia rápida de comandos

```bash
# Arranque estándar (local, sin SSL)
./zyra-up.sh

# Arranque en producción (HTTPS)
./zyra-up.sh --production

# Solo el stack (sin descargar modelos)
./zyra-up.sh start

# Detener todo
./zyra-up.sh stop

# Diagnóstico
./zyra-up.sh doctor

# Validación soberana completa
./zyra-up.sh validate --e2e-security

# Modo desarrollo (hot-reload)
./zyra-up.sh dev

# Ayuda
./zyra-up.sh help
```
