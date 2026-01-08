import uuid
import asyncio
import traceback
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, Cookie, HTTPException
from pydantic import BaseModel

from app.browser import browser_manager
from app.db import db
from app.audio import split_audio, get_audio_duration, combine_audio_files

router = APIRouter()

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)


async def upload_chunk_task(upload_id: str, chunk_data: dict):
    try:
        sam_media_id = await browser_manager.upload_chunk_to_sam(chunk_data["file_path"])
        
        db.table("chunks").update({
            "sam_media_id": sam_media_id,
            "status": "complete"
        }).eq("upload_id", upload_id).eq("chunk_index", chunk_data["chunk_index"]).execute()
        
    except Exception as e:
        traceback.print_exc()
        db.table("chunks").update({
            "status": "failed",
            "error": str(e)
        }).eq("upload_id", upload_id).eq("chunk_index", chunk_data["chunk_index"]).execute()


async def run_upload_to_sam(upload_id: str, file_path: str):
    try:
        duration = get_audio_duration(file_path)
        
        # Split audio into chunks
        chunk_dir = UPLOADS_DIR / f"{upload_id}_chunks"
        chunks = split_audio(file_path, str(chunk_dir))
        
        # Create chunk records in DB
        for chunk in chunks:
            db.table("chunks").insert({
                "upload_id": upload_id,
                "chunk_index": chunk["chunk_index"],
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "status": "processing"
            }).execute()
        
        # Upload all chunks in parallel
        tasks = [upload_chunk_task(upload_id, chunk) for chunk in chunks]
        await asyncio.gather(*tasks)
        
        # Check if all chunks succeeded
        chunks_result = db.table("chunks").select("*").eq("upload_id", upload_id).execute()
        all_complete = all(c["status"] == "complete" for c in chunks_result.data)
        
        if all_complete:
            db.table("uploads").update({
                "status": "complete",
                "duration_seconds": duration
            }).eq("id", upload_id).execute()
        else:
            db.table("uploads").update({
                "status": "failed",
                "error": "Some chunks failed to upload"
            }).eq("id", upload_id).execute()
            
    except Exception as e:
        traceback.print_exc()
        db.table("uploads").update({
            "status": "failed",
            "error": str(e)
        }).eq("id", upload_id).execute()


async def process_chunk_task(output_id: str, chunk: dict, prompt: str):
    try:
        chunk_index = chunk["chunk_index"]
        sam_media_id = chunk["sam_media_id"]
        
        # Update chunk status to processing
        db.table("output_chunks").update({
            "status": "processing"
        }).eq("output_id", output_id).eq("chunk_index", chunk_index).execute()
        
        output_dir = str(OUTPUTS_DIR / output_id)
        outputs = await browser_manager.process_chunk_prompt(sam_media_id, prompt, output_dir, chunk_index)
        
        # Update chunk status to complete
        db.table("output_chunks").update({
            "status": "complete"
        }).eq("output_id", output_id).eq("chunk_index", chunk_index).execute()
        
        return {
            "chunk_index": chunk_index,
            "outputs": outputs
        }
    except Exception as e:
        traceback.print_exc()
        db.table("output_chunks").update({
            "status": "failed",
            "error": str(e)
        }).eq("output_id", output_id).eq("chunk_index", chunk_index).execute()
        raise


async def run_process_prompt(output_id: str, upload_id: str, prompt: str):
    try:
        # Ensure outputs directory exists
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Get all chunks for this upload
        chunks_result = db.table("chunks").select("*").eq("upload_id", upload_id).order("chunk_index").execute()
        chunks = chunks_result.data
        
        # Create output_chunk records for tracking progress
        for chunk in chunks:
            db.table("output_chunks").insert({
                "output_id": output_id,
                "chunk_index": chunk["chunk_index"],
                "status": "pending"
            }).execute()
        
        # Process all chunks in parallel
        tasks = [process_chunk_task(output_id, chunk, prompt) for chunk in chunks]
        chunk_results = await asyncio.gather(*tasks)
        
        # Sort by chunk_index
        chunk_results.sort(key=lambda x: x["chunk_index"])
        
        output_dir = str(OUTPUTS_DIR / output_id)
        
        # Combine outputs for each type in both WAV and MP3 formats
        for output_type in ["isolated", "without_isolated"]:
            file_paths = [result["outputs"][output_type] for result in chunk_results]
            
            # Generate WAV version
            wav_path = os.path.join(output_dir, f"{output_type}.wav")
            combine_audio_files(file_paths, wav_path, format="wav")
            
            # Generate MP3 version
            mp3_path = os.path.join(output_dir, f"{output_type}.mp3")
            combine_audio_files(file_paths, mp3_path, format="mp3")
        
        db.table("outputs").update({
            "status": "complete",
            "isolated_url": f"/outputs/{output_id}/isolated.wav",
            "without_isolated_url": f"/outputs/{output_id}/without_isolated.wav",
            "isolated_mp3_url": f"/outputs/{output_id}/isolated.mp3",
            "without_isolated_mp3_url": f"/outputs/{output_id}/without_isolated.mp3",
        }).eq("id", output_id).execute()
        
        # Update upload with latest prompt
        db.table("uploads").update({
            "last_prompt": prompt
        }).eq("id", upload_id).execute()
        
    except Exception as e:
        traceback.print_exc()
        db.table("outputs").update({
            "status": "failed",
            "error": str(e)
        }).eq("id", output_id).execute()


