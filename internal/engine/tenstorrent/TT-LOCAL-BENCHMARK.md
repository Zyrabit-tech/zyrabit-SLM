# Hoja de Ruta de Validación: Zyrabit Tenstorrent Bridge Local

Este documento define la estrategia y los protocolos de prueba para validar el pipeline de inferencia local utilizando el simulador de hardware (Golden Model) de Tenstorrent para el modelo **Qwen 2.5 1.5B**.

## 1. Arquitectura del Bridge (`tt-forge` a `tt-mlir`)

El flujo de ejecución de nuestro `zyrabit-tt-bridge` se encarga de traducir los grafos dinámicos de PyTorch hacia instrucciones ejecutables por la arquitectura de Tenstorrent:

1. **Intercepción y Lowering (StableHLO)**: Mediante `torch_xla`, capturamos el grafo de cómputo del modelo y lo reducimos a la representación intermedia estándar StableHLO.
2. **Delegación al Compilador (`tt-forge`)**: Configuramos el entorno (`PJRT_DEVICE=TT`) para que el backend XLA envíe las operaciones a `tt-forge`, el framework de compilación de Tenstorrent.
3. **Conversión a `tt-mlir`**: El compilador transforma el StableHLO en el dialecto específico `tt-mlir`, optimizando la distribución de tensores en la grilla Tensix y la alocación entre SRAM (L1) y DRAM.
4. **Simulación (Golden Model)**: Con `INFERENCE_PROVIDER=tt-forge-sim`, el binario final `.tt` se ejecuta en un entorno emulado en CPU que calcula de forma precisa los tiempos y comportamientos del silicio real.

## 2. Protocolo de Pruebas

### Test 1: Compilación de Grafo
- **Objetivo**: Medir el tiempo de preprocesamiento (compilación local) hacia binarios Tenstorrent.
- **Configuración**: `XLA_STABLEHLO_COMPILE=1`, Qwen 2.5 1.5B en `bfloat16`.
- **Métrica**: Tiempo de carga (Cold-start) para generar el archivo ejecutable.

### Test 2: Inferencia en Simulador (Golden Model)
- **Objetivo**: Determinar el rendimiento base (Cycle Counts) que obtendremos en hardware físico.
- **Configuración**: Ejecución de inferencia usando `torch_xla.sync(wait=True)` para asegurar barreras asíncronas correctas en la medición.
- **Métrica**: Ciclos reportados en los logs por token generado.

### Test 3: Integridad de Datos (Zero-Trust PII Guard)
- **Objetivo**: Asegurar que las rutinas de ofuscación o enmascaramiento PII actúen correctamente en el tensor ANTES de enviarse al simulador/hardware.
- **Configuración**: Evaluación con un prompt contaminado.
- **Métrica**: Verificación en la salida final sin corromper la dimensión de los tensores ni filtrar PII real en los logs.

## 3. Métricas de Referencia (Qwen 2.5 1.5B - bfloat16)

| Métrica | Valor Proyectado (Simulador TT) | Notas / Observaciones |
| :--- | :--- | :--- |
| **Tiempo de Compilación** | *[Pendiente]* s | Tiempo desde carga en XLA hasta compilación exitosa |
| **Consumo SRAM Estimado** | *[Pendiente]* MB | Memoria on-chip requerida por núcleos L1 |
| **Consumo DRAM Estimado** | *[Pendiente]* GB | Uso de memoria total (Pesos en bfloat16 + KV Cache) |
| **Cycle Counts (Total)** | *[Pendiente]* | Total de ciclos de reloj para un pase forward |
| **Latencia Estimada** | *[Pendiente]* ms/token | Calculado basado en frecuencia base de tarjeta target |

---
*Nota: Estos valores representan el techo teórico extraído del Golden Model en la Mac, previo al despliegue en host Linux con PCIe real.*
