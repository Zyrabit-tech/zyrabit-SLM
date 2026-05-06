# Integration Playbook

This document details architectural decisions and standards for integrating Zyrabit SLM with external systems and third-party tools.

## Architectural Standards

### 1. Extending the Stack
**Question:** If we add new databases or third-party services (e.g., Strapi, Make), how should they be integrated?

**Standard:**
1. **Define a Contract:** Establish a stable application port and API contract.
2. **Implement an Adapter:** Create a dedicated provider adapter (e.g., `StrapiAdapter`) to handle translation between external and internal payloads.
3. **Expose via Reverse Proxy:** Route the service through Traefik under a single entry point (`https://localhost`).
4. **Apply Security Policies:** Enforce token authentication, request signing, and logging.

### 2. Decoupled Workflow Automation
**Question:** How do we integrate automation tools like n8n without breaking hexagonal boundaries?

**Standard:**
- Treat external automation platforms as external systems.
- The `api-rag` service maintains the core domain and use-case orchestration.
- Use a dedicated adapter for `POST /v1/integrations/n8n/webhook`.
- The adapter maps external payloads into a stable, internal contract (`text` + optional metadata).

### 3. Integration Security Policies
All integrations must adhere to the following minimum security standards:
- **Authentication:** `Authorization: Bearer <token>` for service-to-service communication.
- **Integrity:** HMAC SHA-256 signatures in `X-Zyrabit-Signature` for request verification.
- **Payload Stability:** Strict adherence to the `text`-required payload contract.
- **Zero Public Ports:** No additional public ports should be exposed per integration; all traffic routes through the primary entry point.
- **Secrets Management:** Use Docker Secrets (`_FILE` suffix) or an on-premise Vault.

## Model Optimization Pipelines

### Local Super-Fine-Tuning (SFT)
To improve model accuracy without internet exposure, follow this local fine-tuning sequence:

1. **Failure Detection:** Emit a `model_miss_detected` event when technical responses fall below a confidence threshold.
2. **Dataset Curation:** Persist failing examples locally, including the prompt, expected answer, and technical domain tag.
3. **Batch Processing:** Run offline LoRA/PEFT jobs in batches using local compute resources.
4. **Benchmarking:** Evaluate the tuned model against a localized benchmark dataset.
5. **Promotion:** Promote the model to production only if it passes both quality and safety gates.
