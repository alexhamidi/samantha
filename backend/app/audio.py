from pydub import AudioSegment
from pathlib import Path
import os

MAX_CHUNK_DURATION_MS = 29000  # 29 seconds

def get_audio_duration(file_path: str) -> float:
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0  # seconds

def split_audio(file_path: str, output_dir: str) -> list[dict]:
    audio = AudioSegment.from_file(file_path)
    duration_ms = len(audio)
    
    # If audio is under 29s, no need to split
    if duration_ms <= MAX_CHUNK_DURATION_MS:
        return [{
            "chunk_index": 0,
            "file_path": file_path,
            "start_time": 0.0,
            "end_time": duration_ms / 1000.0
        }]
    
    # Split into chunks - ensure directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    chunks = []
    chunk_index = 0
    
    for start_ms in range(0, duration_ms, MAX_CHUNK_DURATION_MS):
        end_ms = min(start_ms + MAX_CHUNK_DURATION_MS, duration_ms)
        chunk = audio[start_ms:end_ms]
        
        chunk_path = os.path.join(output_dir, f"chunk_{chunk_index}.mp3")
        chunk.export(chunk_path, format="mp3")
        
        chunks.append({
            "chunk_index": chunk_index,
            "file_path": chunk_path,
            "start_time": start_ms / 1000.0,
            "end_time": end_ms / 1000.0
        })
        chunk_index += 1
    
    return chunks

def combine_audio_files(file_paths: list[str], output_path: str, format: str = "wav"):
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    combined = AudioSegment.empty()
    
    for file_path in file_paths:
        audio = AudioSegment.from_file(file_path)
        combined += audio
    
    combined.export(output_path, format=format)

