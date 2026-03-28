import os
import json
import requests
import re
import time
import urllib.parse
import urllib.request
import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types

# =========================================================
# INI_VARIABLE
# Semua yang sering di-custom saya taruh di sini
# =========================================================

# File untuk menyimpan memori/konteks agar tidak mengulang poin di Part selanjutnya
INI_CONTEXT_FILE = "context.txt"

# Ukuran canvas output
INI_CANVAS_WIDTH = 1080
INI_CANVAS_HEIGHT = 1920

# Ukuran font default
INI_TITLE_FONT_SIZE = 85
INI_CONTENT_FONT_SIZE = 68

# Auto shrink font
INI_AUTO_SHRINK_TEXT = False
INI_AUTO_SHRINK_MIN_FONT_SIZE = 42
INI_AUTO_SHRINK_STEP = 2

# Area aman atas/bawah agar box tidak terlalu mentok ke tepi
INI_SAFE_TOP_BOTTOM_MARGIN = 180

# Jarak teks dari tepi kiri/kanan gambar
INI_TEXT_SIDE_MARGIN = 80

# Jarak dalam box putih
INI_BOX_PADDING_X = 55
INI_BOX_PADDING_Y = 35

# Radius sudut box
INI_BOX_RADIUS = 28

# Warna style box
INI_BOX_FILL = (255, 255, 255, 235)   # putih
INI_BOX_TEXT_FILL = (0, 0, 0)         # hitam

# Warna style outline
INI_OUTLINE_TEXT_FILL = "white"
INI_OUTLINE_STROKE_FILL = "black"
INI_OUTLINE_STROKE_RATIO = 0.08

# Spasi antar baris
INI_TEXT_LINE_SPACING = 10

# Geser posisi teks secara vertikal (0 = pas tengah)
INI_TEXT_VERTICAL_OFFSET = 0

# Kualitas JPG output
INI_JPG_QUALITY = 95

# Gemini Point text image
INI_POINTS_ONLY_TEXT = True
INI_MAX_WORDS_PER_SLIDE = 30


