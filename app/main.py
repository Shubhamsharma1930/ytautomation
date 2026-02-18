from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse
import os, traceback

from .utils import new_job, set_job_status, get_job, save_upload_file, ensure_output_dir
from .audio import smooth_fade_mixtape_from_files
from .video import make_video_from_audio
from .description import generate_youtube_description_with_timestamps
from .config import OUTPUT_DIR, ALLOWED_AUDIO_EXT

app = FastAPI(title="Mixtape Automation API")
ensure_output_dir()

# Base directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_ROOT, exist_ok=True)


# ==============================
# Upload Track
# ==============================
@app.post("/upload-track/")
async def upload_track(file: UploadFile = File(...), job_prefix: str = Form(None)):
    job_prefix = job_prefix or "default"

    dest_dir = os.path.join(UPLOAD_ROOT, job_prefix)
    os.makedirs(dest_dir, exist_ok=True)

    dest_path = os.path.join(dest_dir, file.filename)
    save_upload_file(file, dest_path)

    return {"uploaded": dest_path}


# ==============================
# Create Mixtape
# ==============================
@app.post("/create-mixtape/")
def create_mixtape(background_tasks: BackgroundTasks,
                   job_prefix: str = Form(...),
                   transition_ms: int = Form(10000),
                   output_name: str = Form("mixtape.mp3")):

    job_id = new_job()

    def task():
        try:
            folder = os.path.join(UPLOAD_ROOT, job_prefix)

            files = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith(ALLOWED_AUDIO_EXT)
            ]

            if not files:
                set_job_status(job_id, "failed", error="No audio files found")
                return

            set_job_status(job_id, "running")

            out_path = smooth_fade_mixtape_from_files(
                files,
                output_filename=output_name,
                transition_ms=transition_ms
            )

            set_job_status(job_id, "completed", result=out_path)

        except Exception as e:
            set_job_status(job_id, "failed", error=str(e) + "\n" + traceback.format_exc())

    background_tasks.add_task(task)
    return {"job_id": job_id}


# ==============================
# Make Video
# ==============================
@app.post("/make-video/")
def make_video(background_tasks: BackgroundTasks,
               image: UploadFile = File(...),
               job_prefix: str = Form(...),
               output_name: str = Form("mixtape_vid.mp4")):

    job_id = new_job()

    def task():
        try:
            set_job_status(job_id, "running")

            # Save image in upload folder
            dest_dir = os.path.join(UPLOAD_ROOT, job_prefix)
            os.makedirs(dest_dir, exist_ok=True)

            image_path = os.path.join(dest_dir, image.filename)
            save_upload_file(image, image_path)

            # Audio path (generated mixtape)
            audio_path = os.path.join(OUTPUT_DIR, "mixtape.mp3")

            if not os.path.exists(audio_path):
                raise FileNotFoundError("Mixtape audio not found: " + audio_path)

            out = make_video_from_audio(
                image_path,
                audio_path,
                output_filename=output_name
            )

            set_job_status(job_id, "completed", result=out)

        except Exception as e:
            set_job_status(job_id, "failed", error=str(e))

    background_tasks.add_task(task)
    return {"job_id": job_id}


# ==============================
# Generate Description
# ==============================
@app.post("/generate-description/")
def generate_description(job_prefix: str = Form(...),
                         mixtape_name: str = Form("Mixtape"),
                         genre: str = Form("Mix")):

    folder = os.path.join(UPLOAD_ROOT, job_prefix)

    files = [
        os.path.join(folder, f)
        for f in sorted(os.listdir(folder))
        if f.lower().endswith(ALLOWED_AUDIO_EXT)
    ]

    if not files:
        return {"error": "no tracks found"}

    desc = generate_youtube_description_with_timestamps(
        files,
        mixtape_name=mixtape_name,
        genre=genre
    )

    return {"description": desc}


# ==============================
# Job Status
# ==============================
@app.get("/job/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return JSONResponse({"error": "job not found"}, status_code=404)
    return job


# ==============================
# Download
# ==============================
@app.get("/download/")
def download_file(path: str):
    if not os.path.exists(path):
        return JSONResponse({"error": "file not found"}, status_code=404)
    return FileResponse(path, media_type="application/octet-stream", filename=os.path.basename(path))
