# --- Streamlit UI ---
st.set_page_config(page_title="Smart File Compressor", layout="wide")
st.markdown(
    """
    <style>
        body, .stApp {
            background-color: #a0aabd;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📂 Smart File Compressor")

st.sidebar.header("Compression Settings")
level = st.sidebar.selectbox("Choose PDF Compression Level", [
    "Recommended", "High", "Ultra", "Extreme80", "Extreme90", "Extreme92", "ExtremeMax"
])

st.markdown("Upload files to compress all PDFs according to the selected level and retain folder structure.")

uploaded = st.file_uploader("📁 Upload files", accept_multiple_files=True)

if uploaded and st.button("🚀 Compress & Download"):
    with st.spinner("Processing your files..."):
        output_folder = process_files(uploaded, level)

    zip_buffer = zip_files_with_structure(output_folder)
    st.success("✅ Done! Your compressed files are ready.")
    st.download_button("📦 Download ZIP", zip_buffer, file_name="Compressed_Structured.zip", mime="application/zip")
