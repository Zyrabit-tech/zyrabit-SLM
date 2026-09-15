# Container Image Tagging Policy & Multi-Arch Standard

This document defines the official container registry tagging policy for **Zyrabit Platform** across public (Docker Hub: `zyrabitcore/zyrabit-slm`) and private/mirror (GitHub Packages: `ghcr.io/zyrabit-tech/zyrabit-slm`) registries.

---

## 1. Guiding Principles

1. **Zero Catalog Pollution:** Public registries must never be polluted with commit SHAs, intermediate build identifiers, or duplicate prefixes.
2. **Multi-Arch First:** All public entrypoint tags (`2.4.4`, `v2.4.4`, `latest`, `beta`) are **OCI Multi-Arch Manifest Lists** seamlessly supporting both `linux/amd64` (x86_64) and `linux/arm64` (Apple Silicon, AWS Graviton, Raspberry Pi/Ampere).
3. **Explicit Arch Slices Only for Assembly:** Single-architecture slices are pushed with a single canonical suffix (`<version>-<arch>`) strictly to allow manifest construction via `docker buildx imagetools`.
4. **Predictability:** Developers, DevOps engineers, and automated orchestrators (Kubernetes, Docker Compose, Portainer) can reliably reference semantic tags.

---

## 2. Tag Specification Matrix

### A. Stable Release Channel (`v*` Tag or `main` Branch)

When a release tag is pushed (e.g., `v2.4.4`):

| Registry Tag | Type | Target Architectures | Purpose |
| :--- | :--- | :--- | :--- |
| `:2.4.4` | **Multi-Arch Manifest** | `amd64`, `arm64` | Canonical SemVer release tag |
| `:v2.4.4` | **Multi-Arch Manifest** | `amd64`, `arm64` | SemVer alias with `v` prefix |
| `:latest` | **Multi-Arch Manifest** | `amd64`, `arm64` | Production default pointer |
| `:2.4.4-amd64` | Arch Slice | `linux/amd64` | Architecture slice & fallback for x86_64 |
| `:2.4.4-arm64` | Arch Slice | `linux/arm64` | Architecture slice & fallback for aarch64 |

> **Total Tags Generated:** Exactly **5** (3 Multi-Arch manifests + 2 architecture slices).  
> **Forbidden on Docker Hub:** `2.4.4-<sha>`, `2.4.4-<sha>-amd64`, `v2.4.4-amd64`.

---

### B. Beta / Pre-Release Channel (`beta` Branch)

When continuous integration builds from the `beta` branch:

| Registry Tag | Type | Target Architectures | Purpose |
| :--- | :--- | :--- | :--- |
| `:beta` | **Multi-Arch Manifest** | `amd64`, `arm64` | Rolling bleeding-edge preview manifest |
| `:beta-2.4.4` | **Multi-Arch Manifest** | `amd64`, `arm64` | Version-pinned beta preview manifest |
| `:beta-2.4.4-amd64` | Arch Slice | `linux/amd64` | Beta architecture slice for x86_64 |
| `:beta-2.4.4-arm64` | Arch Slice | `linux/arm64` | Beta architecture slice for aarch64 |

> **Total Tags Generated:** Exactly **4** (2 Multi-Arch manifests + 2 architecture slices).

---

## 3. Automation Workflow

The tagging policy is enforced in [`.github/workflows/release.yml`](../../.github/workflows/release.yml):

1. **`build-arch` Job (Matrix):**
   - Builds independent image layers on dedicated native runners (`ubuntu-latest` for amd64, `ubuntu-24.04-arm` for arm64).
   - Pushes only the canonical architecture slice `${IMAGE}:${VERSION}-${SUFFIX}`.
2. **`publish-manifest` Job:**
   - Combines architecture slices into multi-arch manifests using:
     ```bash
     docker buildx imagetools create \
       -t ${IMAGE}:${VERSION} \
       -t ${IMAGE}:v${VERSION} \
       -t ${IMAGE}:latest \
       ${IMAGE}:${VERSION}-amd64 ${IMAGE}:${VERSION}-arm64
     ```
   - Eliminates all SHA tags and redundant permutations.
