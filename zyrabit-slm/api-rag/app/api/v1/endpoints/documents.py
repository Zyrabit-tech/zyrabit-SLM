# pyrefly: ignore [missing-import]
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Request
import os
import logging
from app.infrastructure.shared.config import DOCS_DIR
from app.api.v1.dependencies import get_ingest_use_case
from app.domain.use_cases.ingest_use_case import IngestUseCase
from app.domain.services.whisper_transcription_service import WhisperTranscriptionService

logger = logging.getLogger("uvicorn.error")
router = APIRouter()

@router.get("/documents")
async def list_documents():
    """Lists all files in the document source directory."""
    if not os.path.exists(DOCS_DIR):
        return {"documents": []}
    
    files = []
    for f in os.listdir(DOCS_DIR):
        if os.path.isfile(os.path.join(DOCS_DIR, f)):
            stats = os.stat(os.path.join(DOCS_DIR, f))
            files.append({
                "filename": f,
                "size_bytes": stats.st_size
            })
    return {"documents": files}

async def background_ingestion_task(file_path: str, filename: str, ingest_use_case: IngestUseCase, sio):
    """
    Ingests the file and notifies the user via Socket.io upon completion.
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        audio_extensions = (".wav", ".mp3", ".m4a", ".mp4", ".webm", ".mpeg", ".mpga", ".ogg", ".flac")
        
        if ext in audio_extensions:
            logger.info(f"🎙️ Audio/Video file detected for ingestion: {filename}. Transcribing with Whisper...")
            whisper_service = WhisperTranscriptionService()
            transcription_res = whisper_service.transcribe(file_path)
            
            # Save transcription as a markdown file
            transcript_text = transcription_res["text"]
            transcript_filename = f"{os.path.splitext(filename)[0]}_transcript.md"
            transcript_path = os.path.join(os.path.dirname(file_path), transcript_filename)
            
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(f"# Transcription of {filename}\n\n{transcript_text}\n")
            
            # Swap target file to the markdown transcript path
            file_path = transcript_path
            filename = transcript_filename

        logger.info(f"🧬 Processing background ingestion for: {filename}")
        res = await ingest_use_case.execute(file_path)
        
        if not sio:
            return

        status = res.get("status")
        if status == "success":
            await sio.emit("chat_response", {
                "response": f"¡Listo! He procesado el documento '{filename}' y ya está disponible en mi Vault. ¿Qué te gustaría que analicemos de él?",
                "metadata": {
                    "decision": "ingest-proactive",
                    "latency_ms": 0,
                    "sources": [filename],
                    "rag_hits": 1
                }
            })
            logger.info(f"📢 Proactive notification sent for {filename}")
        elif status == "skipped":
            logger.info(f"⏩ Document {filename} is already up to date. Skipping user notification.")
        else:
            error_msg = res.get("message", "Error desconocido durante la ingesta.")
            await sio.emit("chat_response", {
                "response": f"❌ Lo siento, no he podido procesar el documento '{filename}'. Razón: {error_msg}",
                "metadata": {
                    "decision": "ingest-error",
                    "latency_ms": 0,
                    "sources": [filename],
                    "rag_hits": 0
                }
            })
            logger.info(f"📢 Proactive error notification sent for {filename} (Reason: {error_msg})")
            
    except Exception as e:
        logger.error(f"❌ Background ingestion failed for {filename}: {e}")
        if sio:
            await sio.emit("chat_response", {
                "response": f"❌ Ocurrió un error inesperado al procesar el documento '{filename}'. Razón: {str(e)}",
                "metadata": {
                    "decision": "ingest-error",
                    "latency_ms": 0,
                    "sources": [filename],
                    "rag_hits": 0
                }
            })

@router.post("/ingest")
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    ingest_use_case: IngestUseCase = Depends(get_ingest_use_case)
):
    """
    Uploads and indexes a document before reporting it as available.
    """
    os.makedirs(DOCS_DIR, exist_ok=True)
    file_path = os.path.join(DOCS_DIR, file.filename)
    
    try:
        # 1. Save file locally
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        # 2. Do not expose the document to chat until it is searchable.
        result = await ingest_use_case.execute(file_path)
        if result.get("status") not in {"success", "skipped"}:
            raise HTTPException(status_code=422, detail=result.get("message", "Document could not be indexed."))
        return {"status": "ready", "message": f"File {file.filename} is indexed and ready for retrieval.", "filename": file.filename}
    except Exception as e:
        logger.error(f"Failed to initiate ingestion for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@router.post("/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
):
    """
    OpenAI-compatible transcription endpoint using Whisper.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    audio_extensions = (".wav", ".mp3", ".m4a", ".mp4", ".webm", ".mpeg", ".mpga", ".ogg", ".flac")
    if ext not in audio_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {ext}")
        
    os.makedirs(DOCS_DIR, exist_ok=True)
    temp_path = os.path.join(DOCS_DIR, f"temp_{file.filename}")
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())
            
        whisper_service = WhisperTranscriptionService()
        result = whisper_service.transcribe(temp_path)
        return {"text": result["text"]}
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
