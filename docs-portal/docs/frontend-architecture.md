---
sidebar_position: 5
title: 'Frontend Architecture'
description: 'BYOF (Bring Your Own Front) architecture and the frontend role in the hexagonal stack'
---

# 🖼️ Frontend Architecture: Bring Your Own Front (BYOF)

Zyrabit SLM follows a **Hexagonal Architecture**, which means that the user interface is simply an **Output Adapter**. We are not tied to any frontend technology; the Core is agnostic and sovereign.

---

## 🚀 The "Plug-and-Play" Concept
The interface included by default (`zyrabit-web`) is our **Reference Implementation**. It is built in pure **Vanilla JS** to ensure:
1. **Instant Loading**: No heavy frameworks to process.
2. **Transparency**: The code is readable and auditable by any human.
3. **Portability**: Works in any browser without needing compilation (Zero-Build).

If you prefer to use **Angular**, **React**, or **Next.js**, you can simply disconnect the `zyrabit-web` container and point your application to the exposed Core ports.

---

## 🧩 Web Components (Logical Components)
Although we use Vanilla JS, the frontend is organized into **Logical Components** that encapsulate functionality and communicate through a central **EventBus**.

### Main Components:
| Component | Responsibility | Location |
| :--- | :--- | :--- |
| `zyra-chat` | Real-time chat interface and RAG streaming. | `ui/Renderer.js` |
| `zyra-terminal` | Observability of GDPR events and system logs. | `ui/Renderer.js` |
| `zyra-vault` | Document management and ingestion status. | `main.js` (loadVault) |
| `zyra-mcp-tools` | Visualization and discovery of MCP tools. | `main.js` (loadTools) |

### Why don't we use Shadow DOM?
To keep the **Demo Kit** as compatible and simple as possible. However, the structure is prepared to be wrapped in `CustomElements` if more aggressive style isolation is required.

---

## 🛠️ How to connect your own Frontend
Any external client can interact with the Core through three ways:

1. **REST API**: For CRUD operations on documents and profiles. (Port `8080/v1`)
2. **WebSockets (Socket.io)**: For the real-time chat experience.
3. **MCP RPC**: To securely execute system tools. (Port `8080/mcp/rpc`)

### Connection Example (Javascript):
```javascript
import { io } from "socket.io-client";

const socket = io("https://your-domain.local", {
  path: "/socket.io"
});

socket.emit("chat_message", { text: "Hello Zyra" });
socket.on("chat_response", (data) => console.log(data.response));
```

---

## 🧪 UI Testing
Since the frontend is a "Plug-and-Play" adapter, testing focuses on **Integration**:
* **Contracts**: We validate that the Payloads sent by the Core match what the Front expects.
* **E2E**: We use external tools to verify that the "Question -> RAG -> Answer" flow is smooth.

---

## 🛡️ Security (Cross-Site)
Remember to configure the `ALLOWED_ORIGINS` variable in your `.env` to allow your custom frontend (especially if it runs on `localhost` outside of Docker) to have permission to talk to the Core.

---

## Related Documentation
- [Hexagonal Architecture](./architecture/hexagonal.md)
- [Integration Playbook](./integration-playbook.md)
