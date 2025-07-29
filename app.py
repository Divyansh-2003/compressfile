import streamlit as st
import os
import zipfile
import shutil
import tempfile
from pathlib import Path
from compress_pdf import compress_pdf

# UI Setup
st.set_page_config(page_title="Smart File Compressor", page_icon="📄", layout="wide")
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
        }
        .css-1v0mbdj, .st-emotion-cache-1v0mbdj {
            border: 1px solid #dfe1e6;
            border-radius: 6px;
            padding: 1.5rem;
            background-color: #f4f5f7;
            margin-bottom: 1rem;
        }
        .stButton>button {
            background-color: #0052CC;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }
        .stButton>button:hover {
            background-color: #0747A6;
        }
        .css-1v0mbdj h3 {
            color: #172B4D;
            font-size: 18px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📄 Smart File Compressor")
st.write("Easily compress PDF files while retaining folder structure.")

compression_levels = {
    "Balanced": {"pdfsetting": "/ebook", "dpi": None},
    "Optimized": {"pdfsetting": "/screen", "dpi": None},
    "Compact": {"pdfsetting": "/screen", "dpi": None},
    "Slim": {"pdfsetting": "/screen", "dpi": 80},
    "Lean": {"pdfsetting": "/screen", "dpi": 60},
    "Thin": {"pdfsetting": "/screen", "dpi": 50},
    "Minimal": {"pdfsetting": "/screen", "dpi": 40},
}

uploaded_files = st.file_uploader("Upload PDFs or ZIP folders", type=["pdf", "zip"], accept_multiple_files=True)
compression_choice = st.selectbox("Choose Compression Level", list(compression_levels.keys()))

if st.button("Compress"):
    with tempfile.TemporaryDirectory() as input_dir, tempfile.TemporaryDirectory() as output_dir:
        extracted_dir = os.path.join(input_dir, "extracted")
        os.makedirs(extracted_dir, exist_ok=True)

        # Save uploaded files or extract zip contents
        for file in uploaded_files:
            file_path = os.path.join(input_dir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.read())
            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extracted_dir)
            else:
                shutil.move(file_path, os.path.join(extracted_dir, file.name))

        # Walk through extracted_dir and compress all PDFs
        for foldername, subfolders, filenames in os.walk(extracted_dir):
            for filename in filenames:
                if filename.lower().endswith(".pdf"):
                    input_pdf_path = os.path.join(foldername, filename)
                    rel_path = os.path.relpath(foldername, extracted_dir)
                    output_folder = os.path.join(output_dir, rel_path)
                    os.makedirs(output_folder, exist_ok=True)
                    output_pdf_path = os.path.join(output_folder, filename)
                    compress_pdf(
                        input_pdf_path,
                        output_pdf_path,
                        compression_levels[compression_choice]["pdfsetting"],
                        compression_levels[compression_choice]["dpi"]
                    )
                else:
                    # Copy non-PDF files as-is
                    rel_path = os.path.relpath(foldername, extracted_dir)
                    output_folder = os.path.join(output_dir, rel_path)
                    os.makedirs(output_folder, exist_ok=True)
                    shutil.copy(os.path.join(foldername, filename), os.path.join(output_folder, filename))

        # Create final zip
        final_zip_path = os.path.join(tempfile.gettempdir(), "compressed_files.zip")
        with zipfile.ZipFile(final_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, output_dir)
                    zipf.write(abs_path, arcname=rel_path)

        with open(final_zip_path, "rb") as f:
            st.download_button("Download Compressed ZIP", f, file_name="compressed_files.zip")
