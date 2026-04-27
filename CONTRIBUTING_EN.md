# Contributing to Zyrabit SLM (EN)

[Versión en español](CONTRIBUTING.md)

## Ground rules

- All contributions go through Pull Requests.
- PR base branch must be `beta`.
- Direct PRs to `main` are not accepted.
- Only `beta` can open a PR into `main`.
- **Python Version**: Strictly **Python 3.12**. (3.14+ is currently incompatible with RAG dependencies).
- **KISS Principle**: Favor simple, readable solutions over complex abstractions.
- **Clean Git Tree**: Maintain linear history; feature branches must sync with `beta` before merging.
- Code, variables, and commits must be in English.
- One PR = one clear purpose.

## Recommended workflow

1. Fork and clone.
2. Add upstream.
3. Sync `beta`.
4. Create branch from `beta`.
5. Implement changes + tests.
6. Open PR targeting `beta`.

Commands:

```bash
git clone https://github.com/YOUR_USER/zyrabit-SLM.git
cd zyrabit-SLM
git remote add upstream https://github.com/Zyrabit-tech/zyrabit-SLM.git
git fetch upstream
git checkout beta
git pull upstream beta
git checkout -b feat/my-change
```

## Commit convention

Required format:

```text
type(scope): short description
```

Allowed types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

Examples:

- `feat(api): add chat metadata for route decision`
- `fix(security): prevent pii leak in model payload`
- `docs(readme): add ui verification guide`

## PR checklist

- [ ] PR targets `beta`.
- [ ] Tests pass locally.
- [ ] Documentation updated (ES/EN when applicable).
- [ ] No secrets committed.
- [ ] Commit messages follow Conventional Commits.

## Minimum local verification

```bash
./.venv/bin/python -m pytest -q -c zyrabit-slm/api-rag/pytest.ini
python secure_agent.py "Test query"
./zyrabit-slm/scripts/build_and_verify.sh
```

Extended checklist: `validation/pr-checklist.md`

## Infrastructure Standards

To maintain consistency and readability across the Zyrabit ecosystem, all new containers or services must follow the naming pattern:

`zyrabit-<descriptive-function>`

**Operational Examples:**
- Main API: `zyrabit-api`
- Web Interface: `zyrabit-web`
- Inference Engine: `zyrabit-engine`
- Database: `zyrabit-db`

Any internal reference (DNS) or environment variable (`SLM_URL`, `DB_URL`) must point to these official hostnames.

## Dependency security

Before adding dependencies:

```bash
pip install pip-audit
pip-audit
```

If you add dependencies, include in your PR:

- technical rationale,
- expected impact,
- scan result.

## GitHub Actions

Workflows automatically validate:

- contribution policy (PR base branch `beta`),
- `api-rag` tests,
- dependency security audit.

If CI fails, fix before requesting review.
