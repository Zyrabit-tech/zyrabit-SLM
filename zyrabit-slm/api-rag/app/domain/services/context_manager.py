import logging
import math
from typing import Any, Dict, List

try:
    import tiktoken
except ImportError:
    tiktoken = None

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
    # A document answer must retain complete evidence passages. The previous
    # 1.5k-token allowance could drop the numeric conclusion on later pages.
    RAG_RESERVE = 2400

    # ReAct-specific budgets (separated from direct inference path)
    REACT_SYSTEM_BUDGET = 800   # Identity + compact ReAct instructions
    REACT_TOOLS_BUDGET = 400    # Only lazy-loaded relevant tools
    REACT_HISTORY_BUDGET = 600  # Max 3 conversation turns
    REACT_RAG_BUDGET = 500      # Top-3 fragments trimmed
    REACT_RESPONSE_RESERVE = 796  # Guaranteed space for model response

    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.encoder = None
        if tiktoken is not None:
            for encoding_name in ("cl100k_base", "o200k_base"):
                try:
                    self.encoder = tiktoken.get_encoding(encoding_name)
                    break
                except Exception:
                    continue
        self.model_name = model_name

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0

        if self.encoder is not None:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                pass

        # Offline-safe estimate: roughly 1 token per 4 characters, with a floor for short text.
        estimated = math.ceil(len(text) / 4)
        return max(estimated, len(text.split()))

    def estimate_react_budget(self, system_prompt: str, user_prompt: str) -> dict:
        """Estimate token usage for a ReAct iteration and return budget status."""
        sys_tokens = self.count_tokens(system_prompt)
        usr_tokens = self.count_tokens(user_prompt)
        total = sys_tokens + usr_tokens
        limit = int(self.TOTAL_BUDGET * 0.70)
        return {
            "system_tokens": sys_tokens,
            "user_tokens": usr_tokens,
            "total": total,
            "limit": limit,
            "over_budget": total > limit,
            "remaining": max(limit - total, 0)
        }

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
        "marketing": "You are an expert in Strategic Marketing and Growth. Your goal is to help Abraham Gomez scale Zyrabit. Your tone is creative, data-driven, persuasive, and disruptive. Focus on ROI and Brand Equity.",
        "sales": "You are a top-tier sales closer. You focus on conversion, objection handling, and clear value propositions. Your tone is direct, motivational, and influential. Do not take no for an answer.",
        "admin": "You are an impeccable administrative and operations assistant. You focus on efficiency, order, and process management. Your tone is formal, organized, and highly pragmatic.",
        "aviation": "You are a virtual copilot and advanced aviation expert. You focus on safety, standard operating procedures (SOPs), navigation, and technical precision. Your tone is calm, professional, and ultra-precise.",
        "general": "You are {assistant_name}, the sovereign intelligence engine of Zyrabit. A high-level AI assistant built for Abraham Gomez. Your goal is to be efficient, secure, and discreet."
    }

    def build_final_prompt(self, system_prompt: str, history: List[Dict[str, str]], rag_docs: List[Any], user_query: str, user_profile: Dict[str, Any] = None, source: str = "WEB") -> str:
        """
        V2.0 Sovereign Prompt Construction.
        Dynamically injects Identity, MCP Tools, Profile, and Context.
        """
        # 1. Identity Locking
        assistant_name = user_profile.get("assistant_name", "Zyra") if user_profile else "Zyra"
        persona_key = user_profile.get("persona", "general") if user_profile else "general"
        persona_raw = self.PERSONA_PROMPTS.get(persona_key, self.PERSONA_PROMPTS["general"])
        
        # Format the identity with assistant name
        try:
            persona_desc = persona_raw.format(assistant_name=assistant_name)
        except:
            persona_desc = persona_raw
        
        # Override identity for specific channels
        if source == "TELEGRAM":
            persona_desc = f"You are {assistant_name}, the sovereign notification bridge for Zyrabit. Your goal is to assist Abraham Gomez via Telegram. Be concise and efficient."
        else:
            persona_desc = f"Primary Identity: {assistant_name}.\n" + persona_desc


        # 2. Dynamic Tool Discovery Injection (Phase 4)
        from app.domain.services.mcp_service import mcp
        try:
            mcp_tools = "[AVAILABLE_MCP_TOOLS]:\n"
            for t in mcp._tool_manager._tools.values():
                mcp_tools += f"- {t.name}: {t.description}\n"
        except Exception:
            # Fallback if mock/error
            mcp_tools = """[AVAILABLE_MCP_TOOLS]:
- import_to_vault(source_path: str, destination_name: str): Securely move files to vault.
- list_vault_stats(): Get metadata about the sovereign vault index.
- send_telegram_notification(message: str): Sends a secure, PII-masked alert to Telegram.
"""

        # [NEW] Discriminative RAG: Detect operational/drafting queries to compress context dynamically
        is_operational = any(w in user_query.lower() for w in [
            "mensaje", "redactar", "borrador", "plantilla", "generar", "escribe", "draft", 
            "resumen", "summary", "escribir", "crear mensaje"
        ])
        
        if is_operational:
            rag_budget = 400
            logger.info("⚡ Discriminative RAG: Dynamic Context Compression active (Operational query -> budget capped at 400 tokens).")
        else:
            rag_budget = self.RAG_RESERVE

        trimmed_history = self.trim_history(history)
        trimmed_rag = self.trim_rag_context(rag_docs, budget=rag_budget)
        
        tone = user_profile.get("tone", "professional") if user_profile else "professional"


        profile_str = ""
        if user_profile and user_profile.get("onboarding_completed"):
            profile_str = f"USER: {user_profile.get('name')} | ROLE: {user_profile.get('role')}\n"

        rag_section = ""
        if trimmed_rag:
            rag_section = f"""### RELEVANT KNOWLEDGE (RAG):
{trimmed_rag}

### EVIDENCE RULES:
When RAG knowledge is provided, respond only with explicit statements from that context.
For figures, dates, and conditions, copy the exact value from the document; do not estimate or substitute.
If the information does not appear in the context, state that clearly instead of inferring it.
"""

        final_prompt = f"""### SOVEREIGN IDENTITY:
{persona_desc}
ACTIVE CHANNEL: {source}
TONE: {tone.upper()}

### USER PROFILE:
{profile_str if profile_str else "Active user."}
{rag_section}
### CONVERSATION HISTORY:
{trimmed_history if trimmed_history else "No prior history."}

### CURRENT QUERY:
{user_query}
"""
        return final_prompt
