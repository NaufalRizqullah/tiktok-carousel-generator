import os
import sys
import json
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiktok_carousel import TikTokCarouselGenerator

# Page config
st.set_page_config(
    page_title="TikTok Carousel Generator",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #0f0f0f;
    }
    .stTextInput > div > div > input {
        background-color: #1a1a1a;
        color: white;
    }
    .stSelectbox > div > div > div {
        background-color: #1a1a1a;
        color: white;
    }
    h1, h2, h3 {
        color: #ff0050 !important;
    }
    .stButton > button {
        background-color: #ff0050;
        color: white;
        border: none;
    }
    .stButton > button:hover {
        background-color: #ff3377;
    }
    .stTextArea > div > div > textarea {
        background-color: #1a1a1a;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Project paths
PROJECT_DIR = "/home/clawuser/.openclaw/workspace/tiktok-carousel-generator"
CONTEXT_FILE = os.path.join(PROJECT_DIR, "context.txt")

# Initialize session state for storing generated data
if 'generated' not in st.session_state:
    st.session_state.generated = False
if 'metadata' not in st.session_state:
    st.session_state.metadata = None
if 'slides_dir' not in st.session_state:
    st.session_state.slides_dir = None
if 'slide_files' not in st.session_state:
    st.session_state.slide_files = []

def load_context():
    """Load context.txt content"""
    if os.path.exists(CONTEXT_FILE):
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def save_context(content):
    """Save context.txt content"""
    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

def send_to_telegram_via_subprocess(metadata, slides_dir, slide_files):
    """Send to Telegram using subprocess to call OpenClaw message tool"""
    try:
        import subprocess
        
        # Prepare message
        title = metadata.get("tiktok_title", "")
        description = metadata.get("tiktok_description", "")
        message_text = f"{title}\n\n{description}"
        
        # Create a Python script that uses the message tool
        telegram_script = f'''
import json
import sys
sys.path.insert(0, "{PROJECT_DIR}")

from message import message

# Send title + description
message(
    action="send",
    target="721762130",
    message="""{message_text}"""
)
'''
        
        # Write and execute
        with open("/tmp/send_telegram.py", "w") as f:
            f.write(telegram_script)
        
        # Try to run it
        result = subprocess.run(
            [sys.executable, "/tmp/send_telegram.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Send images
            for slide_file in slide_files:
                slide_path = os.path.join(slides_dir, slide_file)
                img_script = f'''
import sys
sys.path.insert(0, "{PROJECT_DIR}")
from message import message
message(
    action="send",
    target="721762130",
    media="{slide_path}"
)
'''
                with open("/tmp/send_img.py", "w") as f:
                    f.write(img_script)
                subprocess.run([sys.executable, "/tmp/send_img.py"], capture_output=True, timeout=30)
            
            return True
        else:
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def main():
    st.title("🎬 TikTok Carousel Generator")
    st.markdown("Buat konten TikTok carousel dengan AI dalam hitungan menit!")
    
    # Context Editor Section
    with st.expander("📝 Edit Context (Untuk Seri Konten)", expanded=False):
        context_content = st.text_area(
            "Isi Context.txt",
            value=load_context(),
            height=200,
            help="Gunakan ini untuk membuat konten seri. AI tidak akan mengulang poin dari context sebelumnya."
        )
        if st.button("💾 Simpan Context"):
            save_context(context_content)
            st.success("✅ Context tersimpan!")
    
    # Sidebar - Settings
    with st.sidebar:
        st.header("⚙️ Pengaturan")
        
        topic = st.text_input("📝 Topik", placeholder="Contoh: Tips Diet Pemula")
        
        num_slides = st.slider("📊 Jumlah Slide", min_value=3, max_value=10, value=7)
        
        style = st.selectbox(
            "🎨 Gaya Teks",
            ["outline", "box", "box-title-content"],
            index=2,
            format_func=lambda x: {
                "outline": "Outline (Klasik TikTok)",
                "box": "Box (Kotak Transparan)",
                "box-title-content": "Box Title Content (Cerita)"
            }.get(x, x)
        )
        
        output_format = st.selectbox(
            "📐 Format Output",
            ["portrait", "square", "portrait3_4"],
            index=2,
            format_func=lambda x: {
                "portrait": "Portrait (9:16) - TikTok Story",
                "square": "Square (1:1) - Instagram Feed",
                "portrait3_4": "Portrait 3:4 - TikTok Feed"
            }.get(x, x)
        )
        
        generate_btn = st.button("🚀 Generate Sekarang", use_container_width=True)
        
        # Clear data button in sidebar
        if st.session_state.generated:
            st.markdown("---")
            if st.button("🔄 Generate Ulang / Clear", use_container_width=True):
                st.session_state.generated = False
                st.session_state.metadata = None
                st.session_state.slides_dir = None
                st.session_state.slide_files = []
                st.rerun()
    
    # Main content - Generate
    if generate_btn:
        if not topic:
            st.error("❌ Mohon isi topik terlebih dahulu!")
            return
        
        if not os.getenv("GOOGLE_API_KEY") or not os.getenv("PEXELS_API_KEY"):
            st.error("❌ API Key belum diatur! Mohon isi di file .env")
            return
        
        with st.spinner("🧠 Sedang generate konten..."):
            try:
                # Initialize generator
                generator = TikTokCarouselGenerator(
                    pexels_key=os.getenv("PEXELS_API_KEY"),
                    gemini_key=os.getenv("GOOGLE_API_KEY"),
                    output_format=output_format
                )
                
                # Run generation
                generator.run(topic=topic, num_slides=num_slides, style=style)
                
                # Load metadata
                metadata_path = os.path.join(generator.output_dir, "metadata.json")
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                
                # Get slides
                slides_dir = generator.output_dir
                slide_files = sorted([f for f in os.listdir(slides_dir) if f.endswith(".jpg")])
                
                # Store in session state
                st.session_state.generated = True
                st.session_state.metadata = metadata
                st.session_state.slides_dir = slides_dir
                st.session_state.slide_files = slide_files
                
                st.success("✅ Berhasil digenerate!")
                
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    # Display results if generated
    if st.session_state.generated and st.session_state.metadata:
        metadata = st.session_state.metadata
        slides_dir = st.session_state.slides_dir
        slide_files = st.session_state.slide_files
        
        st.markdown("---")
        st.subheader("📱 Metadata")
        st.markdown(f"**Judul:** {metadata['tiktok_title']}")
        st.markdown(f"**Deskripsi:** {metadata['tiktok_description']}")
        st.markdown("**Tags:** " + " ".join([f"`#{tag}`" for tag in metadata['tiktok_tags']]))
        
        st.markdown("---")
        st.subheader("🖼️ Hasil Slide")
        
        # Create columns for display
        cols = st.columns(3)
        for i, slide_file in enumerate(slide_files):
            slide_path = os.path.join(slides_dir, slide_file)
            with cols[i % 3]:
                st.image(slide_path, caption=slide_file, use_container_width=True)
                
                # Download button - doesn't clear data
                with open(slide_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download",
                        data=f,
                        file_name=slide_file,
                        mime="image/jpeg",
                        key=f"dl_{slide_file}"
                    )
        
        # Action buttons
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📦 Download Semua")
            # Create zip file
            import zipfile
            zip_path = os.path.join(slides_dir, "all_slides.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for slide_file in slide_files:
                    slide_path = os.path.join(slides_dir, slide_file)
                    zipf.write(slide_path, slide_file)
            
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Semua (ZIP)",
                    data=f,
                    file_name="tiktok_carousel_slides.zip",
                    mime="application/zip",
                    key="dl_zip"
                )
            
            metadata_path = os.path.join(slides_dir, "metadata.json")
            with open(metadata_path, "r") as f:
                st.download_button(
                    label="📄 Download Metadata (JSON)",
                    data=f,
                    file_name="metadata.json",
                    mime="application/json",
                    key="dl_meta"
                )
        
        with col2:
            st.subheader("📤 Kirim ke Telegram")
            
            # Try automatic send
            if st.button("🚀 Kirim Otomatis ke Telegram", use_container_width=True):
                with st.spinner("Mengirim ke Telegram..."):
                    success = send_to_telegram_via_subprocess(metadata, slides_dir, slide_files)
                    if success:
                        st.success("✅ Berhasil dikirim ke Telegram!")
                    else:
                        st.error("❌ Gagal otomatis, coba manual di bawah!")
            
            # Manual options - doesn't clear data
            st.markdown("**Atau Kirim Manual:**")
            telegram_caption = f"{metadata['tiktok_title']}\n\n{metadata['tiktok_description']}"
            st.code(telegram_caption)
            st.button("📋 Copy Caption", on_click=st.write, args=("Caption disalin!",), key="copy_btn")
            
            st.info("💡 Semua data tetap tampil sampai kamu klik 'Generate Ulang'")
    
    # Info section
    st.markdown("---")
    st.markdown("""
    ### 📋 Cara Penggunaan
    1. Masukkan topik konten yang ingin dibuat
    2. (Opsional) Edit context.txt untuk seri konten
    3. Atur jumlah slide, gaya teks, dan format output
    4. Klik tombol "Generate Sekarang"
    5. Hasil akan tetap tampil sampai Generate ulang
    6. Download atau Kirim ke Telegram - data tidak akan hilang!
    
    ### 🔧 Technology Stack
    - **Backend**: Python, Google Gemini AI, Pexels API
    - **Image Processing**: Pillow
    - **Frontend**: Streamlit
    """)
    
    # API Status
    with st.expander("🔐 Status API Key"):
        google_key = os.getenv("GOOGLE_API_KEY", "")
        pexels_key = os.getenv("PEXELS_API_KEY", "")
        
        st.markdown(f"**Google API Key:** {'✅ Terhubung' if google_key else '❌ Tidak ditemukan'}")
        st.markdown(f"**Pexels API Key:** {'✅ Terhubung' if pexels_key else '❌ Tidak ditemukan'}")

if __name__ == "__main__":
    main()