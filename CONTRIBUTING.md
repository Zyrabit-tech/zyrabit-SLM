# 🤝 Cómo Contribuir a Zyrabit LLM

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
    git clone https://github.com/TU_USUARIO/zyrabit-llm.git
    ```
3.  **Configura el Upstream** (Solo lo haces una vez):
    ```bash
    cd zyrabit-llm
    git remote add upstream https://github.com/Zyrabit-tech/zyrabit-llm.git
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

Tu commit DEBE tener este formato:
`tipo(ámbito): descripción corta`

*   **tipo**: `feat` (nueva feature), `fix` (bug fix), `docs` (documentación), `style` (formato), `refactor` (código), `test` (pruebas), `chore` (mantenimiento).
*   **(ámbito)** (Opcional): `api`, `docker`, `ingest`, `readme`, etc.
*   **descripción**: En minúsculas, imperativo ("agrega", "corrige").

**Ejemplos:**
*   `feat(api): agrega endpoint /v1/ingest`
*   `fix(ingest): corrige validación de PDFs`
*   `docs(contributing): actualiza nombre del proyecto`

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