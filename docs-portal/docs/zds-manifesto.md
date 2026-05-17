# Zyrabit Documentation Standard (ZDS)

Este documento define las reglas de oro para toda la documentación de la infraestructura Zyrabit. Seguimos los patrones de diseño de **Stripe** (interactividad), **Apple** (estética) y **OpenAI** (claridad AI-Native).

## 1. Estructura de Página
Cada documento debe seguir este orden:
1.  **Technical Summary**: Un bloque oculto o resumen breve para LLMs/Agentes.
2.  **Overview**: El "Por Qué" de la funcionalidad.
3.  **Quick Start**: El camino más corto al éxito (3 pasos máximo).
4.  **Deep Dive**: Detalles técnicos, diagramas y referencias.
5.  **Troubleshooting**: Errores comunes y cómo resolverlos.

## 2. Componentes Visuales
Utilizamos alertas de GitHub para enfatizar información:
- `> [!NOTE]`: Información de fondo o arquitectura.
- `> [!TIP]`: Atajos de productividad o mejores prácticas.
- `> [!IMPORTANT]`: Requerimientos críticos para la soberanía de los datos.
- `> [!WARNING]`: Acciones que podrían comprometer la privacidad o el rendimiento.

## 3. Estilo de Escritura
- **Voz**: Activa ("Configura el bot" en lugar de "El bot debe ser configurado").
- **Tono**: Arquitectónico y Seguro.
- **Claridad**: Evitar adjetivos innecesarios. Si algo es "rápido", demuéstralo con un benchmark, no lo digas.

## 4. AI-Native Ready
Cada página debe ser procesable por el **Model Context Protocol (MCP)**. Esto significa usar encabezados claros y metadatos en formato markdown.
