import streamlit as st
import os
import shutil
import subprocess
from pathlib import Path
import humanfriendly
import uuid
from io import BytesIO
import zipfile

# --- Session & directories ---
SESSION_ID = st.session_state.get("session_id", str(uuid.uuid4()))
st.session_state["session_id"] = SESSION_ID
BASE_TEMP_DIR = f"temp_storage_{SESSION_ID}"
INPUT_DIR = os.path.join(BASE_TEMP_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_TEMP_DIR, "output")
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- PDF Compression ---
def compress_pdf_ghostscript(input_path, output_path, quality="recommended"):
    quality_map = {
        "low": "/printer",
        "recommended": "/ebook",
        "high": "/screen",
        "ultra": "/screen"
    }
    dpi_flags = {
        "ultra": ["-dDownsampleColorImages=true", "-dColorImageResolution=50"]
    }
    quality_flag = quality_map.get(quality.lower(), "/ebook")
    extra_flags = dpi_flags.get(quality.lower(), [])

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

# --- ZIP Extractor ---
def extract_zip(file, destination):
    with zipfile.ZipFile(file, 'r') as zip_ref:
        zip_ref.extractall(destination)

# --- Folder Zipper ---
def zip_files_with_structure(base_folder, files_to_include):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files_to_include:
            if Path(path).exists():
                rel_path = Path(path).relative_to(base_folder)
                zf.write(path, arcname=str(rel_path))
    zip_buffer.seek(0)
    return zip_buffer

# --- File Processor ---
def process_files_to_target_size(uploaded_files, target_size):
    working_dir = Path(OUTPUT_DIR)
    if working_dir.exists():
        shutil.rmtree(working_dir)
    working_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded & extract zips
    for file in uploaded_files:
        ext = file.name.split(".")[-1].lower()
        file_path = working_dir / file.name
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        if ext == "zip":
            extract_zip(file_path, working_dir)
            file_path.unlink()

    all_files = [Path(root) / f for root, _, files in os.walk(working_dir) for f in files]

    total_size, selected_files, all_files_flat = 0, [], list(all_files)

    compression_levels = ["ultra", "high", "recommended"]
    for level in compression_levels:
        temp_dir = working_dir / f"temp_{level}"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        shutil.copytree(working_dir, temp_dir, dirs_exist_ok=True)

        temp_selected = []
        temp_total_size = 0
        temp_all = [Path(root) / f for root, _, files in os.walk(temp_dir) for f in files]

        for i, file in enumerate(temp_all):
            ext = file.suffix.lower()
            orig_size = file.stat().st_size

            if ext == ".pdf":
                out_file = file.parent / f"compressed_{file.name}"
                compress_pdf_ghostscript(file, out_file, level)
                if out_file.exists():
                    compressed_size = out_file.stat().st_size
                    if temp_total_size + compressed_size <= target_size:
                        temp_selected.append(out_file)
                        temp_total_size += compressed_size
                    file.unlink()
                    out_file.rename(file)
            else:
                if temp_total_size + orig_size <= target_size:
                    temp_selected.append(file)
                    temp_total_size += orig_size

        if temp_total_size <= target_size:
            return temp_selected, all_files_flat

    return None, all_files_flat

# --- UI ---
st.set_page_config(page_title="📧 Email File Size Optimizer", layout="wide")
st.title("📦 File Compressor & Size-Limiter")

st.markdown("""
Upload multiple files (PDFs, DOCX, ZIPs). This app:
- Compresses only PDFs (if needed)
- Keeps others untouched
- Ensures total size is under your limit
""")

max_size_input = st.text_input("🎯 Target Total Size (e.g., 5MB or 10MB):", "7MB")
try:
    target_bytes = humanfriendly.parse_size(max_size_input)
except:
    st.error("❌ Invalid size format. Use 5MB, 10MB, etc.")
    st.stop()

uploaded_files = st.file_uploader("📁 Upload Files (PDFs, ZIPs, etc)", accept_multiple_files=True)

if uploaded_files and st.button("🚀 Optimize and Download"):
    with st.spinner("Processing..."):
        selected, all_files = process_files_to_target_size(uploaded_files, target_bytes)

    if selected is None:
        st.error("❌ Could not fit all files within size limit. Try removing a few.")
    else:
        zip_selected = zip_files_with_structure(OUTPUT_DIR, selected)
        zip_all = zip_files_with_structure(OUTPUT_DIR, all_files)

        st.success(f"✅ Done! {len(selected)} files included under the {max_size_input} limit.")
        st.download_button("📦 Download Optimized ZIP", zip_selected, file_name="Optimized_Files.zip", mime="application/zip")
        st.download_button("📁 Download All Files ZIP", zip_all, file_name="All_Files.zip", mime="application/zip")
