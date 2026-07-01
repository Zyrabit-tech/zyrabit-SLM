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
            elif ext == ".docx":
                logger.info(f"📑 Extracting DOCX text: {file_path}")
                md_text = PDFProcessor.extract_docx_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")
            
            if not md_text or not md_text.strip():
                raise ValueError("Document contains no extractable text. This file may be scanned, image-only, or empty. Please use an OCR tool first.")
            
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

    @staticmethod
    def extract_docx_text(file_path: str) -> str:
        """
        Reads a DOCX file and extracts paragraphs and tables as plain text.
        """
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            content = []
            
            # Paragraphs
            for p in doc.paragraphs:
                if p.text.strip():
                    content.append(p.text)
                    
            # Tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        content.append(" | ".join(row_text))
                        
            return "\n\n".join(content)
        except Exception as e:
            logger.error(f"❌ DOCX parsing failed: {e}")
            raise RuntimeError(f"Failed to read DOCX content: {e}")
