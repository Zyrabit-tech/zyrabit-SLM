import os
import logging
import pymupdf4llm
from typing import List
from langchain_core.documents import Document

logger = logging.getLogger("zyrabit.api")

class PDFProcessor:
    """
    Handles PDF (via conversion) and native Markdown files.
    """
    
    @staticmethod
    def to_markdown_documents(file_path: str) -> List[Document]:
        """
        Processes a file and returns LangChain Documents in Markdown format.
        """
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == ".md":
                logger.info(f"📝 Reading native Markdown: {file_path}")
                with open(file_path, "r", encoding="utf-8") as f:
                    md_text = f.read()
            elif ext == ".pdf":
                logger.info(f"📑 Converting PDF to Markdown: {file_path}")
                md_text = pymupdf4llm.to_markdown(file_path)
            else:
                raise ValueError(f"Unsupported extension: {ext}")
            
            doc = Document(
                page_content=md_text,
                metadata={
                    "source": file_path,
                    "format": "markdown"
                }
            )
            
            return [doc]
        except Exception as e:
            logger.error(f"❌ Document processing failed: {e}")
            raise RuntimeError(f"Failed to process document: {str(e)}")
