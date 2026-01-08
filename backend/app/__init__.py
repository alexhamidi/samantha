from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import re

from app.browser import browser_manager
from app.api.v1.endpoints import health
from app.endpoints import router as endpoints_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await browser_manager.start()
    yield
    await browser_manager.stop()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)


async def range_requests_response(
    request: Request, file_path: str, media_type: str = "audio/mpeg"
):
    """Returns a file response with support for HTTP range requests."""
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range header
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            
            # Ensure valid range
            start = max(0, min(start, file_size - 1))
            end = max(start, min(end, file_size - 1))
            chunk_size = end - start + 1
            
            # Read the requested chunk
            with open(file_path, "rb") as f:
                f.seek(start)
                data = f.read(chunk_size)
            
            from fastapi.responses import Response
            return Response(
                content=data,
                status_code=206,  # Partial Content
                headers={
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(chunk_size),
                    "Content-Type": media_type,
                },
            )
    
    # No range header, return full file
    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Accept-Ranges": "bytes"},
    )


@app.get("/uploads/{file_path:path}")
async def serve_upload(request: Request, file_path: str):
    full_path = UPLOADS_DIR / file_path
    if not full_path.exists() or not full_path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_type = "audio/mpeg" if file_path.endswith(".mp3") else "audio/wav"
    return await range_requests_response(request, str(full_path), media_type)


@app.get("/outputs/{file_path:path}")
async def serve_output(request: Request, file_path: str):
    full_path = OUTPUTS_DIR / file_path
    if not full_path.exists() or not full_path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_type = "audio/mpeg" if file_path.endswith(".mp3") else "audio/wav"
    return await range_requests_response(request, str(full_path), media_type)


app.include_router(health.router, prefix="/api/v1")
app.include_router(endpoints_router)
