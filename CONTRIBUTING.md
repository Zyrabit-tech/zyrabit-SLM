# 🤝 Cómo Contribuir a Zyrabit SLM

¡Gracias por tu interés en contribuir! Este proyecto es open-source porque creemos en el poder de la comunidad.

Para mantener la armonía, la calidad del código y la sanidad mental de los maintainers (¡y la tuya!), hemos establecido un conjunto de guías. El objetivo no es la burocracia, es facilitar la revisión y la integración de tu increíble trabajo.

## 🧠 Filosofía de Contribución

*   **Un PR, Un Propósito**: Cada Pull Request (PR) debe resolver un problema o agregar una funcionalidad. PRs gigantes que hacen 10 cosas a la vez serán (amablemente) rechazados.
*   **La Calidad no es Negociable**: Un PR sin pruebas o que rompe las existentes no será mergeado.
*   **Comunica Primero, Programa Después**: Si planeas una feature grande o un refactor complejo, abre un Issue primero. Discutamos el enfoque antes de que inviertas horas de código.

## 🚀 El Flujo de Trabajo: El Camino a beta

Tenemos un flujo estricto para proteger la estabilidad. La rama `main` representa la última versión estable, y NADIE pushea o hace PRs directamente a ella.

La rama de integración es `beta`.

> [!WARNING]
> **NUNCA HAGAS UN PULL REQUEST A `main`**
> Todo PR que apunte a `main` será cerrado automáticamente.

Tu flujo de trabajo debe ser:

1.  **Haz Fork**: Crea un fork del repositorio a tu propia cuenta de GitHub.
2.  **Clona tu Fork**:
    ```bash
    git clone https://github.com/TU_USUARIO/zyrabit-SLM.git
    ```
3.  **Configura el Upstream** (Solo lo haces una vez):
    ```bash
    cd zyrabit-SLM
    git remote add upstream https://github.com/Zyrabit-tech/zyrabit-SLM.git
    ```
4.  **Sincroniza tu Fork**: Antes de empezar a programar, asegúrate de tener lo último de `beta`.
    ```bash
    git fetch upstream
    git checkout beta
    git pull upstream beta
    ```
5.  **Crea tu Rama**: Crea tu rama de feature a partir de `beta`.
    ```bash
    git checkout -b mi-feature-genial
    ```
6.  **Programa y Commitea**: Haz tu magia. Usa la Convención de Commits (ver abajo).
7.  **Push a tu Fork**:
    ```bash
    git push -u origin mi-feature-genial
    ```
8.  **Abre el Pull Request**:
    *   Ve a GitHub y abre un PR.
    *   La rama base debe ser **`beta`**.
    *   La rama de comparación debe ser `mi-feature-genial`.
    *   Llena la Plantilla de PR con detalle.

## 💬 Convención de Commits

Para mantener un historial limpio y legible, usamos **Conventional Commits**.

> [!IMPORTANT]
> **Todos los commits DEBEN estar en inglés**. Esto facilita la colaboración internacional y mantiene consistencia con el código.

Tu commit DEBE tener este formato:
`type(scope): short description`

*   **type**: `feat` (new feature), `fix` (bug fix), `docs` (documentation), `style` (formatting), `refactor` (code), `test` (tests), `chore` (maintenance).
*   **(scope)** (Optional): `api`, `docker`, `ingest`, `readme`, etc.
*   **description**: Lowercase, imperative ("add", "fix", "update").

**Ejemplos:**
*   `feat(api): add /v1/ingest endpoint`
*   `fix(ingest): fix PDF validation`
*   `docs(contributing): update project name`
*   `test(security): add PII sanitization tests`

## 📝 Estándares de Código

### Nomenclatura (Naming Conventions)

> [!IMPORTANT]
> **Todo el código debe estar en inglés**: variables, funciones, clases, comentarios de documentación.

**Variables y Funciones**: Usa `snake_case` en inglés
*   ✅ `user_input`, `sanitize_data()`, `process_pdf_file()`
*   ❌ `entrada_usuario`, `sanitizarDatos()`, `procesarArchivoPDF()`

**Clases**: Usa `PascalCase` en inglés
*   ✅ `VectorDatabase`, `SecureAgent`, `OllamaClient`
*   ❌ `BaseDeDatosVectorial`, `AgenteSeguro`

**Diccionarios y Configuración**: Usa `snake_case` para las keys
```python
# ✅ Correcto
config = {
    "model_name": "phi3",
    "max_tokens": 1000,
    "enable_sanitization": True
}

# ❌ Incorrecto
config = {
    "nombreModelo": "phi3",
    "maxTokens": 1000
}
```

**Comentarios**:
*   Docstrings (documentación de funciones/clases): **Obligatorio en inglés**
*   Comentarios inline: Preferiblemente en inglés, pero se permite español para claridad interna

### Seguridad de Dependencias

Antes de agregar una nueva dependencia a `requirements.txt`, **debes verificar su seguridad**:

```bash
# Instalar herramientas de seguridad
pip install pip-audit safety

# Escanear dependencias actuales
pip-audit
safety check

# Verificar una dependencia específica antes de agregarla
pip install <nueva-dependencia>
pip-audit
```

**Requisitos para PRs que agregan dependencias:**
- [ ] Ejecutar `pip-audit` y `safety check`
- [ ] Incluir resultados del escaneo en la descripción del PR
- [ ] Justificar por qué la dependencia es necesaria
- [ ] Verificar que no haya vulnerabilidades conocidas

## 📋 Plantilla de Pull Request

Un PR es tu carta de presentación. Véndele tu solución.

**Checklist Básico:**
- [ ] Mis commits siguen la convención.
- [ ] Mi código sigue las buenas prácticas.
- [ ] Agregué o actualicé las pruebas necesarias.
- [ ] La documentación está actualizada.
- [ ] Mi PR apunta a la rama **`beta`**.

## 🆘 ¿Atorado?

No sufras en silencio.
*   **Abre un Issue**: Con el label `pregunta` o `ayuda`.
*   **Crea un Draft PR**: Y explica dónde estás atorado.

Estamos aquí para construir juntos.