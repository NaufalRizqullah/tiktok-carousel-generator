import os
import json

from . import config
from .utils import download_font_if_missing, read_context, append_context, sanitize_text, get_font_path
from .content import ContentGenerator
from .image_source import PexelsImageSource
from .renderer import SlideRenderer


class TikTokCarouselGenerator:
    """Orchestrator utama yang menggabungkan semua modul menjadi satu pipeline."""

    def __init__(self, pexels_key: str, gemini_key: str, 
                 title_font_family: str = None, title_font_weight: int = None,
                 content_font_family: str = None, content_font_weight: int = None,
                 output_dir: str = "output"):
        
        tf_family = title_font_family or config.TITLE_FONT_FAMILY
        tf_weight = title_font_weight or config.TITLE_FONT_WEIGHT
        self.title_font_path = get_font_path(tf_family, tf_weight)

        cf_family = content_font_family or config.CONTENT_FONT_FAMILY
        cf_weight = content_font_weight or config.CONTENT_FONT_WEIGHT
        self.content_font_path = get_font_path(cf_family, cf_weight)
        
        self.output_dir = output_dir

        # Inisialisasi sub-modul
        self.content_gen = ContentGenerator(api_key=gemini_key)
        self.image_source = PexelsImageSource(api_key=pexels_key)
        self.renderer = SlideRenderer(title_font_path=self.title_font_path, content_font_path=self.content_font_path)

    def run(self, topic: str, num_slides: int, style: str) -> None:
        """Jalankan pipeline: generate konten → cari gambar → render slide → simpan."""
        download_font_if_missing(self.title_font_path)
        download_font_if_missing(self.content_font_path)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        try:
            # 1. Dapatkan JSON yang berisi Metadata + Slides
            previous_context = read_context(config.CONTEXT_FILE)
            full_data = self.content_gen.generate(topic, num_slides, style, previous_context)

            # 2. Ekstraksi data
            tiktok_title = full_data.get("tiktok_title", "Tanpa Judul")
            tiktok_desc = full_data.get("tiktok_description", "")
            tiktok_tags = full_data.get("tiktok_tags", [])
            slides = full_data.get("slides", [])

            # 3. Print Metadata ke Console
            print("\n" + "=" * 50)
            print("📱 METADATA TIKTOK POST")
            print("=" * 50)
            print(f"📍 Judul     : {tiktok_title}")
            print(f"📍 Deskripsi : {tiktok_desc}")

            # Format hashtag agar ada tanda '#' nya jika AI lupa
            formatted_tags = " ".join([f"#{t.replace('#', '')}" for t in tiktok_tags])
            print(f"📍 Tags      : {formatted_tags}")
            print("=" * 50 + "\n")

            # 4. Simpan Metadata ke file metadata.json
            metadata_filepath = os.path.join(self.output_dir, "metadata.json")
            with open(metadata_filepath, "w", encoding="utf-8") as f:
                json.dump(full_data, f, ensure_ascii=False, indent=4)
            print(f"💾 Metadata berhasil disimpan di: {metadata_filepath}")

            # 5. Simpan isi konten ke context.txt untuk memori generasi berikutnya
            if slides:
                append_context(config.CONTEXT_FILE, topic, slides)
                print(f"📝 Sejarah konten (Context) berhasil di-update di: {config.CONTEXT_FILE}")
            else:
                print("⚠️ Peringatan: Data 'slides' kosong dari AI.")

            # 6. Proses Render Gambar Slide
            for i, slide in enumerate(slides):
                print(f"\n▶️ Memproses Slide {i} ({slide.get('type', 'unknown')})")

                font_size = config.TITLE_FONT_SIZE if slide.get("type") == "judul" else config.CONTENT_FONT_SIZE

                slide_text = slide.get("teks", "")
                slide_text = slide_text.replace(". ", ".\n\n")
                slide_title = slide.get("slide_title", "")

                # Bersihkan emoji/simbol non-BMP
                slide_text = sanitize_text(slide_text)
                slide_title = sanitize_text(slide_title)

                is_title = slide.get("type") == "judul"

                raw_img = self.image_source.get_image(slide.get("keyword_gambar", "background"))
                final_img = self.renderer.process_slide(raw_img, slide_text, font_size, style, slide_title, is_title)

                filename = os.path.join(self.output_dir, f"slide_{i:02d}.jpg")
                final_img.save(filename, quality=config.JPG_QUALITY)
                print(f"✅ Berhasil disimpan: {filename}")

            print(f"\n🎉 SELESAI! Semua file gambar dan metadata telah disimpan di folder '{self.output_dir}'.")

        except Exception as e:
            print(f"\n❌ Terjadi kesalahan saat eksekusi: {e}")
