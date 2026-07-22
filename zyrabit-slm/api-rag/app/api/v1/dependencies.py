from fastapi import Request, HTTPException
from app.domain.use_cases.chat_use_case import ChatUseCase
from app.domain.use_cases.ingest_use_case import IngestUseCase

def get_vector_store(request: Request):
    if not hasattr(request.app.state, 'vector_store'):
        raise HTTPException(status_code=503, detail="Vector store is initializing")
    return request.app.state.vector_store

def get_inference_provider(request: Request):
    if not hasattr(request.app.state, 'inference_provider'):
        raise HTTPException(status_code=503, detail="Inference provider is initializing")
    return request.app.state.inference_provider

def get_chat_use_case(request: Request) -> ChatUseCase:
    """
    Returns the pre-initialized ChatUseCase from app state.
    """
    if not hasattr(request.app.state, 'chat_use_case'):
        raise HTTPException(status_code=503, detail="Chat Use Case not initialized")
    return request.app.state.chat_use_case

def get_ingest_use_case(request: Request) -> IngestUseCase:
    """
    Returns the pre-initialized IngestUseCase from app state.
    """
    if not hasattr(request.app.state, 'ingest_use_case'):
        raise HTTPException(status_code=503, detail="Ingest Use Case not initialized")
    return request.app.state.ingest_use_case

def get_retriever_service(request: Request):
    """
    Returns the pre-initialized HybridRetrieverService from app state.
    """
    if not hasattr(request.app.state, 'retriever_service'):
        raise HTTPException(status_code=503, detail="Retriever service not initialized")
    return request.app.state.retriever_service

def get_state_aggregator(request: Request):
    """
    Returns an instance of StateAggregatorUseCase.
    """
    from app.application.use_cases.state_aggregator_use_case import StateAggregatorUseCase
    return StateAggregatorUseCase()


