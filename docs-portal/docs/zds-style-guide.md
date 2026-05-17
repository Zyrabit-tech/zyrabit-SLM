# 📝 Zyrabit Documentation Style Guide (ZDSG)

Esta guía establece el estándar para toda la documentación de Zyrabit SLM, garantizando que sea legible tanto para humanos como para IAs.

---

## 1. Estructura y Jerarquía
Toda página debe comenzar con un H1 (`#`) que incluya un emoji descriptivo.

### Ejemplo:
`# 🛡️ Seguridad Soberana`

---

## 2. Bloques de Código y Terminal
El estándar para ejemplos técnicos es vital para la reproducibilidad.

### Terminal (Interacción)
Usa el lenguaje `bash`. Si es un comando que el usuario debe ejecutar, usa el prefijo `$`.
```bash
$ ./zyra-up.sh start
```

### Logs o Salidas
No uses el prefijo `$`.
```text
[INFO] Zyrabit Core started on port 8080
[SUCCESS] Vector DB connection established
```

---

## 3. Alertas y Notas (GitHub Style)
Utilizamos el estándar de alertas de GitHub para resaltar información crítica.

> [!NOTE]
> Información útil o contexto adicional.

> [!WARNING]
> Advertencias sobre configuraciones que podrían fallar.

> [!CAUTION]
> Riesgos de pérdida de datos o brechas de seguridad.

---

## 4. Tipografía y Visuales
*   **Fuentes**: Títulos en `Funnel Display` y cuerpo en `Inter`.
*   **Código**: `JetBrains Mono`.
*   **Colores**: Basados en el branding Zyrabit (`#3f5a6d`, `#6090b4`).

---

## 5. Estrategia Multilingüe e i18n
Para soportar múltiples idiomas de forma soberana:

### Estructura de Directorios
Separamos por código de idioma ISO (2 letras):
- `docs/en/` (Source of truth)
- `docs/es/` (Traducción oficial)

### Implementación del Traductor (Zyra-AI Sync)
Proponemos un flujo automatizado:
1.  **Agente de Traducción**: Un script de Node/Python que lee los archivos Markdown.
2.  **Preservación de Estructura**: El agente traduce solo los textos narrativos, dejando intactos los bloques de código, diagramas de Mermaid y enlaces.
3.  **Localización**: El agente puede ajustar ejemplos (ej. cambiar una ruta `/Users/...` por `/home/...` según el idioma/contexto si es necesario).

---

## 6. AI-Readability (Optimización para LLMs)
Para que las IAs entiendan mejor nuestra documentación:
- **Descripciones en Imágenes**: Siempre usa el atributo `alt`.
- **Metadata**: Incluye un bloque front-matter en cada archivo con `description` y `tags`.
