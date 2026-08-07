# Suite heredada

Estas pruebas se conservan porque cubren módulos que aún existen, pero ya no
son criterios de aceptación del nodo documental. Cubren MCP, ReAct, n8n,
memoria y el flujo de chat anterior basado en mocks.

No se ejecutan en la suite principal. Para reactivarlas, primero debe activarse
`ENABLE_LEGACY_EXTENSIONS=true` y actualizar sus contratos contra la interfaz
actual; moverlas de vuelta sin hacerlo produciría falsos positivos.
