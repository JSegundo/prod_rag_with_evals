import asyncio
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.pipeline.processor import get_processor
from app.websocket.manager import manager

router = APIRouter(prefix="/api/document")

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50MB limit")

    job_id = str(uuid4())
    file_path = Path(settings.uploads_dir) / f"{job_id}.pdf"

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Start background processing
    processor = get_processor()
    asyncio.create_task(
        processor.process_document(
            file_id=job_id,
            file_path=str(file_path),
            filename=file.filename or "unknown.pdf",
            ws_manager=manager,
        )
    )

    return {
        "jobId": job_id,
        "message": "File uploaded and processing started",
        "originalName": file.filename,
    }
