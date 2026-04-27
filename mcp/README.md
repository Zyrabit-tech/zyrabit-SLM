# Zyrabit MCP Installer Server

Este módulo contiene un servidor MCP (Model Context Protocol) diseñado para actuar como un Asistente Técnico Automatizado para el despliegue del ecosistema Zyrabit-SLM.

## Funciones Principales

1. **Herramientas de Diagnóstico (`check_system_status`, `suggest_fix`)**: Capaces de consultar el daemon de Docker (`docker ps`, `docker logs`) utilizando un volumen montado para identificar problemas en los servicios de Zyrabit (Ollama, Vector DB, Traefik, etc.).
2. **Extracción de Contexto (`docs://install-guide`)**: Proporciona el contexto actualizado de `README.md` y `CONTRIBUTING.md` a cualquier cliente MCP para sugerencias alineadas a las mejores prácticas del proyecto.
3. **Punto de Conexión HTTP (`/diagnose`)**: Facilita el consumo de un diagnóstico simplificado a través de una API REST.

## 🔌 Integración con Clientes Externos (Claude Desktop, Cursor)

Puedes conectar este Asistente directamente a tu agente de escritorio para que pueda intervenir si algo sale mal con los contenedores.

### Claude Desktop

Añade lo siguiente en el archivo de configuración de Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "zyrabit-installer": {
      "command": "docker",
      "args": [
        "exec", 
        "-i", 
        "mcp-server", 
        "python", 
        "install_server.py"
      ]
    }
  }
}
```
*Asegúrate de que el contenedor `mcp-server` de Zyrabit esté ejecutándose.*

### Cursor IDE

En tu IDE Cursor, ve a **Settings** > **Features** > **MCP Servers** y añade uno nuevo con:

- **Type**: `command`
- **Name**: `Zyrabit-Installer`
- **Command**: `docker exec -i mcp-server python install_server.py`

*(O alternativamente, ejecutar directamente usando el intérprete Python local si instalaste dependencias localmente)*:
- **Command**: `python path/to/mcp/install_server.py`

## Uso Dual

El script `install_server.py` se puede arrancar de dos formas:
1. `python install_server.py` -> Inicia el puente estándar de **`stdio`** usado por el ecosistema Protocol Context Model.
2. `python install_server.py --http` -> Levanta una instancia de **`uvicorn`** en el puerto 8001 para conectividad vía HTTP (REST).
