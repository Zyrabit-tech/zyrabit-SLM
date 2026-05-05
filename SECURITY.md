# Security Policy

> This document is maintained in English only, by project policy.

## Reporting a Vulnerability

If you discover a security vulnerability in Zyrabit SLM, **do not open a public issue.**

Report privately through one of these channels:
- **GitHub Security Advisory:** [Create a private advisory](https://github.com/Zyrabit-tech/zyrabit-SLM/security/advisories/new)
- **Email:** `security@zyrabit.com`

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge within **48 hours** and provide a resolution timeline within **7 days** for critical issues.

---

## Dependency Security

### Automated Scanning

| Tool | Scope | Cadence |
|---|---|---|
| `pip-audit` | Python dependency CVEs | Every PR + weekly |
| GitHub Dependabot | Dependency version updates | Continuous |

### Manual Check Before Adding a Dependency

```bash
uv run --with pip-audit pip-audit -r pyproject.toml
```

**Best practices:**
- Pin exact versions (`==`) in `requirements.txt` and `pyproject.toml`.
- Only add dependencies that are strictly necessary.
- Review the package's maintainers, release cadence, and open issues before adopting.
- For the Langchain ecosystem: all `langchain-*` packages must stay within the same version era to avoid dependency conflicts.

---

## PII Sanitization

This project implements **Privacy by Design**. The following rules are enforced:

1. **Never log PII.** Emails, phone numbers, credit cards, and SSNs must never appear in application logs.
2. **Sanitize before inference.** Every inference path passes through `zyrabit-slm/api-rag/app/core/security/pii_pipeline.py`.
3. **De-anonymize only on exit.** The model receives tokens (`<USER_EMAIL_1>`, `<SSN_1>`, etc.). Raw values are restored only in the final response layer.
4. **Test every new pattern.** Add tests in `zyrabit-slm/api-rag/tests/test_security.py` and `test_pii_pipeline.py`.

### Supported PII Patterns

| Pattern | Token example |
|---|---|
| Email address | `<USER_EMAIL_1>` |
| Phone number (US) | `<PHONE_1>` |
| Credit card (Luhn-validated) | `<CARD_1>` |
| Social Security Number | `<SSN_1>` |
| Monetary amount | `<AMOUNT_1>` |
| Person name | `<USER_NAME_1>` |

To add a new pattern: extend the detectors in `pii_pipeline.py` and update `test_security.py`.

---

## Network Isolation

Services are split into three Docker networks:

| Network | Services | External access |
|---|---|---|
| `frontend-network` | Traefik | Yes — ports 80/443 |
| `backend-network` | API, ChromaDB, Prometheus, Grafana, MCP | No |
| `model-network` | Ollama (`internal: true`) | No — no egress |

The inference engine (`zyrabit-engine`) is intentionally isolated with no external network egress.

---

## Security Audit Log

| Date | Tool | Vulnerabilities Found | Status |
|---|---|---|---|
| 2026-05-04 | pip-audit | 0 | ✅ Clean |
| 2026-03-12 | pip-audit | 0 | ✅ Clean |

---

## Security Validation Checklist

Before merging any PR:

```bash
# 1. Run the full test suite
uv run pytest

# 2. Run dependency audit
uv run --with pip-audit pip-audit -r pyproject.toml

# 3. Verify PII never reaches the model payload
uv run pytest tests/test_services_security.py -v

# 4. Verify MCP resources are sanitized by default
uv run pytest tests/test_mcp.py -v
```

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [pip-audit documentation](https://pypi.org/project/pip-audit/)
