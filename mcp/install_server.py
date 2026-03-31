import os
import subprocess
from fastapi import FastAPI
from pydantic import BaseModel

try:
    from fastmcp import FastMCP # Independent package
except ImportError:
    from mcp.server.fastmcp import FastMCP # Part of official mcp sdk

# Creamos el servidor MCP
mcp = FastMCP("Zyrabit Installer Agent")

@mcp.resource("docs://install-guide")
def get_install_guide() -> str:
    """Extrae la guía de instalación de Zyrabit desde los README y archivos CONTRIBUTING."""
    content = ""
    paths = ["/app/README.md", "/app/CONTRIBUTING.md", "../README.md", "../CONTRIBUTING.md"]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content += f"\n# {os.path.basename(path)}\n" + f.read() + "\n"
            except Exception:
                pass
    if not content:
        content = "No se pudieron encontrar las guías de instalación locales."
    return content

@mcp.tool()
def check_system_status() -> str:
    """Revisa el estado de los contenedores Docker mediante comandos shell para diagnosticar fallos."""
    try:
        ps_output = subprocess.check_output(
            ["docker", "ps", "-a", "--format", "{{.Names}} - {{.Status}}"], 
            stderr=subprocess.STDOUT
        ).decode("utf-8")
        if not ps_output.strip():
            return "No hay contenedores Docker en ejecución."
        return f"Estado de los contenedores:\n{ps_output}"
    except FileNotFoundError:
        return "Error: el comando 'docker' no se encuentra instalado en este contenedor."
    except Exception as e:
        return f"Error al ejecutar docker ps: {str(e)}"

@mcp.tool()
def suggest_fix(error_query: str) -> str:
    """Basado en errores detectados en los contenedores o logs, devuelve la solución recomendada del README."""
    q = error_query.lower()
    if "443" in q and "already in use" in q:
        return "Sugerencia: Puerto 443 ocupado. Asegúrate de detener Nginx, Apache u otro proceso que ocupe el puerto 443 antes del despliegue."
    if "gpu" in q or "cuda" in q or "nvidia" in q:
        return "Sugerencia: Fallo en la detección o inicialización de GPU. Se sugiere cambiar al modo 'Ollama Nativo' (Solo CPU) configurando el servicio slm-engine."
    if "ollama:latest not found" in q:
        return "Sugerencia: No se encontró la imagen de Ollama. Confirma tu conexión a internet o haz pull manualmente con 'docker pull ollama/ollama:latest'."
    if "exited" in q:
        return "Sugerencia: Un contenedor crítico se detuvo inesperadamente. Revisa los logs de ese contenedor para determinar si falta memoria (OOM) o configuración de puertos."
    
    return "Sugerencia: Por favor, revisa detalladamente la sección de Troubleshooting del README para el error reportado."


# Configuramos la dualidad:
# - Ejecución como script principal: arranca el servidor MCP estándar por stdio para Cursor/Claude.
# - Alternativa web: Servidor FastAPI mapeando las herramientas (para que Streamlit conecte y consuma fácilmente por HTTP GET)
app = FastAPI(title="Zyrabit Installer - Diagnostic API")

class StatusResponse(BaseModel):
    status: str
    suggested_fix: str

@app.get("/diagnose", response_model=StatusResponse)
def diagnose_endpoint():
    status = check_system_status()
    # Ejecutamos una evaluación simple para proveer la fix automáticamente
    fix = suggest_fix("exited") if "Exited" in status else "Sistemas estables aparentemente."
    if "GPU" in status or "error" in status.lower():
        fix = suggest_fix("gpu")
    return StatusResponse(status=status, suggested_fix=fix)

# En FastMCP actual podemos inyectar la FastMCP Starlette app si usamos transorte SSE,
# pero para mantener una conexión estúpida con Streamlit, usamos FastAPI puro encima.

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8001)
    else:
        # Arrancar en modo stdio MCP si es ejecutado por consola, ej por Claude/Cursor
        mcp.run()
