import logging
from typing import List, Dict, Any
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger("zyrabit.api")

class DocumentChunker:
    """
    Splits Markdown documents structurally based on headers and size.
    """
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Headers to split on
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]

    def split(self, documents: List[Document], domain: str = "general") -> List[Document]:
        """
        Structural split: Header-based -> Character-based.
        """
        logger.info(f"🧱 Splitting {len(documents)} documents with Structural Chunking...")
        
        # 1. Split by Markdown Headers
        header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=self.headers_to_split_on)
        
        # 2. Refine with character-based splitter if sections are too large
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        final_chunks = []
        for doc in documents:
            # First level: Headers
            header_splits = header_splitter.split_text(doc.page_content)
            
            # Second level: Sub-splitting large sections
            refined_splits = text_splitter.split_documents(header_splits)
            
            # Inject mandatory metadata
            for chunk in refined_splits:
                chunk.metadata.update({
                    "source": doc.metadata.get("source"),
                    "domain": domain,
                    "version": "1.0",
                    "type": "high-precision"
                })
                final_chunks.append(chunk)
                
        logger.info(f"✅ Generated {len(final_chunks)} chunks with domain='{domain}'")
        return final_chunks
