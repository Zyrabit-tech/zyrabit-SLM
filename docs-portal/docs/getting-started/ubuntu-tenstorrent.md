---
sidebar_position: 2
title: Instalación Ubuntu + Tenstorrent P150A
description: Guía de despliegue de Zyrabit SLM en servidor Ubuntu Linux con tarjeta aceleradora PCIe Tenstorrent P150A (Wormhole RISC-V).
---

# Guía de Instalación: Ubuntu + Tenstorrent P150A (Wormhole)

Esta guía detalla los pasos para desplegar **Zyrabit SLM** en una máquina con sistema operativo **Ubuntu Linux** equipada con la tarjeta aceleradora de IA **Tenstorrent P150A** (arquitectura Wormhole PCIe RISC-V).

---

## 📋 Requisitos Previos del Sistema

### 1. Requisitos de Hardware

- **Procesador:** x86_64 o ARM64 (mínimo 4 núcleos)
- **RAM del Host:** 16 GB o superior (24 GB recomendado si ejecutas modelos de 7B)
- **Acelerador PCIe:** Tarjeta **Tenstorrent P150A** (16 GB TT-DDR6) instalada en ranura PCIe Gen4/Gen5 con alimentación auxiliar de 8 pines.
- **Ranura PCIe:** Verificar acceso al dispositivo `/dev/tenstorrent`.

### 2. Requisitos de Software (Ubuntu 22.04 LTS o 24.04 LTS)

- Ubuntu Linux 22.04 LTS o superior (64-bit / x86_64).
- Controladores KMD de Tenstorrent (`tenstorrent-kmd`) instalados.
- Docker Engine & Docker Compose V2.
- Herramienta Python `uv` (para aislamiento hermético).

> [!NOTE]
> **Si estás en Windows (PowerShell/CMD):**
> `uname` es un comando de Linux. Para verificar la arquitectura de tu procesador desde Windows antes de instalar Ubuntu:
>
> ```powershell
> (Get-CimInstance Win32_OperatingSystem).OSArchitecture
> # o ejecutando:
> $env:PROCESSOR_ARCHITECTURE
> ```
>
> Si devuelve `64-bit` o `AMD64`, tu equipo soporta Ubuntu 64-bit para la P150A.

---

## 🛠️ Paso 1: Verificación de la Tarjeta Tenstorrent P150A

Asegúrate de que Ubuntu reconozca la tarjeta PCIe y que los drivers KMD estén cargados:

```bash
# 1. Verificar presencia de la tarjeta en el bus PCIe (ID 1e52:f000 o similar)
lspci | grep -i tenstorrent

# 2. Confirmar existencia del nodo de dispositivo PCIe
ls -l /dev/tenstorrent*

# 3. Verificar estado de la tarjeta y temperatura mediante tt-smi (si está instalado)
tt-smi
```

> [!IMPORTANT]
> Si el dispositivo `/dev/tenstorrent` no existe, instala el controlador oficial del kernel de Tenstorrent ejecutando:
>
> ```bash
> sudo apt-get update && sudo apt-get install -y dkms build-essential
> git clone https://github.com/tenstorrent/tt-kmd.git
> cd tt-kmd && sudo make install
> sudo modprobe tenstorrent
> ```

---

## 🚀 Paso 2: Clonar el Repositorio Zyrabit SLM

```bash
# Clonar el proyecto
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
```

---

## ⚡ Paso 3: Instalación Interactiva (Modo Tenstorrent P150A)

Zyrabit incluye soporte nativo para aceleradores Tenstorrent en su script unificado `./zyra`:

```bash
# Iniciar el instalador/wizard interactivo
./zyra wizard
```

En el menú interactivo, selecciona los siguientes valores:

1. **Environment:** `1) Local / Dev` (o `2) Production` con tu dominio).
2. **Inference Engine:** Selecciona la opción **`5) Tenstorrent P150A / Wormhole`**.
3. **AI Model:** Selecciona el modelo deseado (ej. `qwen2.5:7b` o `qwen2.5:1.5b`).
4. **Database:** `1) SQLite WAL` (desarrollo) o `2) PostgreSQL` (producción).
5. **Whisper:** `1) Yes` si deseas transcripción de audio local con aceleración.

### Instalación Directa sin Wizard (Vía Banderas / Variables)

Si prefieres realizar la instalación automatizada desde la terminal o scripts CI/CD:

```bash
# Iniciar stack activando el perfil Tenstorrent
./zyra start --profile tenstorrent
```

---

## 🐋 Paso 4: Arquitectura del Contenedor Tenstorrent

Cuando se selecciona el perfil `tenstorrent`, Docker Compose levanta el servicio **`zyrabit-tt-metal`** definido en `docker-compose.yml`:

```yaml
  zyrabit-tt-metal:
    image: zyrabit-slm/tt-bridge
    container_name: zyrabit-tt-metal
    profiles: [ "tenstorrent" ]
    devices:
      - /dev/tenstorrent:/dev/tenstorrent
    ipc: host
    environment:
      - ZYRABIT_TT_MODE=metal
      - ZYRABIT_TT_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
    ports:
      - "8090:8090"
```

Este servicio:

- Monta directamente el dispositivo de hardware `/dev/tenstorrent` dentro del contenedor Linux.
- Utiliza la compilación TT-MLIR / TT-Metalium para ejecutar la inferencia de matrices sobre los núcleos RISC-V Tensix de la P150A.
- Expone la API OpenAI-compatible en el puerto local `8090`.

---

## ✅ Paso 5: Verificación de Salud y Pruebas

Una vez desplegado el stack, verifica la conectividad y el estado del acelerador:

```bash
# 1. Comprobar estado de los contenedores
./zyra verify

# 2. Consultar el endpoint de inferencia activado
curl http://localhost:8082/v1/health

# 3. Realizar una consulta de prueba a la API de Zyrabit
curl -X POST http://localhost:8082/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer zyrabit-local-token" \
  -d '{"text": "Hola Zyrabit, confirma que estás ejecutando inferencia sobre la tarjeta Tenstorrent P150A."}'
```

---

## 📊 Paso 6: Benchmarks de Rendimiento

Para medir los tokens por segundo (t/s) y la latencia del primer token (TTFT) en la P150A:

```bash
# Ejecutar benchmark live
./zyra benchmark
```

Los resultados reflejarán la aceleración de hardware en la tarjeta Tenstorrent sin consumo de CPU ni memoria RAM del host.
