# Contribuir a Zyrabit SLM (ES)

[English version](CONTRIBUTING_EN.md)

## Reglas base

- Toda contribución entra por Pull Request.
- La rama base del PR debe ser `beta`.
- No se aceptan PRs directos a `main`.
- Código, variables y commits en inglés.
- Un PR = un propósito claro.

## Flujo recomendado

1. Haz fork y clona.
2. Configura upstream.
3. Sincroniza `beta`.
4. Crea rama desde `beta`.
5. Implementa cambios + pruebas.
6. Abre PR hacia `beta`.

Comandos:

```bash
git clone https://github.com/TU_USUARIO/zyrabit-SLM.git
cd zyrabit-SLM
git remote add upstream https://github.com/Zyrabit-tech/zyrabit-SLM.git
git fetch upstream
git checkout beta
git pull upstream beta
git checkout -b feat/mi-cambio
```

## Convención de commits

Formato obligatorio:

```text
type(scope): short description
```

Tipos válidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

Ejemplos:

- `feat(api): add chat metadata for route decision`
- `fix(security): prevent pii leak in model payload`
- `docs(readme): add ui verification guide`

## Checklist para abrir PR

- [ ] PR apunta a `beta`.
- [ ] Tests pasan localmente.
- [ ] Documentación actualizada (ES/EN cuando aplique).
- [ ] Sin secretos en commits.
- [ ] Commit messages en formato convencional.

## Verificación local mínima

```bash
./.venv/bin/python -m pytest -q -c zyrabit-brain-api/api-rag/pytest.ini
streamlit run slm_console.py
./scripts/run_final_tests.sh
```

Checklist extendido: `validation/pr-checklist.md`

## Seguridad de dependencias

Antes de agregar librerías:

```bash
pip install pip-audit
pip-audit
```

Si agregas dependencias, documenta en el PR:

- justificación técnica,
- impacto esperado,
- resultado del escaneo.

## GitHub Actions

Los workflows validan automáticamente:

- política de contribución (base `beta`),
- pruebas en `api-rag`,
- auditoría de dependencias.

Si CI falla, corrige antes de pedir review.
