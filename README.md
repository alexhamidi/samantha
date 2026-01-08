# Samantha

A wrapper for Meta's [SAM Audio Editor](https://aidemos.meta.com/segment-anything/editor/segment-audio) that handles audio files of **any length** (Meta's demo has a 29-second limit).

Upload an MP3/WAV and edit it with natural language prompts like "remove vocals" or "isolate the drums". Audio >29s is automatically split into chunks, processed in parallel, and stitched back together.

## Setup

Install ffmpeg and Chrome, then:

```bash
# Backend
cd backend
uv pip install -r requirements.txt
playwright install-deps

# Frontend
cd frontend
bun install
```

## Run

```bash
# Backend (port 8000)
cd backend && python run.py

# Frontend (port 3000)
cd frontend && bun dev
```

Open `http://localhost:3000`

## Notes

Built on top of Meta's [SAM (Segment Anything Model)](https://segment-anything.com/) audio demo.

This tool automates Meta's playground. By using it, you agree to their [Terms](https://aidemos.meta.com/segment-anything/terms/) and [Usage Policy](https://aidemos.meta.com/segment-anything/usage/). Personal/non-commercial use only.

Processed outputs are stored locally in the `backend/uploads/` and `backend/outputs/` directories and metadata is stored in `backend/data.json`.