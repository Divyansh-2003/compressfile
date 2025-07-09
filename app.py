import streamlit as st
import os
import shutil
import subprocess
from pathlib import Path
import uuid
from io import BytesIO
import zipfile
from concurrent.futures import ThreadPoolExecutor

# --- Streamlit UI Setup ---
st.set_page_config(page_title="Smart File Compressor", layout="wide")
st.markdown("""
    <style>
        body, .stApp {
            background-color: #d3d3d3;
        }
    </style>
    """, unsafe_allow_html=True)

st.title("📂 Smart File Compressor")
st.sidebar.header("Compression Settings")
level = st.sidebar.selectbox("Choose PDF Compression Level", [
    "Recommended", "High", "Ultra", "Extreme80", "Extreme90", "Extreme92", "ExtremeMax"
])

# --- Session Paths ---
SESSION_ID = st.session_state.get("session_id", str(uuid.uuid4()))
st.session_state["session_id"] = SESSION_ID
BASE_TEMP_DIR = f"temp_storage_{SESSION_ID}"
INPUT_DIR = os.path.join(BASE_TEMP_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_TEMP_DIR, "output")
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Compression Maps ---
QUALITY_MAP = {
    "Recommended": "/ebook",
    "High": "/screen",
    "Ultra": "/screen",
    "Extreme80": "/screen",
    "Extreme90": "/screen",
    "Extreme92": "/screen",
    "ExtremeMax": "/screen"
}

DPI_FLAGS = {
    "Extreme80": ["-dDownsampleColorImages=true", "-dColorImageResolution=80"],
    "Extreme90": ["-dDownsampleColorImages=true", "-dColorImageResolution=60"],
    "Extreme92": ["-dDownsampleColorImages=true", "-dColorImageResolution=50"],
    "ExtremeMax": ["-dDownsampleColorImages=true", "-dColorImageResolution=40"]
}

# --- Core Functions ---
def compress_pdf(input_path, output_path, quality):
    quality_flag = QUALITY_MAP.get(quality, "/ebook")
    extra_flags = DPI_FLAGS.get(quality, [])
    try:
        subprocess.run([
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={quality_flag}",
            *extra_flags,
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output_path}",
            str(input_path)
        ], check=True)
    except subprocess.CalledProcessError:
        shutil.copy(input_path, output_path)

def extract_zip(file, destination):
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(destination)

def zip_files_with_structure(base_folder):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(base_folder):
            for f in files:
                full_path = Path(root) / f
                relative_path = full_path.relative_to(base_folder)
                zf.write(full_path, arcname=str(relative_path))
    zip_buffer.seek(0)
    return zip_buffer

def compress_task(fpath, quality):
    if fpath.suffix.lower() == ".pdf":
        out_path = fpath.parent / f"compressed_{fpath.name}"
        compress_pdf(fpath, out_path, quality)
        fpath.unlink()
        out_path.rename(fpath)

def process_files(files, quality):
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    temp_dir = Path(OUTPUT_DIR)

    # Step 1: Save and extract ZIPs
    for file in files:
        ext = file.name.split(".")[-1].lower()
        path = temp_dir / file.name
        with open(path, "wb") as f:
            f.write(file.getbuffer())
        if ext == "zip":
            extract_zip(path, temp_dir)
            path.unlink()

    # Step 2: Collect all files
    all_files = []
    for root, _, file_list in os.walk(temp_dir):
        for fname in file_list:
            all_files.append(Path(root) / fname)

    # Step 3: Compress PDFs in parallel
    progress = st.progress(0)
    total = len(all_files)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for i, fpath in enumerate(all_files):
            if fpath.suffix.lower() == ".pdf":
                futures.append(executor.submit(compress_task, fpath, quality))
            progress.progress((i + 1) / total)

        # Wait for all tasks
        for i, f in enumerate(futures):
            f.result()

    return temp_dir

# --- File Upload UI ---
st.markdown("Upload files to compress all PDFs and preserve folder structure in ZIP.")

uploaded = st.file_uploader("📁 Upload files", accept_multiple_files=True)

if uploaded and st.button("🚀 Compress & Download"):
    with st.spinner("Processing your files..."):
        output_folder = process_files(uploaded, level)

    zip_buffer = zip_files_with_structure(output_folder)
    st.success("✅ Done! Your compressed files are ready.")
    st.download_button("📦 Download ZIP", zip_buffer, file_name="Compressed_Structured.zip", mime="application/zip")
