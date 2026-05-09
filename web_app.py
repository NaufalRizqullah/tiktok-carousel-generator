import os
import sys
import json
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime

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
TOPIK_TIKTOK_FILE = os.path.join(PROJECT_DIR, "topik_tiktok.json")
TOPIK_LEMON8_FILE = os.path.join(PROJECT_DIR, "topik_lemon8.json")
TOPIK_QUOTES_FILE = os.path.join(PROJECT_DIR, "topik_quotes.json")


def load_topik_queue(platform):
    """Load topic queue from JSON file"""
    if platform == "tiktok":
        file_path = TOPIK_TIKTOK_FILE
    elif platform == "lemon8":
        file_path = TOPIK_LEMON8_FILE
    else:
        file_path = TOPIK_QUOTES_FILE
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"platform": platform, "version": 1, "topics": []}


def get_next_topic(platform):
    """Get the first pending topic from queue"""
    data = load_topik_queue(platform)
    for topic in data.get("topics", []):
        if topic.get("status") == "pending":
            return topic
    return None


def mark_topic_done(platform, topic_id):
    """Mark a topic as done"""
    if platform == "tiktok":
        file_path = TOPIK_TIKTOK_FILE
    elif platform == "lemon8":
        file_path = TOPIK_LEMON8_FILE
    else:
        file_path = TOPIK_QUOTES_FILE
    data = load_topik_queue(platform)
    for topic in data.get("topics", []):
        if topic.get("id") == topic_id:
            topic["status"] = "done"
            topic["processed_at"] = datetime.now().isoformat() + "Z"
            topic["telegram_sent"] = True
            break
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def skip_topic(platform, topic_id):
    """Skip a topic (mark as skipped)"""
    if platform == "tiktok":
        file_path = TOPIK_TIKTOK_FILE
    elif platform == "lemon8":
        file_path = TOPIK_LEMON8_FILE
    else:
        file_path = TOPIK_QUOTES_FILE
    data = load_topik_queue(platform)
    for topic in data.get("topics", []):
        if topic.get("id") == topic_id:
            topic["status"] = "skipped"
            topic["processed_at"] = datetime.now().isoformat() + "Z"
            break
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_queue_stats(platform):
    """Get queue statistics"""
    data = load_topik_queue(platform)
    topics = data.get("topics", [])
    pending = sum(1 for t in topics if t.get("status") == "pending")
    done = sum(1 for t in topics if t.get("status") == "done")
    skipped = sum(1 for t in topics if t.get("status") == "skipped")
    return {"total": len(topics), "pending": pending, "done": done, "skipped": skipped}


# Initialize session state for storing generated data
if "generated" not in st.session_state:
    st.session_state.generated = False
if "metadata" not in st.session_state:
    st.session_state.metadata = None
if "slides_dir" not in st.session_state:
    st.session_state.slides_dir = None
if "slide_files" not in st.session_state:
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

def clear_output_folder():
    """Clear output folder before generating new content"""
    output_dir = os.path.join(PROJECT_DIR, "output")
    if os.path.exists(output_dir):
        import shutil
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Error removing {item_path}: {e}")


def send_to_telegram_via_subagent(metadata, slides_dir, slide_files):
    """Spawn sub-agent to send to Telegram immediately"""
    try:
        import subprocess

        title = metadata.get("tiktok_title", "")
        description = metadata.get("tiktok_description", "")
        slides = [os.path.join(slides_dir, f) for f in slide_files]

        slides_list = "\n".join([f"- {s}" for s in slides])
        task = f"""INI PRIORITY TUGAS - KIRIM KE TELEGRAM SEKARANG!

Target: chat ID 721762130

LANGKAH 1 - Kirim pesan text ini:
{title}

{description}

LANGKAH 2 - Kirim gambar-gambar ini satu per satu (pake message tool action='send' media='path'):
{slides_list}

LANGKAH 3 - Setelah selesai, hapus file /tmp/telegram_queue.json jika ada

LAKUKAN SEKARANG! Jangan tunda."""

        queue_data = {
            "title": title,
            "description": description,
            "slides": slides,
            "status": "processing",
        }
        with open("/tmp/telegram_queue.json", "w") as f:
            json.dump(queue_data, f, indent=2)

        spawn_script = f"""#!/usr/bin/env python3
import json
import sys
sys.path.insert(0, "/home/clawuser/.openclaw/workspace")

try:
    from sessions_spawn import sessions_spawn

    result = sessions_spawn(
        task={task!r},
        runtime="subagent",
        timeoutSeconds=180
    )
    print("SUCCESS: Sub-agent spawned")
except Exception as e:
    print(f"Error: {{e}}")
    sys.exit(1)
"""

        with open("/tmp/spawn_agent.py", "w") as f:
            f.write(spawn_script)

        result = subprocess.run(
            [sys.executable, "/tmp/spawn_agent.py"],
            capture_output=True,
            text=True,
            timeout=15,
        )

        print(f"Spawn result: {result.stdout} {result.stderr}")
        return True

    except Exception as e:
        print(f"Error in send_to_telegram: {e}")
        return False


