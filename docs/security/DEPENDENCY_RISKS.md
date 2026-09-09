# Dependency risk register

This register makes unresolved third-party advisories visible to the release
process.  It is not a suppression list and does not state that a package is
safe. A release owner must explicitly accept, remediate, or remove an entry
before a production release.

| Advisory | Component | Installed version | Fix available | State | Required action |
| --- | --- | ---: | --- | --- | --- |
| `PYSEC-2026-311` | `chromadb` | `1.5.9` | No upstream fixed version published | open | Track upstream advisory; do not expose Chroma directly outside the local runtime network; obtain explicit release-risk acceptance before production. |
| `CVE-2026-45830` | `chromadb` | `1.5.9` | No upstream fixed version published | open | Track upstream advisory; validate multi-tenant authorization policies; obtain explicit release-risk acceptance before production. |
| `CVE-2026-45831` | `chromadb` | `1.5.9` | No upstream fixed version published | open | Track upstream advisory; enforce strict collection-level RBAC; obtain explicit release-risk acceptance before production. |
| `CVE-2026-45833` | `chromadb` | `1.5.9` | No upstream fixed version published | open | Track upstream advisory; disable trust_remote_code in collection update; obtain explicit release-risk acceptance before production. |
| `PYSEC-2026-2447` | `diskcache` | `5.6.3` | No upstream fixed version published | open | Track upstream advisory; obtain explicit release-risk acceptance before production. |

## Release rule

`pip-audit` is never run with an undocumented ignore. New advisories fail the
security job. Entries marked **open** also block a production release decision;
they are recorded here so the exception is visible, reviewable and removable.
The current beta may be built and tested locally, but it is **not cleared for a
production release** until the two open records have an owner, review date and
explicit decision.
