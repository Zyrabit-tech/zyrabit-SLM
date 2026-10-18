# Container Image Tagging Policy & Multi-Arch Standard

This document defines the official container registry tagging policy for **Zyrabit Platform** across public (Docker Hub: `zyrabitcore/zyrabit-slm`) and private/mirror (GitHub Packages: `ghcr.io/zyrabit-tech/zyrabit-slm`) registries.

---

## 1. Guiding Principles

1. **Zero Catalog Pollution:** Public registries expose only canonical multi-arch tags. They do not expose commit SHAs, architecture slices, or a second tag that only adds a `v` prefix.
2. **Multi-Arch First:** Every public tag is an OCI manifest list for `linux/amd64` and `linux/arm64`.
3. **Digests for Assembly:** Each architecture is built on a native runner and pushed by digest. The digest is not a public tag. The publish job assembles those digests into the manifest list.
4. **Predictability:** Operators pull `2.4.6`, `latest`, `beta`, or `beta-2.4.6`. Git release tags keep the `v` prefix (`v2.4.6`). Container tags do not.

---

## 2. Tag Specification Matrix

### A. Stable Release Channel (`main` or a `v*` git tag)

When a release tag is pushed (for example `v2.4.6`):

| Registry Tag | Type | Target Architectures | Purpose |
| :--- | :--- | :--- | :--- |
| `:2.4.6` | **Multi-Arch Manifest** | `amd64`, `arm64` | Canonical SemVer release tag |
| `:latest` | **Multi-Arch Manifest** | `amd64`, `arm64` | Production default pointer |

> **Public tags:** exactly **2**.
> **Forbidden:** `:v2.4.6`, `:2.4.6-amd64`, `:2.4.6-arm64`, `:2.4.6-<sha>`.

---

### B. Beta / Pre-Release Channel (`beta` Branch)

| Registry Tag | Type | Target Architectures | Purpose |
| :--- | :--- | :--- | :--- |
| `:beta` | **Multi-Arch Manifest** | `amd64`, `arm64` | Rolling preview |
| `:beta-2.4.6` | **Multi-Arch Manifest** | `amd64`, `arm64` | Version-pinned preview |

> **Public tags:** exactly **2**.
> **Forbidden:** `:beta-2.4.6-amd64`, `:beta-2.4.6-arm64`.

---

## 3. Automation Workflow

The policy is enforced in [`.github/workflows/release.yml`](../../.github/workflows/release.yml):

1. **`build-arch`** builds `linux/amd64` on `ubuntu-latest` and `linux/arm64` on `ubuntu-24.04-arm`. Each image is pushed with `push-by-digest=true`, so the registry stores the manifest without a tag.
2. **`publish-manifest`** downloads the two digests and creates the public manifest list:

```bash
docker buildx imagetools create \
  -t ${IMAGE}:${VERSION} \
  -t ${IMAGE}:latest \
  ${IMAGE}@sha256:<amd64> ${IMAGE}@sha256:<arm64>
```

Tags already published by older releases stay in the registry until they are deleted by hand. This workflow does not create new slice tags or `v`-prefixed image tags.