class ProcessRequest(BaseModel):
    upload_id: str
    prompt: str


@router.post("/upload")
async def upload(file: UploadFile, user_id: str | None = Cookie(default=None)):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id cookie required")
    
    # Ensure uploads directory exists
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    upload_id = str(uuid.uuid4())
    file_path = UPLOADS_DIR / f"{upload_id}.mp3"
    
    content = await file.read()
    file_path.write_bytes(content)
    
    # Store original filename (without extension for display)
    filename = file.filename or "Untitled"
    # Remove extension
    if "." in filename:
        filename = ".".join(filename.split(".")[:-1])
    
    db.table("uploads").insert({
        "id": upload_id,
        "user_id": user_id,
        "filename": filename,
        "status": "processing",
    }).execute()
    
    asyncio.create_task(run_upload_to_sam(upload_id, str(file_path)))
    
    return {"upload_id": upload_id}


@router.get("/status/upload/{upload_id}")
async def get_upload(upload_id: str):
    result = db.table("uploads").select("*").eq("id", upload_id).execute()
    if not result.data:
        return {"status": "not_found"}
    
    upload = result.data[0]
    
    # Get chunk status
    chunks_result = db.table("chunks").select("*").eq("upload_id", upload_id).execute()
    chunks = chunks_result.data if chunks_result.data else []
    completed_chunks = sum(1 for c in chunks if c["status"] == "complete")
    
    return {
        "status": upload["status"],
        "error": upload.get("error"),
        "chunks": len(chunks),
        "completed_chunks": completed_chunks,
        "duration_seconds": upload.get("duration_seconds"),
        "filename": upload.get("filename", "Untitled"),
        "last_prompt": upload.get("last_prompt")
    }


@router.post("/process")
async def process(req: ProcessRequest, user_id: str | None = Cookie(default=None)):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id cookie required")
    
    upload_result = db.table("uploads").select("*").eq("id", req.upload_id).execute()
    if not upload_result.data:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload = upload_result.data[0]
    if upload["status"] != "complete":
        raise HTTPException(status_code=400, detail="Upload not complete")
    
    output_id = str(uuid.uuid4())
    db.table("outputs").insert({
        "id": output_id,
        "upload_id": req.upload_id,
        "user_id": user_id,
        "prompt": req.prompt,
        "status": "processing",
    }).execute()
    
    asyncio.create_task(run_process_prompt(output_id, req.upload_id, req.prompt))
    
    return {"output_id": output_id}


@router.get("/status/output/{output_id}")
async def get_output(output_id: str):
    result = db.table("outputs").select("*").eq("id", output_id).execute()
    if not result.data:
        return {"status": "not_found"}
    
    output = result.data[0]
    
    # Get chunk progress
    chunks_result = db.table("output_chunks").select("*").eq("output_id", output_id).execute()
    chunks = chunks_result.data if chunks_result.data else []
    completed_chunks = sum(1 for c in chunks if c["status"] == "complete")
    
    response = {
        "status": output["status"],
        "error": output.get("error"),
        "chunks": len(chunks),
        "completed_chunks": completed_chunks,
        "upload_id": output.get("upload_id"),
        "prompt": output.get("prompt"),
    }
    
    if output["status"] == "complete":
        response["outputs"] = {
            "isolated": output["isolated_url"],
            "without_isolated": output["without_isolated_url"],
            "isolated_mp3": output["isolated_mp3_url"],
            "without_isolated_mp3": output["without_isolated_mp3_url"],
        }
    
    return response


@router.get("/library")
async def get_library(user_id: str | None = Cookie(default=None)):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id cookie required")
    
    # Get all completed uploads for this user
    uploads_result = db.table("uploads").select("*").eq("user_id", user_id).execute()
    
    # Filter to only completed uploads
    completed_uploads = [
        u for u in uploads_result.data
        if u.get("status") == "complete"
    ]
    
    # For each upload, get all completed outputs
    uploads_with_outputs = []
    for upload in completed_uploads:
        outputs_result = db.table("outputs").select("*").eq("upload_id", upload["id"]).execute()
        completed_outputs = [
            {
                "id": o["id"],
                "prompt": o.get("prompt", ""),
                "created_at": o.get("created_at", "")
            }
            for o in outputs_result.data
            if o.get("status") == "complete"
        ]
        
        # Sort outputs by created_at descending (most recent first)
        completed_outputs.sort(key=lambda x: x["created_at"], reverse=True)
        
        uploads_with_outputs.append({
            "id": upload["id"],
            "filename": upload.get("filename", "Untitled"),
            "created_at": upload.get("created_at", ""),
            "duration_seconds": upload.get("duration_seconds"),
            "outputs": completed_outputs
        })
    
    # Sort uploads by created_at descending (most recent first)
    uploads_with_outputs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {"uploads": uploads_with_outputs}
