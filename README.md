# Samantha


https://github.com/user-attachments/assets/d5d3b53d-6ac9-40fc-9776-1afc7efbe4f4


A wrapper for Meta's [SAM Audio Editor](https://aidemos.meta.com/segment-anything/editor/segment-audio) that handles audio files of **any length** (Meta's demo has a 29-second limit).

Upload an MP3/WAV/M4A and edit it with natural language prompts like "remove vocals" or "isolate the drums". Audio >29s is automatically split into chunks, processed in parallel, and stitched back together.

## Setup & Run

Run the setup script (handles everything automatically):

```bash
./setup.sh
```

The script will:
- Install ffmpeg (if not present)
- Install Chrome (if not present)
- Create a virtual environment (uses `uv` if available for faster installs)
- Install all Python dependencies
- Install Playwright and its dependencies
- Install all frontend dependencies (uses `bun` if available)
- Optionally start both backend (port 8000) and frontend (port 3000)

Then open `http://localhost:3000`

## Notes

Built on top of Meta's [SAM (Segment Anything Model)](https://segment-anything.com/) audio demo.

This tool automates Meta's playground. By using it, you agree to their [Terms](https://aidemos.meta.com/segment-anything/terms/) and [Usage Policy](https://aidemos.meta.com/segment-anything/usage/). Personal/non-commercial use only.

Processed outputs are stored locally in the `backend/uploads/` and `backend/outputs/` directories and metadata is stored in `backend/data.json`.
