import os
import logging
from typing import Optional

logger = logging.getLogger("zyrabit.api")

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

class IngestionValidator:
    """
    Fail-Fast validator for document ingestion.
    """
    
    @staticmethod
    def validate(file_path: str) -> Optional[str]:
        """
        Runs all validations. Returns error message if invalid, None otherwise.
        """
        # 1. Check existence
        if not os.path.exists(file_path):
            return "File does not exist"
            
        # 2. Check size (Fail-Fast)
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            logger.warning(f"⚠️ Rejecting file {file_path}: Size {file_size} bytes exceeds limit of {MAX_FILE_SIZE_MB}MB")
            return f"File too large ({file_size / (1024*1024):.2f}MB). Limit is {MAX_FILE_SIZE_MB}MB."
            
        # 3. Check extension
        allowed_extensions = [".pdf", ".md"]
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in allowed_extensions:
            return f"Unsupported file type ({ext}). Allowed: {', '.join(allowed_extensions)}"
            
        return None
