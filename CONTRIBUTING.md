# Contributing to Zyrabit SLM

Thank you for your interest in contributing. This document explains the branching model, commit conventions, and review process for this project.

---

## Branching Model

```
main        ← production-only, protected
  └── beta  ← staging integration branch
        └── feat/*, fix/*, docs/*, chore/*  ← all work branches
```

**Rules:**
- All PRs must target `beta`. Direct PRs to `main` are rejected by CI.
- Only `beta` merges into `main` (enforced by the contribution-policy workflow).
- Keep your branch in sync with `beta` before opening a PR.

---

## Workflow

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USER/zyrabit-SLM.git
cd zyrabit-SLM

# 2. Add upstream
git remote add upstream https://github.com/Zyrabit-tech/zyrabit-SLM.git

# 3. Sync beta
git fetch upstream
git checkout beta
git pull upstream beta

# 4. Create your branch
git checkout -b feat/my-change

# 5. Make changes, add tests, commit
git commit -m "feat(api): add streaming response support"

# 6. Open a PR targeting beta
```

---

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>
```

| Type | When to use |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or fixing tests |
| `chore` | Tooling, CI, dependencies, config |

**Examples:**
```
feat(security): add credit card PII pattern to pipeline
fix(api): handle empty ingest response from ChromaDB
docs(readme): update quick start with uv sync instructions
chore(ci): pin ubuntu-latest to ubuntu-24.04
```

---

## PR Checklist

Before requesting review, verify:

- [ ] PR targets `beta` (not `main`)
- [ ] Tests pass locally: `uv run pytest`
- [ ] No secrets, credentials, or PII in code or commits
- [ ] Documentation updated if behavior changed
- [ ] Commit messages follow Conventional Commits
- [ ] New dependencies include a rationale and `pip-audit` scan result

---

## Local Verification

```bash
# Install dependencies
uv sync

# Run the full test suite
uv run pytest

# Verify the PII pipeline end-to-end
python secure_agent.py "My email is test@example.com and SSN is 123-45-6789"

# Build and verify all containers
cd zyrabit-slm/scripts
./build_and_verify.sh
```

Extended checklist: [`validation/pr-checklist.md`](validation/pr-checklist.md)

---

## Dependency Policy

Before adding a new dependency:

1. Check if the functionality can be implemented without it.
2. Run a security scan:
   ```bash
   uv run --with pip-audit pip-audit -r pyproject.toml
   ```
3. Include in your PR description:
   - Why this dependency is needed
   - Number of transitive dependencies it adds
   - `pip-audit` result (clean)

**Langchain ecosystem note:** All `langchain-*` packages must stay within the same version era (currently `LangChain Core 1.x`). Do not mix packages from different eras — they have incompatible sub-dependency ranges.

---

## Infrastructure Standards

All services must follow the container naming pattern: `zyrabit-<function>`.

| Service | Container name |
|---|---|
| API backend | `zyrabit-api` |
| Web UI | `zyrabit-web` |
| Inference engine | `zyrabit-engine` |
| Vector database | `zyrabit-db` |
| MCP tool server | `zyrabit-mcp` |

Environment variable references (`SLM_URL`, `DB_URL`) must use these official hostnames.

---

## Code Standards

- **Python version:** 3.12 strictly. Avoid 3.13+ until all dependencies declare support.
- **Language:** Code, variable names, comments, and commit messages must be in English.
- **Architecture:** New integrations must implement an adapter over an existing port — do not couple domain logic to external providers directly.
- **KISS principle:** Prefer simple, readable solutions over clever abstractions.
- **One PR = one purpose.** Split unrelated changes into separate PRs.

---

## CI / GitHub Actions

| Workflow | Trigger | What it checks |
|---|---|---|
| `ci.yml` | PR to `beta`/`main` | Contribution policy, tests, production build gate |
| `security-audit.yml` | Weekly + every PR | Dependency vulnerability scan (`pip-audit`) |
| `deploy-docs.yml` | Push to `main` | Publishes docs to GitHub Pages |

If CI fails, fix the issue before requesting a review. Do not merge with failing checks.
