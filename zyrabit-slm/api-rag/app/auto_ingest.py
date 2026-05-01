import os
import logging
from app.domain.use_cases.ingest_use_case import IngestUseCase

logger = logging.getLogger("uvicorn.error")

def run_auto_ingest(vector_store):
    """
    Scans the repository for documentation files (README, docs) and ingests them.
    Receives the vector_store from the lifespan manager.
    """
    logger.info("🚀 Starting Zyrabit Auto-Ingest Protocol...")
    
    ingest_use_case = IngestUseCase(vector_store)
    
    # 1. Path to README in the root (mounted in Docker)
    readme_path = "/app/README.md"
    if os.path.exists(readme_path):
        try:
            logger.info("📄 Auto-Ingesting root README.md...")
            # Note: execute is async, we wrap in a simple way for the bootstrap
            import asyncio
            asyncio.run(ingest_use_case.execute(readme_path))
        except Exception as e:
            logger.error(f"❌ Failed to auto-ingest README.md: {e}")
    
    logger.info("✅ Auto-Ingest Protocol Completed.")
