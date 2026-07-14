"""
Documentation Service — Dynamically reads and serves project documentation
directly from the repository files, avoiding duplicated content.
"""
import psutil
import platform
import sqlite3
import time
import logging
from pathlib import Path

logger = logging.getLogger("zyrabit.docs")


class DocumentationService:
    @staticmethod
    def _find_project_root() -> Path:
        """Helper to find the project root directory by searching upwards for .git or pyproject.toml."""
        current = Path(__file__).resolve().parent
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                return parent
        return current

    @classmethod
    def _read_file_content(cls, relative_path: str, fallback_content: str) -> str:
        """Reads file content from the project root, or falls back to standard text if missing."""
        root = cls._find_project_root()
        target = root / relative_path
        if target.exists() and target.is_file():
            try:
                return target.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Error reading documentation file {target}: {e}")
        return fallback_content

    @classmethod
    def get_quick_start_guide(cls, platform_name: str = "linux") -> str:
        # Read from Docusaurus fundamentals or main README
        fallback = """
# 🚀 QUICK START GUIDE
Clone the repository and run:
$ ./zyra-up.sh start
"""
        return cls._read_file_content("docs-portal/docs/getting-started/fundamentals.md", fallback)

    @classmethod
    def get_api_reference(cls, endpoint: str = "all") -> str:
        fallback = """
# 📖 API REFERENCE
Complete reference is available under /docs-portal/docs/api-reference.md.
"""
        content = cls._read_file_content("docs-portal/docs/api-reference.md", fallback)
        
        # If the user specifically wanted one part, we can filter or just return the full doc
        ep = endpoint.lower().strip()
        if ep != "all" and ep:
            # Simple substring filtering or return full
            lines = content.split("\n")
            filtered = []
            capture = False
            for line in lines:
                if line.startswith("##") or line.startswith("###"):
                    if ep in line.lower():
                        capture = True
                    else:
                        capture = False
                if capture:
                    filtered.append(line)
            if filtered:
                return f"# API Reference Section: {endpoint}\n" + "\n".join(filtered)
        return content

    @classmethod
    def get_docker_compose_example(cls, profile: str = "minimal") -> str:
        fallback = """
# 🐳 DOCKER COMPOSE CONFIGURATION
The main configuration file is located at zyrabit-slm/docker-compose.yml.
"""
        # Return the actual live docker-compose.yml from the repo!
        return cls._read_file_content("zyrabit-slm/docker-compose.yml", fallback)

    @classmethod
    def get_architecture_overview(cls) -> str:
        fallback = """
# 🏛️ ARCHITECTURE OVERVIEW
For detailed hexagonal architecture design, please consult zyrabit-slm/api-rag/app/HEXAGONAL_ARCHITECTURE.md.
"""
        return cls._read_file_content("zyrabit-slm/api-rag/app/HEXAGONAL_ARCHITECTURE.md", fallback)

    @classmethod
    def get_troubleshooting_guide(cls, error_keyword: str) -> str:
        # Check if DOCKER_DEBUG_GUIDE has tips
        fallback = """
# ⚠️ TROUBLESHOOTING GUIDE
Please check your container logs using:
$ docker compose logs
"""
        content = cls._read_file_content("DOCKER_DEBUG_GUIDE.md", fallback)
        return content

    @classmethod
    def get_environment_variables_reference(cls) -> str:
        # Read the template example.env directly
        fallback = """
# ⚙️ CONFIGURATION REFERENCE
All variables are configured in zyrabit-slm/.env.
"""
        return cls._read_file_content("zyrabit-slm/example.env", fallback)

    @staticmethod
    def run_self_diagnostic() -> str:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        sys_os = platform.system()
        
        db_ok = "OFFLINE"
        db_latency = 0.0
        try:
            from app.infrastructure.shared.state_tracker import SovereignStateManager
            start = time.time()
            with sqlite3.connect(SovereignStateManager.DB_PATH) as conn:
                conn.execute("SELECT 1")
            db_ok = "ONLINE"
            db_latency = (time.time() - start) * 1000.0
        except Exception:
            pass

        from app.core.security.api_key_store import ApiKeyStore
        api_keys_loaded = len(ApiKeyStore._keys)

        return f"""
# 🩺 SOVEREIGN SYSTEM DIAGNOSTIC REPORT

* **OS:** {sys_os} ({platform.machine()})
* **CPU Load:** {cpu}%
* **RAM Load:** {ram}%
* **SQLite State DB:** {db_ok} (latency: {db_latency:.2f}ms)
* **API Keys Loaded:** {api_keys_loaded}
* **Status:** {"OK" if db_ok == "ONLINE" and api_keys_loaded > 0 else "DEGRADED"}
"""