def main():
    st.title("🎬 TikTok Carousel Generator")
    st.markdown("Buat konten TikTok carousel dengan AI dalam hitungan menit!")

    # Platform Selection
    with st.container():
        col_plat1, col_plat2 = st.columns([1, 3])
        with col_plat1:
            platform = st.selectbox(
                "📱 Pilih Platform",
                ["tiktok", "lemon8", "quotes"],
                format_func=lambda x: {"tiktok": "TikTok", "lemon8": "Lemon8", "quotes": "Quotes"}.get(x, x),
            )
        with col_plat2:
            stats = get_queue_stats(platform)
            st.markdown(
                f"**Queue Stats:** 📋 {stats['pending']} pending | "
                f"✅ {stats['done']} done | ⏭️ {stats['skipped']} skipped"
            )

    # Get next topic from queue
    current_topic = get_next_topic(platform)

    if current_topic:
        st.info(f"📌 **Topik Saat Ini:** {current_topic.get('judul', 'N/A')}")
        st.caption(
            f"Kategori: {current_topic.get('kategori', 'N/A')} | "
            f"Urutan: #{current_topic.get('urutan', 'N/A')}"
        )
    else:
        st.warning("✅ Semua topik sudah diproses! Tambahkan topik baru di JSON file.")

    # Context Editor Section
    with st.expander("📝 Edit Context (Untuk Seri Konten)", expanded=False):
        context_content = st.text_area(
            "Isi Context.txt",
            value=load_context(),
            height=200,
            help="Gunakan ini untuk membuat konten seri. AI tidak akan mengulang poin dari context sebelumnya.",
        )
        if st.button("💾 Simpan Context"):
            save_context(context_content)
            st.success("✅ Context tersimpan!")

    # Sidebar - Settings
    with st.sidebar:
        st.header("⚙️ Pengaturan")

        default_topic = current_topic.get("judul", "") if current_topic else ""
        topic = st.text_input(
            "📝 Topik",
            value=default_topic,
            placeholder="Contoh: Tips Diet Pemula",
        )

        num_slides = st.slider("📊 Jumlah Slide", min_value=3, max_value=10, value=7)

        style = st.selectbox(
            "🎨 Gaya Teks",
            ["outline", "box", "box-title-content", "plain"],
            index=2,
            format_func=lambda x: {
                "outline": "Outline (Klasik TikTok)",
                "box": "Box (Kotak Transparan)",
                "box-title-content": "Box Title Content (Cerita)",
                "plain": "Plain (Teks Putih Polos)",
            }.get(x, x),
        )

        # Opacity slider — hanya tampil untuk style box
        box_opacity = None
        if style in ("box", "box-title-content"):
            box_opacity = st.slider(
                "🔲 Transparansi Box",
                min_value=0,
                max_value=255,
                value=235,
                help="0 = transparan penuh, 255 = solid putih",
            )

        output_format = st.selectbox(
            "📐 Format Output",
            ["portrait", "square", "portrait3_4"],
            index=2,
            format_func=lambda x: {
                "portrait": "Portrait (9:16) - TikTok Story",
                "square": "Square (1:1) - Instagram Feed",
                "portrait3_4": "Portrait 3:4 - TikTok Feed",
            }.get(x, x),
        )

        generate_btn = st.button("🚀 Generate Sekarang", use_container_width=True)

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
                generator = TikTokCarouselGenerator(
                    pexels_key=os.getenv("PEXELS_API_KEY"),
                    gemini_key=os.getenv("GOOGLE_API_KEY"),
                    output_format=output_format,
                )

                # Clear output folder first
                clear_output_folder()

                generator.run(topic=topic, num_slides=num_slides, style=style, box_opacity=box_opacity)

                metadata_path = os.path.join(generator.output_dir, "metadata.json")
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                slides_dir = generator.output_dir
                slide_files = sorted(
                    [f for f in os.listdir(slides_dir) if f.endswith(".jpg")]
                )

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
        st.markdown("**Tags:** " + " ".join([f"`#{tag}`" for tag in metadata["tiktok_tags"]]))

        st.markdown("---")
        st.subheader("🖼️ Hasil Slide")

        cols = st.columns(3)
        for i, slide_file in enumerate(slide_files):
            slide_path = os.path.join(slides_dir, slide_file)
            with cols[i % 3]:
                st.image(slide_path, caption=slide_file, use_container_width=True)

                with open(slide_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download",
                        data=f,
                        file_name=slide_file,
                        mime="image/jpeg",
                        key=f"dl_{slide_file}",
                    )

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📦 Download Semua")
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
                    key="dl_zip",
                )

            metadata_path = os.path.join(slides_dir, "metadata.json")
            with open(metadata_path, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📄 Download Metadata (JSON)",
                    data=f.read(),
                    file_name="metadata.json",
                    mime="application/json",
                    key="dl_meta",
                )

        with col2:
            st.subheader("📤 Kirim ke Telegram")

            if st.button("🚀 Kirim ke Telegram (Cepat)", use_container_width=True):
                with st.spinner("Memproses..."):
                    success = send_to_telegram_via_subagent(metadata, slides_dir, slide_files)
                    if success:
                        st.success("✅ Trigger terkirim! Agent akan memproses dalam beberapa detik...")
                    else:
                        st.warning("⚠️ Trigger failed. Queue disimpan, akan diproses heartbeat.")

        if current_topic:
            st.markdown("---")
            st.subheader("🏷️ Kelola Topik")
            col_topic1, col_topic2, col_topic3 = st.columns(3)

            topic_id = current_topic.get("id")

            with col_topic1:
                if st.button("✅ Tandai Selesai & Lanjut", use_container_width=True):
                    mark_topic_done(platform, topic_id)
                    st.success("✅ Topik ditandai selesai! Halaman akan refresh...")
                    st.rerun()

            with col_topic2:
                if st.button("⏭️ Lewati / Skip", use_container_width=True):
                    skip_topic(platform, topic_id)
                    st.info("⏭️ Topik dilewati! Halaman akan refresh...")
                    st.rerun()

            with col_topic3:
                st.caption("✅ = Sudah dikirim ke Telegram\n⏭️ = Skip ini, lanjut topik berikutnya")

            st.markdown("**Atau Kirim Manual:**")
            telegram_caption = (
                f"{metadata['tiktok_title']}\n\n{metadata['tiktok_description']}"
            )
            st.code(telegram_caption)
            st.button(
                "📋 Copy Caption",
                on_click=st.write,
                args=("Caption disalin!",),
                key="copy_btn",
            )

            st.info("💡 Semua data tetap tampil sampai kamu klik 'Generate Ulang'")

    # Info section
    st.markdown("---")
    st.markdown(
        """
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
"""
    )

    # API Status
    with st.expander("🔐 Status API Key"):
        google_key = os.getenv("GOOGLE_API_KEY", "")
        pexels_key = os.getenv("PEXELS_API_KEY", "")

        st.markdown(f"**Google API Key:** {'✅ Terhubung' if google_key else '❌ Tidak ditemukan'}")
        st.markdown(f"**Pexels API Key:** {'✅ Terhubung' if pexels_key else '❌ Tidak ditemukan'}")


if __name__ == "__main__":
    main()