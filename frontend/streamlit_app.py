import streamlit as st
import requests
import time

API_BASE = "http://127.0.0.1:8000"

st.title("🎵 YouTube Mixtape Automation")

job_prefix = st.text_input("Job prefix (folder name)", value="job1")

# ==============================
# Upload Tracks
# ==============================
st.header("Upload audio tracks")

uploaded = st.file_uploader(
    "Choose audio files",
    accept_multiple_files=True,
    type=["mp3","wav","m4a","aac","ogg","flac"]
)

if st.button("Upload tracks"):
    if not uploaded:
        st.warning("No files selected.")
    else:
        for f in uploaded:
            files = {"file": (f.name, f.getvalue())}
            data = {"job_prefix": job_prefix}
            r = requests.post(f"{API_BASE}/upload-track/", files=files, data=data)
            st.write(r.json())

# ==============================
# Create Mixtape
# ==============================
st.header("Create mixtape")

transition_ms = st.number_input("Transition ms", value=10000)
output_name = st.text_input("Output MP3 filename", value="mixtape.mp3")

if st.button("Start mixtape"):

    data = {
        "job_prefix": job_prefix,
        "transition_ms": str(transition_ms),
        "output_name": output_name
    }

    r = requests.post(f"{API_BASE}/create-mixtape/", data=data)
    response = r.json()
    st.write(response)

    job_id = response.get("job_id")

    if job_id:
        status_placeholder = st.empty()
        for _ in range(60):
            s = requests.get(f"{API_BASE}/job/{job_id}").json()
            status_placeholder.json(s)

            if s.get("status") in ("completed", "failed"):
                break
            time.sleep(1)

# ==============================
# Generate Description
# ==============================
st.header("Generate YouTube description")

mixtape_name = st.text_input("Mixtape name", value="Bollywood Hindi Songs Mix")

if st.button("Generate description"):

    r = requests.post(
        f"{API_BASE}/generate-description/",
        data={
            "job_prefix": job_prefix,
            "mixtape_name": mixtape_name,
            "genre": "Bollywood Romantic"
        }
    )

    st.text_area("Description", value=r.json().get("description",""), height=300)

# ==============================
# Create Video
# ==============================
st.header("Make video from mixtape")

image_file = st.file_uploader("Background image", type=["jpg","jpeg","png"])
video_name = st.text_input("Output video filename", value="mixtape_vid.mp4")

if st.button("Create video"):

    if not image_file:
        st.error("Please upload an image first.")
    else:
        files = {
            "image": (image_file.name, image_file.getvalue())
        }

        data = {
            "job_prefix": job_prefix,
            "output_name": video_name
        }

        r = requests.post(f"{API_BASE}/make-video/", files=files, data=data)
        response = r.json()
        st.write(response)

        job_id = response.get("job_id")

        if job_id:
            status_placeholder = st.empty()
            for _ in range(120):
                s = requests.get(f"{API_BASE}/job/{job_id}").json()
                status_placeholder.json(s)

                if s.get("status") in ("completed", "failed"):
                    break
                time.sleep(1)
