import os
import logging
from app.domain.use_cases.ingest_use_case import IngestUseCase

logger = logging.getLogger("zyrabit.api")

async def run_auto_ingest(vector_store):
    """
    Protocol to ensure core documentation is always in the vector store.
    """
    logger.info("🚀 Starting Zyrabit Auto-Ingest Protocol...")
    
    ingest_use_case = IngestUseCase(vector_store)
    
    # 1. Locate README (Docker vs Local)
    readme_path = "/app/README.md"
    if not os.path.exists(readme_path):
        # Attempt to find it in project root when running locally
        readme_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../README.md"))
        
    if os.path.exists(readme_path):
        try:
            logger.info(f"📄 Auto-Ingesting: {readme_path}")
            await ingest_use_case.execute(readme_path)
            logger.info("✅ README.md auto-ingested successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to auto-ingest README.md: {e}")
    else:
        logger.warning(f"⚠️ README.md not found at {readme_path}. Skipping auto-ingest.")
    
    logger.info("🏁 Auto-Ingest Protocol Completed.")