class TikTokCarouselGenerator:
    def __init__(self, pexels_key, gemini_key, font_path="font.ttf", output_dir="output"):
        self.pexels_key = pexels_key
        self.gemini_key = gemini_key
        self.font_path = font_path
        self.output_dir = output_dir

        # State
        self.used_pexels_ids = set()

        # Gemini Config
        self.MODEL = "gemini-2.5-flash"
        self.MAX_ATTEMPTS = 10
        self.INITIAL_WAIT_SECONDS = 60
        self.WAIT_INCREMENT_SECONDS = 30
        self.REQUEST_TIMEOUT_MS = 15 * 60 * 1000
        self.RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

    # ==========================================
    # UTILITY: DOWNLOAD FONT & CONTEXT
    # ==========================================
    def _download_font_if_missing(self):
        """Mengecek dan mendownload font default jika belum ada di lokal."""
        if not os.path.exists(self.font_path):
            print(f"📥 Font '{self.font_path}' tidak ditemukan. Mengunduh font default (Montserrat-Black)...")
            url = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Black.ttf"
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                with open(self.font_path, "wb") as f:
                    f.write(response.content)
                print("✅ Font berhasil diunduh dan siap digunakan!")
            except Exception as e:
                print(f"⚠️ Gagal mengunduh font: {e}")
                print("⚠️ Akan menggunakan font default sistem (tampilan mungkin kurang maksimal).")

    def _read_context(self):
        """Membaca file context history jika ada."""
        if os.path.exists(INI_CONTEXT_FILE):
            with open(INI_CONTEXT_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def _append_context(self, topic, slides):
        """Menyimpan poin-poin yang baru di-generate ke file context."""
        with open(INI_CONTEXT_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n[TOPIK: {topic}]\n")
            for slide in slides:
                if slide.get("type") == "konten":
                    teks = slide.get("teks", "").replace("\n", " ")
                    f.write(f"- {teks}\n")

    # ==========================================
    # MODUL 1: AI CONTENT GENERATOR (GEMINI)
    # ==========================================
    def _extract_status_code(self, exc: Exception):
        for attr in ("status_code", "code", "status"):
            value = getattr(exc, attr, None)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
        match = re.search(r"\b(408|429|500|502|503|504)\b", str(exc))
        return int(match.group(1)) if match else None

    def _is_retryable_exception(self, exc: Exception) -> bool:
        if isinstance(exc, json.JSONDecodeError):
            return True
        status_code = self._extract_status_code(exc)
        if status_code in self.RETRYABLE_STATUS_CODES:
            return True
        msg = str(exc).lower()
        transient_keywords = (
            "timeout", "temporarily unavailable", "deadline", "connection reset",
            "connection aborted", "service unavailable",
        )
        return any(k in msg for k in transient_keywords)

    def _generate_json_with_retry(self, client, prompt_text):
        last_exc = None
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                print(f"[Gemini] Attempt {attempt}/{self.MAX_ATTEMPTS}...")
                response = client.models.generate_content(
                    model=self.MODEL,
                    contents=prompt_text,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}]
                    ),
                )

                text = (response.text or "").strip()
                text = text.removeprefix("```json").removesuffix("```").strip()
                return json.loads(text)

            except Exception as exc:
                last_exc = exc
                status_code = self._extract_status_code(exc)
                retryable = self._is_retryable_exception(exc)

                print(f"[Gemini] Attempt {attempt}/{self.MAX_ATTEMPTS} gagal | status={status_code} | error={exc}")

                if (not retryable) or attempt == self.MAX_ATTEMPTS:
                    raise RuntimeError(
                        f"Gagal memanggil Gemini setelah {attempt} percobaan. status={status_code}, error={exc}"
                    ) from exc

                wait_seconds = self.INITIAL_WAIT_SECONDS + ((attempt - 1) * self.WAIT_INCREMENT_SECONDS)
                print(f"[Gemini] Retry lagi dalam {wait_seconds} detik...")
                time.sleep(wait_seconds)

        raise RuntimeError(f"Gagal memanggil Gemini. Error terakhir: {last_exc}") from last_exc

    def generate_carousel_content(self, topic, num_slides):
        if not self.gemini_key:
            raise ValueError("GOOGLE_API_KEY tidak ditemukan. Set di .env atau parameter.")

        client = genai.Client(
            api_key=self.gemini_key,
            http_options=types.HttpOptions(
                timeout=self.REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

        # Cek apakah ada context dari part sebelumnya
        previous_context = self._read_context()
        context_instruction = ""
        if previous_context:
            print(f"📚 Ditemukan {INI_CONTEXT_FILE}! Mengingatkan AI agar tidak mengulang poin lama...")
            context_instruction = f"""
            PENTING (CONTEXT HISTORY):
            Berikut adalah poin-poin yang SUDAH DIBAHAS pada part/generasi sebelumnya.
            Kamu DILARANG KERAS mengulangi poin, fakta, atau ide yang ada di bawah ini.
            Berikan poin/fakta yang sepenuhnya BARU untuk topik ini.
            
            <context_history>
            {previous_context}
            </context_history>
            """

        base_rules = f"""
        Kamu adalah pembuat konten TikTok profesional.

        Tugas:
        1. Gunakan Google Search untuk mencari fakta, data, atau tren terbaru tentang "{topic}".
        2. Kembalikan HANYA JSON valid berbentuk OBJECT, bukan array langsung.
        3. Buatkan juga judul catchy, deskripsi untuk caption, dan 3 hashtag.
        4. Jangan pakai markdown, jangan pakai ```json, jangan beri kalimat tambahan.

        {context_instruction}

        Format wajib:
        {{
            "tiktok_title": "Judul Postingan Catchy",
            "tiktok_description": "Deskripsi/caption singkat dan menarik yang memancing interaksi.",
            "tiktok_tags": ["tag1", "tag2", "tag3"],
            "slides": [
                {{"type": "judul", "teks": "Judul singkat di gambar", "keyword_gambar": "keyword pexels"}},
                {{"type": "konten", "teks": "Isi slide 1", "keyword_gambar": "keyword pexels"}}
            ]
        }}

        Aturan output umum:
        - keyword_gambar harus Bahasa Inggris, maksimal 2 kata
        - slide array: Total item {num_slides + 1} (1 judul, {num_slides} konten)
        """

        if INI_POINTS_ONLY_TEXT:
            prompt = base_rules + f"""
            Aturan khusus teks slide:
            - Isi teks slide harus berupa POINT SINGKAT saja, bukan paragraf.
            - Setiap slide konten hanya boleh berisi 1 poin utama.
            - Maksimal {INI_MAX_WORDS_PER_SLIDE} kata per slide konten.
            - Gunakan bahasa Indonesia yang singkat, tajam, dan enak dibaca di gambar.
            - Hindari tanda baca berlebihan.
            """
        else:
            prompt = base_rules + f"""
            Aturan khusus teks slide:
            - Teks konten harus memuat fakta/data terbaru.
            - Boleh memakai kalimat yang agak panjang, tapi tetap padat dan jelas.
            """

        print(f"🧠 Meminta Gemini riset & membuat konten + metadata untuk topik: '{topic}'...")
        return self._generate_json_with_retry(client, prompt)

    # ==========================================
    # MODUL 2: IMAGE SOURCING (PEXELS)
    # ==========================================
    def get_pexels_image(self, query):
        if not self.pexels_key:
            raise ValueError("PEXELS_API_KEY tidak ditemukan.")

        print(f"🔍 Mencari gambar di Pexels untuk keyword: '{query}'")
        headers = {"Authorization": self.pexels_key, "User-Agent": "Mozilla/5.0"}
        params = urllib.parse.urlencode({
            "query": query,
            "orientation": "portrait",
            "size": "large",
            "per_page": 30,
        })
        search_url = f"https://api.pexels.com/v1/search?{params}"
        req = urllib.request.Request(search_url, headers=headers)

        try:
            with urllib.request.urlopen(req) as response:
                data = json.load(response)
        except Exception as e:
            print(f"   ⚠️ Error API Pexels saat mencari '{query}': {e}")
            return Image.new("RGB", (INI_CANVAS_WIDTH, INI_CANVAS_HEIGHT), color=(30, 30, 30))

        if not data.get("photos"):
            print(f"   ⚠️ Pexels tidak menemukan gambar untuk '{query}'.")
            return Image.new("RGB", (INI_CANVAS_WIDTH, INI_CANVAS_HEIGHT), color=(30, 30, 30))

        available_photos = [p for p in data["photos"] if p["id"] not in self.used_pexels_ids]
        if not available_photos:
            print(f"   🔄 Pool gambar untuk '{query}' habis, me-reset history.")
            available_photos = data["photos"]
            self.used_pexels_ids.clear()

        photo_data = random.choice(available_photos)
        self.used_pexels_ids.add(photo_data["id"])

        img_url = photo_data["src"]["original"]
        download_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})

        try:
            with urllib.request.urlopen(download_req) as response:
                img_data = response.read()
            return Image.open(BytesIO(img_data))
        except Exception as e:
            print(f"   ⚠️ Error saat download gambar '{query}': {e}")
            return Image.new("RGB", (INI_CANVAS_WIDTH, INI_CANVAS_HEIGHT), color=(30, 30, 30))

    # ==========================================
    # MODUL 3: IMAGE PROCESSING (PILLOW)
    # ==========================================
    def _load_font(self, font_size):
        try:
            return ImageFont.truetype(self.font_path, font_size)
        except IOError:
            return ImageFont.load_default()

    def _wrap_text_by_pixel_width(self, draw, text, font, max_width):
        words = text.split()
        if not words:
            return ""

        lines = []
        current_line = words[0]

        for word in words[1:]:
            candidate = f"{current_line} {word}"
            bbox = draw.textbbox((0, 0), candidate, font=font)
            candidate_width = bbox[2] - bbox[0]

            if candidate_width <= max_width:
                current_line = candidate
            else:
                lines.append(current_line)
                current_line = word

        lines.append(current_line)
        return "\n".join(lines)

    def _calculate_text_layout(self, draw, text, font_size, style):
        font = self._load_font(font_size)

        if style == "box":
            max_text_width = INI_CANVAS_WIDTH - (INI_TEXT_SIDE_MARGIN * 2) - (INI_BOX_PADDING_X * 2)
        else:
            max_text_width = INI_CANVAS_WIDTH - (INI_TEXT_SIDE_MARGIN * 2)

        wrapped_text = self._wrap_text_by_pixel_width(draw, text, font, max_text_width)

        bbox = draw.multiline_textbbox(
            (0, 0),
            wrapped_text,
            font=font,
            align="center",
            spacing=INI_TEXT_LINE_SPACING
        )

        t_width = bbox[2] - bbox[0]
        t_height = bbox[3] - bbox[1]

        if style == "box":
            final_height = t_height + (INI_BOX_PADDING_Y * 2)
        else:
            final_height = t_height

        return {
            "font": font,
            "wrapped_text": wrapped_text,
            "text_width": t_width,
            "text_height": t_height,
            "block_height": final_height,
        }

    def _get_best_fitting_layout(self, draw, text, initial_font_size, style):
        layout = self._calculate_text_layout(draw, text, initial_font_size, style)

        if not INI_AUTO_SHRINK_TEXT:
            return initial_font_size, layout

        max_allowed_height = INI_CANVAS_HEIGHT - (INI_SAFE_TOP_BOTTOM_MARGIN * 2)

        current_size = initial_font_size
        best_layout = layout

        while current_size > INI_AUTO_SHRINK_MIN_FONT_SIZE and best_layout["block_height"] > max_allowed_height:
            current_size -= INI_AUTO_SHRINK_STEP
            best_layout = self._calculate_text_layout(draw, text, current_size, style)

        return current_size, best_layout

    def process_slide_image(self, img, text, font_size, style):
        target_size = (INI_CANVAS_WIDTH, INI_CANVAS_HEIGHT)
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]

        if img_ratio > target_ratio:
            new_width = int(target_size[1] * img_ratio)
            img = img.resize((new_width, target_size[1]), Image.Resampling.LANCZOS)
        else:
            new_height = int(target_size[0] / img_ratio)
            img = img.resize((target_size[0], new_height), Image.Resampling.LANCZOS)

        left = (img.width - target_size[0]) / 2
        top = (img.height - target_size[1]) / 2
        img = img.crop((left, top, left + target_size[0], top + target_size[1]))

        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)

        final_font_size, layout = self._get_best_fitting_layout(draw, text, font_size, style)
        font = layout["font"]
        wrapped_text = layout["wrapped_text"]
        t_width = layout["text_width"]
        t_height = layout["text_height"]

        x_pos = (img.width - t_width) / 2
        y_pos = ((img.height - t_height) / 2) + INI_TEXT_VERTICAL_OFFSET

        if style == "outline":
            stroke_width = max(2, int(final_font_size * INI_OUTLINE_STROKE_RATIO))
            draw.multiline_text(
                (x_pos, y_pos),
                wrapped_text,
                font=font,
                fill=INI_OUTLINE_TEXT_FILL,
                align="center",
                spacing=INI_TEXT_LINE_SPACING,
                stroke_width=stroke_width,
                stroke_fill=INI_OUTLINE_STROKE_FILL
            )

        elif style == "box":
            box_left = x_pos - INI_BOX_PADDING_X
            box_top = y_pos - INI_BOX_PADDING_Y
            box_right = x_pos + t_width + INI_BOX_PADDING_X
            box_bottom = y_pos + t_height + INI_BOX_PADDING_Y

            draw.rounded_rectangle(
                [box_left, box_top, box_right, box_bottom],
                radius=INI_BOX_RADIUS,
                fill=INI_BOX_FILL
            )

            draw.multiline_text(
                (x_pos, y_pos),
                wrapped_text,
                font=font,
                fill=INI_BOX_TEXT_FILL,
                align="center",
                spacing=INI_TEXT_LINE_SPACING
            )

        return img.convert("RGB")

    # ==========================================
    # PIPELINE EXECUTION
    # ==========================================
    def run(self, topic, num_slides, style):
        self._download_font_if_missing()
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        try:
            # 1. Dapatkan JSON yang sekarang berisi Metadata + Slides
            full_data = self.generate_carousel_content(topic, num_slides)

            # 2. Ekstraksi data
            tiktok_title = full_data.get("tiktok_title", "Tanpa Judul")
            tiktok_desc = full_data.get("tiktok_description", "")
            tiktok_tags = full_data.get("tiktok_tags", [])
            slides = full_data.get("slides", [])

            # 3. Print Metadata ke Console
            print("\n" + "="*50)
            print("📱 METADATA TIKTOK POST")
            print("="*50)
            print(f"📍 Judul     : {tiktok_title}")
            print(f"📍 Deskripsi : {tiktok_desc}")
            
            # Format hashtag agar ada tanda '#' nya jika AI lupa
            formatted_tags = " ".join([f"#{t.replace('#', '')}" for t in tiktok_tags])
            print(f"📍 Tags      : {formatted_tags}")
            print("="*50 + "\n")

            # 4. Simpan Metadata ke file metadata.json
            metadata_filepath = os.path.join(self.output_dir, "metadata.json")
            with open(metadata_filepath, "w", encoding="utf-8") as f:
                json.dump(full_data, f, ensure_ascii=False, indent=4)
            print(f"💾 Metadata berhasil disimpan di: {metadata_filepath}")

            # 5. Simpan isi konten ke context.txt untuk memori generasi berikutnya
            if slides:
                self._append_context(topic, slides)
                print(f"📝 Sejarah konten (Context) berhasil di-update di: {INI_CONTEXT_FILE}")
            else:
                print("⚠️ Peringatan: Data 'slides' kosong dari AI.")

            # 6. Proses Render Gambar Slide
            for i, slide in enumerate(slides):
                print(f"\n▶️ Memproses Slide {i} ({slide.get('type', 'unknown')})")

                font_size = INI_TITLE_FONT_SIZE if slide.get("type") == "judul" else INI_CONTENT_FONT_SIZE

                raw_img = self.get_pexels_image(slide.get("keyword_gambar", "background"))
                final_img = self.process_slide_image(raw_img, slide.get("teks", ""), font_size, style)

                filename = os.path.join(self.output_dir, f"slide_{i:02d}.jpg")
                final_img.save(filename, quality=INI_JPG_QUALITY)
                print(f"✅ Berhasil disimpan: {filename}")

            print(f"\n🎉 SELESAI! Semua file gambar dan metadata telah disimpan di folder '{self.output_dir}'.")

        except Exception as e:
            print(f"\n❌ Terjadi kesalahan saat eksekusi: {e}")