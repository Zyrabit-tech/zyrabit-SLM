from fastapi import Request
from app.domain.use_cases.chat_use_case import ChatUseCase
from app.domain.use_cases.ingest_use_case import IngestUseCase
from app.domain.services.gatekeeper import Gatekeeper
from app.infrastructure.shared.cache import global_cache

def get_vector_store(request: Request):
    return request.app.state.vector_store

def get_inference_provider(request: Request):
    return request.app.state.inference_provider

def get_chat_use_case(request: Request) -> ChatUseCase:
    """
    Factory dependency for ChatUseCase with Cache.
    """
    if not request.app.state.inference_provider:
        raise HTTPException(status_code=503, detail="Inference Provider not initialized")
    
    return ChatUseCase(
        inference_provider=request.app.state.inference_provider,
        retriever_service=request.app.state.retriever_service,
        gatekeeper=Gatekeeper,
        cache=global_cache
    )

def get_ingest_use_case(request: Request) -> IngestUseCase:
    """
    Factory dependency for IngestUseCase.
    """
    return IngestUseCase(
        vector_store=request.app.state.vector_store
    )
