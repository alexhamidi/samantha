# SAM Wrapper

A frontend for Meta's SAM audio editor that lets users upload audio and edit it with natural language prompts.

## How It Works

1. **User uploads an MP3/WAV** → Backend splits audio into ≤29s chunks (SAM's limit) → Each chunk is uploaded to SAM in parallel via browser automation → Each chunk gets a `sam_media_id`

2. **User enters a prompt** (e.g. "remove vocals") → Backend processes all chunks in parallel with the same prompt → Each chunk generates 3 outputs (combined, isolated, without_isolated) → Outputs are stitched back together

3. **User sees 3 audio players** → Can download any, enter another prompt (runs against original upload chunks), or start over with a new file

## Backend

**`POST /upload`**
- Receives audio file from user
- Analyzes duration with pydub
- If >29s, splits into chunks (stored in DB)
- Uploads all chunks to SAM in parallel (each in separate browser context)
- Each chunk navigates to SAM, clicks accept, uploads via file chooser
- Waits for URL to change to `?media_id={id}` for each chunk
- Stores `sam_media_id` for each chunk
- Returns `upload_id` for polling

**`GET /status/upload/{upload_id}`**
- Returns `{status: "processing" | "complete" | "failed", chunks: N, duration_seconds}`
- Frontend polls this until status is complete

**`POST /process`**
- Receives `upload_id` and `prompt`
- Looks up all chunks for this upload (with their `sam_media_id`s)
- Processes all chunks in parallel (each in separate browser context)
- Each chunk: loads SAM with `?media_id={sam_media_id}`, types prompt, downloads 3 outputs
- Combines chunk outputs for each type (combined, isolated, without_isolated) using pydub
- Saves combined files to `/outputs/{output_id}/`
- Returns `output_id` for polling

**`GET /status/output/{output_id}`**
- Returns `{status: "processing" | "complete" | "failed", outputs: {combined, isolated, without_isolated}}`
- Frontend polls this until status is complete

**`GET /outputs/{output_id}/*.wav`**
- Static file serving for downloaded audio

## Key Behaviors

- **Chunking**: Audio >29s is split into chunks. Each chunk is processed independently and then recombined.

- **Parallel processing**: All chunks are uploaded/processed in parallel for speed.

- **Browser reuse**: One browser stays running. Each chunk operation gets an isolated context (fast startup, no state leakage).

- **Media persistence**: SAM's `media_id` URLs are permanent. We store each chunk's ID and reuse for all prompts.

- **One job per user**: Users can't run multiple operations simultaneously. Frontend polls until complete.

- **Prompts are independent**: Each prompt runs against the original upload chunks, not chained on previous outputs.

## Database

Uses local JSON file (`backend/data.json`) with three tables:
- **uploads**: Tracks overall upload status, duration
- **chunks**: One row per chunk (upload_id, chunk_index, sam_media_id, start_time, end_time)
- **outputs**: Tracks prompt processing status and final output URLs

Thread-safe with file locking for concurrent operations.
