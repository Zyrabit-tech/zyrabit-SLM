🤝 Cómo Contribuir a RAG-Stack-Local

¡Gracias por tu interés en contribuir! Este proyecto es open-source porque creemos en el poder de la comunidad.

Para mantener la armonía, la calidad del código y la sanidad mental de los maintainers (¡y la tuya!), hemos establecido un conjunto de guías. El objetivo no es la burocracia, es facilitar la revisión y la integración de tu increíble trabajo.

🧠 Filosofía de Contribución

Un PR, Un Propósito: Cada Pull Request (PR) debe resolver un problema o agregar una funcionalidad. PRs gigantes que hacen 10 cosas a la vez serán (amablemente) rechazados.

La Calidad no es Negociable: Un PR sin pruebas o que rompe las existentes no será mergeado. (Lee la sección de Pruebas en el README.md).

Comunica Primero, Programa Después: Si planeas una feature grande o un refactor complejo, abre un Issue primero. Discutamos el enfoque antes de que inviertas horas de código.

🚀 El Flujo de Trabajo: El Camino a beta

Tenemos un flujo estricto para proteger la estabilidad. La rama main representa la última versión estable, y NADIE pushea o hace PRs directamente a ella.

La rama de integración es beta.

⚠️ ADVERTENCIA: NUNCA HAGAS UN PULL REQUEST A main ⚠️
Todo PR que apunte a main será cerrado automáticamente.

Tu flujo de trabajo debe ser:

Haz Fork: Crea un fork del repositorio a tu propia cuenta de GitHub.

Clona tu Fork: git clone https://github.com/TU_USUARIO/RAG-Stack-Local.git

Configura el Upstream: (Solo lo haces una vez)

cd RAG-Stack-Local
git remote add upstream [https://github.com/USUARIO_ORIGINAL/RAG-Stack-Local.git](https://github.com/USUARIO_ORIGINAL/RAG-Stack-Local.git)


Sincroniza tu Fork: Antes de empezar a programar, asegúrate de tener lo último de beta.

git fetch upstream
git checkout beta
git pull upstream beta


Crea tu Rama: Crea tu rama de feature a partir de beta.

git checkout -b mi-feature-genial


Programa y Commitea: Haz tu magia. Usa la Convención de Commits (ver abajo).

Push a tu Fork:

git push -u origin mi-feature-genial


Abre el Pull Request:

Ve a GitHub y abre un PR.

La rama base debe ser beta.

La rama de comparación debe ser mi-feature-genial.

Llena la Plantilla de PR con detalle.

💬 Convención de Commits

Para mantener un historial limpio y legible (y facilitar los changelogs), usamos Conventional Commits. Es simple:

Tu commit DEBE tener este formato:
tipo(ámbito): descripción corta

tipo: feat (nueva feature), fix (bug fix), docs (documentación), style (formato, linting), refactor (no añade feature ni arregla bug), test (añadir o corregir pruebas), chore (tareas de build, scripts, etc.).

(ámbito) (Opcional): La parte del código afectada. (ej. api, docker, ingest, readme).

descripción: En minúsculas, en imperativo ("agrega", "corrige", "actualiza").

Ejemplos:

feat(api): agrega endpoint /v1/query

fix(ingest): corrige el parseo de PDFs con imágenes

docs(contributing): añade plantilla de PR

refactor(api): simplifica la lógica de formateo del prompt

test(api): añade pruebas unitarias para el servicio de RAG

📋 Plantilla de Pull Request

Un PR es tu carta de presentación al maintainer. Véndele tu solución. Un PR vacío será ignorado.

Usa esta plantilla (estará en el PR automáticamente) y llénala.

(Ejemplo de Plantilla de PR LLENADA)

Título del PR: fix(api): Corrige el manejo de errores 500 en /query

Cuerpo del PR:

¿Qué hace este PR?

Este PR intercepta excepciones generales (como ValueError o fallos de conexión con Chroma) en el endpoint /query y devuelve una respuesta JSON HTTP 500 estandarizada, en lugar de crashear el worker de uvicorn.

¿Por qué es necesario?

Actualmente, si la VectorDB está caída, el API crashea y devuelve un error de conexión genérico al cliente. Esto rompe el contrato del API.
Resuelve el Issue: #42

¿Cómo se probó?

[x] Pruebas Unitarias (Pytest)

[ ] Pruebas de Integración

[x] Manualmente (describe cómo)

Levanté el stack (docker compose up).

Maté el contenedor vector-db (docker stop vector-db).

Hice un curl al endpoint /query.

Verifiqué que recibo un JSON {"error": "Error interno del servidor"} y un código 500.

Checklist

[x] Mis commits siguen la convención del proyecto.

[x] Mi código sigue las buenas prácticas del README.md.

[x] Agregué o actualicé las pruebas necesarias.

[x] La documentación (docs, README) está actualizada.

[x] Mi PR apunta a la rama beta (¡NO A main!).

🆘 ¿Atorado? ¡Pide Ayuda! (El "How-To Zyrabit")

¿Atorado con Git? ¿No entiendes el flujo? ¿Confundido sobre cómo probar tu cambio?

No sufras en silencio.

El peor PR es el que nunca se hace. Si tienes una idea pero estás bloqueado por el proceso, haz una de estas dos cosas:

Abre un Issue: Crea un Issue con el label [pregunta] o [ayuda] y describe tu problema.

Crea un Draft PR: Abre tu Pull Request (incluso si no está terminado) y márcalo como "Draft". En la descripción, explica dónde estás atorado.

Estamos aquí para construir juntos.