try:
    import tiktoken
except ImportError:
    import unittest.mock as mock
    tiktoken = mock.MagicMock()
import logging
from typing import List, Dict, Any

logger = logging.getLogger("zyrabit.api")

class ContextManager:
    """
    V2.0 Sovereign Context Manager (The "Kai" Strategy).
    Handles precise token budgeting and prompt construction for SLMs.
    """
    
    # Standard Budget for 4k Context (adjust if model supports 32k)
    TOTAL_BUDGET = 4096
    SYSTEM_RESERVE = 1000 # Increased slightly for profile
    MEMORY_RESERVE = 1000
    TOOLS_RESERVE = 600
    RAG_RESERVE = TOTAL_BUDGET - (SYSTEM_RESERVE + MEMORY_RESERVE + TOOLS_RESERVE)

    def __init__(self, model_name: str = "qwen2.5:7b"):
        # Default to cl100k_base (standard for many modern models)
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoder = tiktoken.get_encoding("gpt-4") # Fallback
        
        self.model_name = model_name

    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))

    def trim_history(self, history: List[Dict[str, str]], budget: int = MEMORY_RESERVE) -> str:
        """Keep only the last N turns that fit in the budget."""
        formatted_history = []
        current_tokens = 0
        total_history_tokens = sum([self.count_tokens(f"{m['role']}: {m['content']}\n") for m in history])
        
        # Process from newest to oldest
        for msg in reversed(history):
            msg_text = f"{msg['role']}: {msg['content']}\n"
            msg_tokens = self.count_tokens(msg_text)
            
            if current_tokens + msg_tokens > budget:
                break
            
            formatted_history.insert(0, msg_text)
            current_tokens += msg_tokens
        
        discarded = total_history_tokens - current_tokens
        if discarded > 0:
            logger.warning(f"📉 Context Budgeter: Discarded {discarded} tokens from History to fit budget.")
            
        return "".join(formatted_history)

    def trim_rag_context(self, documents: List[Any], budget: int = RAG_RESERVE) -> str:
        """Rank-Based Trimming for RAG fragments."""
        selected_fragments = []
        current_tokens = 0
        total_rag_tokens = sum([self.count_tokens(d.page_content if hasattr(d, 'page_content') else str(d)) for d in documents])
        
        for doc in documents:
            text = doc.page_content if hasattr(doc, 'page_content') else str(doc)
            tokens = self.count_tokens(text)
            
            if current_tokens + tokens > budget:
                continue
            
            selected_fragments.append(text)
            current_tokens += tokens
            
        discarded = total_rag_tokens - current_tokens
        if discarded > 0:
            logger.warning(f"📉 Context Budgeter: Discarded {discarded} tokens from RAG Context (Notes too long).")
            
        return "\n\n".join(selected_fragments)

    PERSONA_PROMPTS = {
        "marketing": "Eres un experto en Marketing Estratégico y Crecimiento. Tu objetivo es ayudar a Abraham Gomez a escalar Zyrabit. Tu tono es creativo, orientado a datos, persuasivo y disruptivo. Enfócate en el ROI y el Brand Equity.",
        "sales": "Eres un cerrador de ventas de alto nivel. Te enfocas en la conversión, el manejo de objeciones y la propuesta de valor clara. Tu tono es directo, motivador e influyente. No aceptes un no por respuesta.",
        "admin": "Eres un asistente administrativo y de operaciones impecable. Te enfocas en la eficiencia, el orden y la gestión de procesos. Tu tono es formal, organizado y altamente pragmático.",
        "aviation": "Eres un copiloto virtual y experto en aviación avanzada. Te enfocas en la seguridad, los procedimientos estándar (SOPs), la navegación y la precisión técnica. Tu tono es calmado, profesional y ultra-preciso.",
        "general": "Eres Kai, el cerebro soberano de Zyrabit. Un asistente de IA de alto nivel diseñado para Abraham Gomez. Tu objetivo es ser eficiente, seguro y discreto."
    }

    def build_final_prompt(self, system_prompt: str, history: List[Dict[str, str]], rag_docs: List[Any], user_query: str, user_profile: Dict[str, Any] = None) -> str:
        # 1. System Prompt (Highest Priority)
        # 2. History (Contextual continuity)
        # 3. RAG Context (Knowledge)
        # 4. User Query (The trigger)
        
        trimmed_history = self.trim_history(history)
        trimmed_rag = self.trim_rag_context(rag_docs)
        
        persona_key = user_profile.get("persona", "general") if user_profile else "general"
        persona_desc = self.PERSONA_PROMPTS.get(persona_key, self.PERSONA_PROMPTS["general"])
        tone = user_profile.get("tone", "professional") if user_profile else "professional"

        profile_str = ""
        if user_profile and user_profile.get("onboarding_completed"):
            profile_str = f"USUARIO: {user_profile.get('name')} | ROL: {user_profile.get('role')} | EXPERTISE: {user_profile.get('interests')}\n"

        final_prompt = f"""### INSTRUCCIONES DE IDENTIDAD (PERSONA):
{persona_desc}
TONO REQUERIDO: {tone.upper()}

### PERFIL DEL USUARIO:
{profile_str if profile_str else "Usuario nuevo (sin perfil)."}

### CONOCIMIENTO RELEVANTE (RAG):
{trimmed_rag if trimmed_rag else "No se encontraron documentos relevantes."}

### HISTORIAL DE CONVERSACIÓN:
{trimmed_history if trimmed_history else "No hay historial previo."}

### CONSULTA ACTUAL:
{user_query}
"""
        return final_prompt

