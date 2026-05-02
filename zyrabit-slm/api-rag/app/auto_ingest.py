import os
import logging
from app.domain.use_cases.ingest_use_case import IngestUseCase

logger = logging.getLogger("zyrabit.api")

async def run_auto_ingest(vector_store, retriever_service=None):
    """
    V5.0 Auto-Ingest: Ingests core documentation using the High-Precision pipeline.
    """
    logger.info("🚀 Starting Zyrabit Auto-Ingest Protocol V5.0...")
    
    ingest_use_case = IngestUseCase(vector_store, retriever_service)
    
    # Locate README (Docker vs Local)
    readme_path = "/app/README.md"
    if not os.path.exists(readme_path):
        readme_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../README.md"))
        
    if os.path.exists(readme_path):
        try:
            logger.info(f"📄 Auto-Ingesting: {readme_path}")
            res = await ingest_use_case.execute(readme_path, domain="zyrabit-docs")
            if res.get("status") == "success":
                logger.info("✅ README.md auto-ingested successfully.")
            else:
                logger.error(f"⚠️ README.md ingestion failed: {res.get('message')}")
        except Exception as e:
            logger.error(f"❌ Failed to auto-ingest README.md: {e}")
    else:
        logger.warning(f"⚠️ README.md not found. Skipping auto-ingest.")
    
    logger.info("🏁 Auto-Ingest Protocol Completed.")
