# 🖼️ Frontend Architecture: Bring Your Own Front (BYOF)

Zyrabit SLM sigue una **Arquitectura Hexagonal**, lo que significa que la interfaz de usuario es simplemente un **Adaptador de Salida**. No estamos casados con ninguna tecnología de frontend; el Core es agnóstico y soberano.

---

## 🚀 El Concepto "Quita-y-Pon"
La interfaz incluida por defecto (`zyrabit-web`) es nuestra **Implementación de Referencia**. Está construida en **Vanilla JS** puro para garantizar:
1.  **Carga Instantánea**: Sin frameworks pesados que procesar.
2.  **Transparencia**: El código es legible y auditable por cualquier humano.
3.  **Portabilidad**: Funciona en cualquier navegador sin necesidad de compilación (Zero-Build).

Si prefieres usar **Angular**, **React** o **Next.js**, simplemente puedes desconectar el contenedor `zyrabit-web` y apuntar tu aplicación a los puertos expuestos del Core.

---

## 🧩 Web Components (Componentes Lógicos)
Aunque usamos Vanilla JS, el frontend está organizado en **Componentes Lógicos** que encapsulan funcionalidad y se comunican a través de un **EventBus** central. 

### Componentes Principales:
| Componente | Responsabilidad | Ubicación |
| :--- | :--- | :--- |
| `zyra-chat` | Interfaz de chat en tiempo real y streaming de RAG. | `ui/Renderer.js` |
| `zyra-terminal` | Observabilidad de eventos GDPR y logs del sistema. | `ui/Renderer.js` |
| `zyra-vault` | Gestión de documentos y estado de ingesta. | `main.js` (loadVault) |
| `zyra-mcp-tools` | Visualización y descubrimiento de herramientas MCP. | `main.js` (loadTools) |

### ¿Por qué no usamos Shadow DOM?
Para mantener el **Demo Kit** lo más compatible y simple posible. Sin embargo, la estructura está preparada para ser envuelta en `CustomElements` si se requiere un aislamiento de estilos más agresivo.

---

## 🛠️ Cómo conectar tu propio Frontend
Cualquier cliente externo puede interactuar con el Core a través de tres vías:

1.  **REST API**: Para operaciones CRUD de documentos y perfiles. (Puerto `8080/v1`)
2.  **WebSockets (Socket.io)**: Para la experiencia de chat en tiempo real.
3.  **MCP RPC**: Para ejecutar herramientas del sistema de forma segura. (Puerto `8080/mcp/rpc`)

### Ejemplo de Conexión (Javascript):
```javascript
import { io } from "socket.io-client";

const socket = io("https://tu-dominio.local", {
  path: "/socket.io"
});

socket.emit("chat_message", { text: "Hola Zyra" });
socket.on("chat_response", (data) => console.log(data.response));
```

---

## 🧪 Testing de UI
Dado que el frontend es un adaptador "Quita-y-Pon", el testing se centra en la **Integración**:
*   **Contratos**: Validamos que los Payloads enviados por el Core coincidan con lo que el Front espera.
*   **E2E**: Usamos herramientas externas para verificar que el flujo de "Pregunta -> RAG -> Respuesta" sea fluido.

---

## 🛡️ Seguridad (Cross-Site)
Recuerda configurar la variable `ALLOWED_ORIGINS` en tu `.env` para permitir que tu frontend personalizado (especialmente si corre en `localhost` fuera de Docker) tenga permiso para hablar con el Core.
