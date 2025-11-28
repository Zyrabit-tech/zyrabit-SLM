# 🤝 How to Contribute to Zyrabit LLM

Thank you for your interest in contributing! This project is open-source because we believe in the power of community.

To maintain harmony, code quality, and maintainer sanity (and yours!), we have established a set of guidelines. The goal is not bureaucracy, but to facilitate the review and integration of your amazing work.

## 🧠 Contribution Philosophy

*   **One PR, One Purpose**: Each Pull Request (PR) should solve one problem or add one feature. Giant PRs that do 10 things at once will be (politely) rejected.
*   **Quality is Non-Negotiable**: A PR without tests or that breaks existing ones will not be merged.
*   **Communicate First, Code Later**: If you plan a large feature or complex refactor, open an Issue first. Let's discuss the approach before you invest hours of coding.

## 🚀 The Workflow: The Road to beta

We have a strict flow to protect stability. The `main` branch represents the latest stable version, and NO ONE pushes or makes PRs directly to it.

The integration branch is `beta`.

> [!WARNING]
> **NEVER MAKE A PULL REQUEST TO `main`**
> Any PR targeting `main` will be automatically closed.

Your workflow should be:

1.  **Fork**: Create a fork of the repository to your own GitHub account.
2.  **Clone your Fork**:
    ```bash
    git clone https://github.com/YOUR_USER/zyrabit-llm.git
    ```
3.  **Setup Upstream** (Do this only once):
    ```bash
    cd zyrabit-llm
    git remote add upstream https://github.com/Zyrabit-tech/zyrabit-llm.git
    ```
4.  **Sync your Fork**: Before coding, make sure you have the latest from `beta`.
    ```bash
    git fetch upstream
    git checkout beta
    git pull upstream beta
    ```
5.  **Create your Branch**: Create your feature branch from `beta`.
    ```bash
    git checkout -b my-cool-feature
    ```
6.  **Code and Commit**: Work your magic. Use the Commit Convention (see below).
7.  **Push to your Fork**:
    ```bash
    git push -u origin my-cool-feature
    ```
8.  **Open the Pull Request**:
    *   Go to GitHub and open a PR.
    *   The base branch must be **`beta`**.
    *   The compare branch must be `my-cool-feature`.
    *   Fill out the PR Template in detail.

## 💬 Commit Convention

To keep a clean and readable history, we use **Conventional Commits**.

Your commit MUST follow this format:
`type(scope): short description`

*   **type**: `feat` (new feature), `fix` (bug fix), `docs` (documentation), `style` (formatting), `refactor` (code change), `test` (tests), `chore` (maintenance).
*   **(scope)** (Optional): `api`, `docker`, `ingest`, `readme`, etc.
*   **description**: In lowercase, imperative ("add", "fix").

**Examples:**
*   `feat(api): add /v1/ingest endpoint`
*   `fix(ingest): fix PDF validation`
*   `docs(contributing): update project name`
*   `test(security): add PII sanitization tests`

## 📝 Coding Standards

### Naming Conventions

> [!IMPORTANT]
> **All code must be in English**: variables, functions, classes, documentation comments.

**Variables and Functions**: Use `snake_case` in English
*   ✅ `user_input`, `sanitize_data()`, `process_pdf_file()`
*   ❌ `entrada_usuario`, `sanitizarDatos()`, `procesarArchivoPDF()`

**Classes**: Use `PascalCase` in English
*   ✅ `VectorDatabase`, `SecureAgent`, `OllamaClient`
*   ❌ `BaseDeDatosVectorial`, `AgenteSeguro`

**Dictionaries and Configuration**: Use `snake_case` for keys
```python
# ✅ Correct
config = {
    "model_name": "phi3",
    "max_tokens": 1000,
    "enable_sanitization": True
}

# ❌ Incorrect
config = {
    "nombreModelo": "phi3",
    "maxTokens": 1000
}
```

**Comments**:
*   Docstrings (function/class documentation): **Required in English**
*   Inline comments: Preferably in English, but Spanish allowed for internal clarity

### Dependency Security

Before adding a new dependency to `requirements.txt`, **you must verify its security**:

```bash
# Install security tools
pip install pip-audit safety

# Scan current dependencies
pip-audit
safety check

# Verify a specific dependency before adding it
pip install <new-dependency>
pip-audit
```

**Requirements for PRs adding dependencies:**
- [ ] Run `pip-audit` and `safety check`
- [ ] Include scan results in PR description
- [ ] Justify why the dependency is necessary
- [ ] Verify there are no known vulnerabilities

## 📋 Pull Request Template

A PR is your cover letter. Sell your solution.

**Basic Checklist:**
- [ ] My commits follow the convention.
- [ ] My code follows best practices.
- [ ] I added or updated necessary tests.
- [ ] Documentation is updated.
- [ ] My PR targets the **`beta`** branch.

## 🆘 Stuck?

Don't suffer in silence.
*   **Open an Issue**: With the label `question` or `help`.
*   **Create a Draft PR**: And explain where you are stuck.

We are here to build together.
