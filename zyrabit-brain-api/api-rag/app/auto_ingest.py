import os
import logging
from . import services

logger = logging.getLogger("uvicorn.error")

def run_auto_ingest():
    """
    Scans the repository for documentation files (README, docs) and ingests them.
    """
    logger.info("Starting Zyrabit Auto-Ingest Protocol...")
    
    # 1. Path to README in the root (mounted in Docker)
    readme_path = "/app/README.md"
    if os.path.exists(readme_path):
        try:
            logger.info("Ingesting root README.md...")
            services.process_and_ingest_file(readme_path)
            logger.info("README.md ingested successfully.")
        except Exception as e:
            logger.error(f"Failed to ingest README.md: {e}")
    else:
        logger.warning(f"README.md not found at {readme_path}")

    # 2. Path to other docs if any
    docs_dir = "/app/docs"
    if os.path.isdir(docs_dir):
        for entry in os.listdir(docs_dir):
            if entry.endswith((".md", ".txt")):
                full_path = os.path.join(docs_dir, entry)
                try:
                    logger.info(f"Ingesting documentation: {entry}")
                    services.process_and_ingest_file(full_path)
                except Exception as e:
                    logger.error(f"Failed to ingest {entry}: {e}")

    logger.info("Auto-Ingest Protocol Completed.")

if __name__ == "__main__":
    run_auto_ingest()
