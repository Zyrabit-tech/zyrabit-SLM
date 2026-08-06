# Ollama vs llama.cpp/Metal — carga, recuperación y respuesta

Fecha: 2026-08-06. Hardware: MacBook Pro M1 Pro, 16 GB de memoria unificada, GPU Metal de 14 núcleos.

## Flujo validado

1. Se subió `demo-brief.txt` al endpoint local `/v1/ingest`.
2. Zyrabit lo dividió, generó embeddings y lo persistió en Chroma 1.5.9; la API respondió `indexed and ready for retrieval`.
3. Se usó el mismo contenido y la misma pregunta en ambos motores: “What are the three priorities?”
4. Ambos devolvieron las tres prioridades correctas: ingestión, respuestas con fuentes y despliegue local-first.

## Configuración

| Ruta | Modelo | Aceleración |
| --- | --- | --- |
| Ollama | `qwen2.5:1.5b` (986 MB) | Metal a través de Ollama local |
| llama.cpp | `qwen2.5-1.5b-instruct-q4_k_m.gguf` (940 MB) | `llama-server`, 99 capas GPU, Metal |

No son pesos binariamente idénticos, pero sí la misma familia y tamaño de modelo. La comparación sirve para la decisión operativa, no como prueba científica de cuantización idéntica.

## Pasada caliente (misma pregunta, 64 tokens de prompt)

| Métrica | Ollama | llama.cpp / Metal |
| --- | ---: | ---: |
| Tokens de salida | 29 | 29 |
| Prompt tokens/s | 757.7 | 203.1 |
| Generación tokens/s | 88.8 | 92.9 |
| Tiempo de generación | 326.5 ms | 312.3 ms |
| Tiempo total reportado | 624.4 ms | 627.3 ms aprox. |

## Primera pasada

Ollama reportó 2.55 s de total, de los cuales 1.84 s fueron carga de modelo. llama.cpp se inició y cargó el modelo antes de recibir la consulta; por eso su primer request no debe compararse como TTFT frío directo.

## Resultado

Para este modelo y hardware, llama.cpp/Metal entrega generación ligeramente más rápida en caliente (92.9 vs 88.8 tokens/s). La diferencia es pequeña: Ollama sigue siendo la ruta principal más simple y administrable. `llama_cpp_server` queda como alternativa nativa de Metal en el wizard de `./zyra.sh`.
