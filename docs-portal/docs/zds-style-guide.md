---
sidebar_position: 2
title: 'Documentation Style Guide'
description: 'Writing standards and formatting conventions for Zyrabit documentation'
---

# 📝 Zyrabit Documentation Style Guide (ZDSG)

This guide establishes the standard for all Zyrabit SLM documentation, ensuring it is readable by both humans and AIs.

---

## 1. Structure and Hierarchy
Every page must start with an H1 (`#`) that includes a descriptive emoji.

### Example:
`# 🛡️ Sovereign Security`

---

## 2. Code Blocks and Terminal
The standard for technical examples is vital for reproducibility.

### Terminal (Interaction)
Use the `bash` language. If it is a command the user must execute, use the `$` prefix.
```bash
$ ./zyra.sh start
```

### Logs or Outputs
Do not use the `$` prefix.
```text
[INFO] Zyrabit Core started on port 8080
[SUCCESS] Vector DB connection established
```

---

## 3. Alerts and Notes (GitHub Style)
We use the GitHub alerts standard to highlight critical information.

> [!NOTE]
> Useful information or additional context.

> [!WARNING]
> Warnings about configurations that might fail.

> [!CAUTION]
> Risks of data loss or security breaches.

---

## 4. Typography and Visuals
*   **Fonts**: Titles in `Funnel Display` and body in `Inter`.
*   **Code**: `JetBrains Mono`.
*   **Colors**: Based on Zyrabit branding (`#3f5a6d`, `#6090b4`).

---

## 5. Multilingual Strategy and i18n
To support multiple languages in a sovereign way:

### Directory Structure
We separate by ISO language code (2 letters):
- `docs/en/` (Source of truth)
- `docs/es/` (Official translation)

### Translator Implementation (Zyra-AI Sync)
We propose an automated flow:
1.  **Translation Agent**: A Node/Python script that reads the Markdown files.
2.  **Structure Preservation**: The agent translates only the narrative texts, leaving code blocks, Mermaid diagrams, and links intact.
3.  **Localization**: The agent can adjust examples (e.g., changing a path `/Users/...` to `/home/...` depending on the language/context if necessary).

---

## 6. AI-Readability (Optimization for LLMs)
For AIs to better understand our documentation:
- **Image Descriptions**: Always use the `alt` attribute.
- **Metadata**: Include a front-matter block in each file with `description` and `tags`.
