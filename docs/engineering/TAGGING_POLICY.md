# Container Image Tagging Policy & Multi-Arch Standard

This document defines the official container registry tagging policy for **Zyrabit Platform** across public (Docker Hub: `zyrabitcore/zyrabit-slm`) and private/mirror (GitHub Packages: `ghcr.io/zyrabit-tech/zyrabit-slm`) registries.

---

## 1. Guiding Principles

1. **Zero Catalog Pollution:** Public registries expose only canonical multi-arch tags. They do not expose commit SHAs, architecture slices, or a second tag that only adds a `v` prefix.
2. **Multi-Arch First:** Every public tag is an OCI manifest list for `linux/amd64` and `linux/arm64`.
3. **Digests for Assembly:** Each architecture is built on a native runner and pushed by digest. The digest is not a public tag. The publish job assembles those digests into the manifest list.
4. **Predictability:** Operators pull `2.4.8`, `latest`, `beta`, or `beta-2.4.8`. Git release tags keep the `v` prefix (`v2.4.8`). Container tags do not.

---

## 2. Tag Specification Matrix

### A. Stable Release Channel (a `vX.Y.Z` tag whose commit is on `main`)

A stable git tag such as `v2.4.9` publishes only when that commit is contained in `main` and `VERSION` is `2.4.9`. `v2.4.8` stays as it was published. The workflow refuses to move an immutable tag that already exists.

| Registry Tag | Type | Target Architectures | Purpose |
| :--- | :--- | :--- | :--- |
| `:2.4.9` | **Multi-Arch Manifest** | `amd64`, `arm64` | Immutable SemVer release |
| `:latest` | **Multi-Arch Manifest** | `amd64`, `arm64` | Moving production pointer on GHCR. Docker Hub receives it only when the repository allows that tag to change. |

Both architecture digests must exist before either tag is updated. A failed AMD64 or ARM64 build does not publish the stable manifest.

> **Forbidden:** `:v2.4.9`, architecture slice tags, and publishing `:latest` from `beta`.

---

### B. Beta / Pre-Release Channel (`vX.Y.Z-beta.N` created from `beta`)

`beta` creates `vX.Y.Z-beta.1` once per `VERSION`. It does not create `vX.Y.Z`.

| Registry Tag | Type | Target Architectures | Purpose |
| :--- | :--- | :--- | :--- |
| `:beta` | **Multi-Arch Manifest** | `amd64`, `arm64` | Moving preview pointer on GHCR. Docker Hub receives it only when the repository allows that tag to change. |
| `:2.4.9-beta.1` | **Multi-Arch Manifest** | `amd64`, `arm64` | Immutable prerelease |

> **Forbidden:** moving `:latest`, moving `:2.4.9-beta.1` after it exists, and architecture slice tags.

---

## 3. Automation Workflow

The policy is enforced in [`.github/workflows/release.yml`](../../.github/workflows/release.yml):

1. **`build-arch`** builds `linux/amd64` on `ubuntu-latest` and `linux/arm64` on `ubuntu-24.04-arm`. Each image is pushed with `push-by-digest=true`, so the registry stores the manifest without a tag.
2. **`publish-manifest`** downloads the two digests and creates the public manifest list:

The publish job calls `scripts/resolve_release_channel.py`. Stable tags are checked against `main` before any manifest is created. The job writes a ledger with the git tag, full SHA, and the amd64 and arm64 digests. An existing immutable image tag stops the job.

Docker Hub `zyrabitcore/zyrabit-slm` has tag immutability enabled for `.*`. A tag that already exists, including `:beta` and `:latest`, cannot be moved there. The workflow still publishes the new version tag on Docker Hub and publishes the moving tag on GHCR. Narrowing the Hub rule to version tags (and leaving `beta` and `latest` out of it) makes those two pointers move on Docker Hub again.

Tags already published by older releases, including `2.4.8` and `v2.4.8`, stay where they are. This workflow does not create new slice tags or `v`-prefixed image tags.
