# Architecture Overview

```mermaid
flowchart TB
    U[User or External Client] -->|HTTPS 443| T[Traefik Gateway]

    subgraph VPC["Zyrabit Sovereign Infrastructure"]
      direction TB

      subgraph SN["zyrabit-sovereign-net (Shared Ecosystem)"]
        T
        A[zyrabit-api (Core)]
        W[zyrabit-web (Vanilla UI)]
        D[docs-portal]
        N[n8n]
        P[prometheus]
        G[grafana]
        C[(vector-db / Chroma)]
      end

      subgraph MO["model-network (Internal Protected)"]
        S[zyrabit-engine / Ollama]
      end
    end

    T -->|/v1| A
    T -->|/| W
    T -->|/docs| D
    T -->|/n8n| N
    T -->|/metrics| P
    T -->|/grafana| G

    W <-->|Socket.io / REST| A
    N -->|Adapter Port| A
    A <--> C
    A <--> S
    
    %% Security Layer
    GK[PII Gatekeeper] --- A
    A -.->|MCP RPC| U
```
