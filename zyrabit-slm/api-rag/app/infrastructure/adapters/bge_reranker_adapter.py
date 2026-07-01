from typing import List, Tuple
import re
from app.domain.ports.reranker_port import ReRankerPort
from langchain_core.documents import Document

class BGEReRankerAdapter(ReRankerPort):
    """
    Sovereign ReRanker: Implements a lightweight, fast, and local term-overlap 
    relevance scorer to avoid contextual pollution without hitting model execution latency.
    """
    
    def _stem(self, word: str) -> str:
        # Strip common Spanish/English suffixes for plurals and gender/form agreements
        if word.endswith("es"):
            word = word[:-2]
        elif word.endswith("s"):
            word = word[:-1]
        
        if word.endswith("as") or word.endswith("os"):
            word = word[:-2]
        elif word.endswith("a") or word.endswith("o"):
            word = word[:-1]
            
        return word

    def _tokenize(self, text: str) -> set:
        # Lowercase, strip punctuation and get unique words of length > 2
        words = re.findall(r'\b\w{3,}\b', text.lower())
        # Filter common spanish/english stop words to focus on content keywords
        stopwords = {
            "dame", "un", "una", "unos", "unas", "de", "del", "el", "la", "los", "las", "y", "o", "en", "para", 
            "con", "sobre", "por", "que", "como", "este", "esta", "estos", "estas", "su", "sus", "the", "and", 
            "for", "with", "about", "your", "that", "this", "are"
        }
        return {self._stem(w) for w in words if w not in stopwords}


    def rerank(self, query: str, documents: List[Document]) -> List[Tuple[Document, float]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [(doc, 1.0) for doc in documents]

        ranked_docs = []
        for doc in documents:
            doc_tokens = self._tokenize(doc.page_content)
            if not doc_tokens:
                score = 0.0
            else:
                intersection = query_tokens.intersection(doc_tokens)
                # Jaccard similarity coefficient with bias towards query coverage
                score = len(intersection) / len(query_tokens)
                
                # Bonus score if exact phrases match or if terms appear multiple times
                # (simple term frequency scaling)
                tf_bonus = sum(doc.page_content.lower().count(t) for t in intersection) * 0.05
                score = min(score + tf_bonus, 1.0)

            ranked_docs.append((doc, score))

        # Sort by score descending
        ranked_docs.sort(key=lambda x: x[1], reverse=True)
        return ranked_docs
