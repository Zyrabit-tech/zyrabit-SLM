# Contributing to Zyrabit SLM

Thank you for your interest in contributing to the sovereign AI ecosystem. Zyrabit SLM is built for organizations, engineers, and researchers seeking high-performance, air-gapped local AI. Whether you're fixing a typo in documentation, expanding MCP tool adapters, or benchmarking specialized hardware, your contributions are welcome!

---

## 🌟 Where to Start (Good First Issues)

If you are new to Zyrabit SLM or looking for a fast way to get involved:

1. **Browse Good First Issues**: Filter our issue tracker by the [`good first issue`](https://github.com/Zyrabit-tech/zyrabit-SLM/labels/good%20first%20issue) or [`help wanted`](https://github.com/Zyrabit-tech/zyrabit-SLM/labels/help%20wanted) labels.
2. **Claim an Issue**: Comment on the issue stating that you'd like to work on it so the community can avoid duplicate work.
3. **Need Guidance?**: Ask in the issue or in [GitHub Discussions](https://github.com/Zyrabit-tech/zyrabit-SLM/discussions). The project lead reviews pull requests. See [GOVERNANCE.md](GOVERNANCE.md) for who decides.
4. **Security Researcher?**: See [SECURITY.md](SECURITY.md) for our private disclosure guidelines and our **Security Hall of Fame**.

---

## Active repair wave (Nov 2026) — fix what is broken

Verified findings on `main` v2.4.9. **One pull request per issue. Target `beta`. No new product features** — restore contracts the README already promises (hybrid RAG, verified citations, real delete, honest health, safe defaults).

### Rules for every PR in this wave

- Prefer adapters/ports already in the hexagonal layout; do not invent a second RAG stack, MCP gateway, or vector DB.
- Replace silent `except Exception: pass` / empty fallbacks on the RAG path with logged degradation + response metadata.
- Tests must exercise the **real adapter signature** (or ephemeral Chroma / fake HTTP). Do not leave fakes that accept kwargs the production adapter rejects.
- Docs/README that overclaim must be corrected in the same PR that touches that behavior (or in the dedicated docs issue).
- Leave enhancement/roadmap issues alone (`#115`–`#122`, `#118`, `#184`, `#192`, etc.) until this wave lands.

### Close-first (already shipped — do not reopen)

| Issue | Status |
| :--- | :--- |
| `#102` `zyra status --json` | Closed (2.4.7) |
| `#113` Docker multi-arch tags | Closed (2.4.7 / 2.4.9) |
| `#136` RFC / CURP / CLABE masking | Closed (2.4.7) |
| `#139` `#145` `#150` `#163` `#168` `#188` dated dependency scans | Closed as superseded by `#200` |

### Open repair queue (one PR each)

| Priority | Issue | Title | Effort |
| :---: | :---: | :--- | :---: |
| P0 | [#205](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/205) | Vector `document_id` filter TypeError → hybrid becomes lexical | S |
| P0 | [#207](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/207) | Citation format mismatch (`id=` vs `:uuid`) | S |
| P0 | [#206](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/206) | Delete/reindex never removes Chroma vectors | S |
| P1 | [#204](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/204) | Embedding timeout 5s; health false green | S |
| P1 | [#209](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/209) | Map Ollama `num_predict` / stop ReadTimeout retries | S |
| P1 | [#213](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/213) | `docker.sock` / docker_* allowlist / Chroma bind | M |
| P1 | [#208](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/208) | ES questions vs EN docs (lexical gate) — after `#205` | M |
| P2 | [#212](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/212) | `zyra status` / `verify` false healthy | S |
| P2 | [#214](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/214) | `/v1/extract` `valid` → `schema_valid` + docs | M |
| P2 | [#211](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/211) | README MCP `:8001` docs correction only | S |
| P3 | [#210](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/210) | Duplicate `docker_*` tools + `pymupdf` import | XS |

### Related good-first / security hygiene (same wave)

| Issue | Note |
| :--- | :--- |
| [#137](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/137) | Show cited passage next to the answer (UI) |
| [#138](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/138) | Empty default `PII_CUSTOM_NAMES` fallback |
| [#200](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/200) | Current dependency scan (`dnspython` / `opentelemetry-api` bumps) |
| [#158](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/158) / [#159](https://github.com/Zyrabit-tech/zyrabit-SLM/issues/159) | gitleaks / Semgrep — need org secrets before CI can enforce |

### Suggested merge order into `beta`

`#205` → `#207` → `#206` → `#204` + `#209` → `#213` → `#208` → `#212` → `#214` → `#211` → `#210` (plus `#137` / `#138` whenever ready).

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
./zyra.sh verify
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
