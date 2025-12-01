# Security Policy

## 🔒 Reporting Security Vulnerabilities

If you discover a security vulnerability in Zyrabit SLM, please **do not** open a public issue. Instead:

1. **Email**: Send details to `security@zyrabit.com` (or create a private security advisory on GitHub)
2. **Include**: 
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## 🛡️ Dependency Security

### Automated Scanning

This project uses the following tools to monitor dependency security:

- **pip-audit**: Scans Python dependencies for known vulnerabilities
- **safety**: Checks against the Safety DB of known security issues
- **Dependabot** (GitHub): Automatically creates PRs for dependency updates

### Manual Security Checks

Before adding or updating dependencies, run:

```bash
# Install security tools
pip install pip-audit safety

# Scan all dependencies
pip-audit
safety check --json

# Check a specific package
pip install <package-name>
pip-audit
```

### Security Best Practices

1. **Pin Versions**: Always specify exact versions in `requirements.txt`
2. **Review Dependencies**: Check the package's GitHub repo, maintainers, and recent activity
3. **Minimize Dependencies**: Only add dependencies that are absolutely necessary
4. **Regular Updates**: Keep dependencies up-to-date with security patches

## 🔐 PII Sanitization Guidelines

This project implements Privacy by Design. When handling user data:

1. **Never Log PII**: Emails, phone numbers, credit cards, SSNs must never appear in logs
2. **Sanitize Before SLM**: Use the `SecureAgent` class to redact PII before sending to the model
3. **Test Sanitization**: Add tests for new PII patterns in `tests/test_security.py`

### Supported PII Patterns

Currently sanitized patterns:
- Email addresses
- Phone numbers (US format)
- Credit card numbers
- Social Security Numbers (SSN)

To add new patterns, update `SecureAgent.patterns` in `secure_agent.py`.

## 🚨 Known Security Considerations

### Local Execution

This project is designed for **local or on-premise deployment**. Key security features:

- **No External APIs**: All SLM inference happens locally via Ollama
- **Air-Gapped Mode**: Can run completely offline after initial model download
- **Data Sovereignty**: Your data never leaves your infrastructure

### Docker Network Isolation

Services communicate via internal Docker network (`zyrabit-network`). Only the API port (8080) is exposed to the host.

## 📊 Security Audit History

| Date | Tool | Vulnerabilities Found | Status |
|------|------|----------------------|--------|
| 2025-11-28 | pip-audit | 0 | ✅ Clean |
| 2025-11-28 | safety | 0 | ✅ Clean |

*Last updated: 2025-11-28*

## 🔄 Security Update Process

1. **Detection**: Dependabot or manual scan identifies vulnerability
2. **Assessment**: Evaluate severity and impact
3. **Patch**: Update dependency to patched version
4. **Test**: Run full test suite
5. **Deploy**: Merge to `beta`, then `main`
6. **Notify**: Update this document and notify users if critical

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Docker Security](https://docs.docker.com/engine/security/)
