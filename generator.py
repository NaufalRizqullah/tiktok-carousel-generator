import os
import json
import textwrap
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

class TikTokCarouselGenerator:
    def __init__(self, pexels_key, gemini_key, font_path="font.ttf", output_dir="output"):
        self.pexels_key = pexels_key
        self.gemini_key = gemini_key
        self.font_path = font_path
        self.output_dir = output_dir
        
        # State
        self.used_pexels_ids = set()
        
        # Gemini Config
        # self.MODEL = "gemini-3-flash-preview"
        self.MODEL = "gemini-2.5-flash"
        self.MAX_ATTEMPTS = 10
        self.INITIAL_WAIT_SECONDS = 60
        self.WAIT_INCREMENT_SECONDS = 30
        self.REQUEST_TIMEOUT_MS = 15 * 60 * 1000
        self.RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

    # ==========================================
    # UTILITY: DOWNLOAD FONT
    # ==========================================
    def _download_font_if_missing(self):
        """Mengecek dan mendownload font default jika belum ada di lokal"""
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
        transient_keywords = ("timeout", "temporarily unavailable", "deadline", "connection reset", "connection aborted", "service unavailable")
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

        prompt = f"""
        Kamu adalah pembuat konten TikTok profesional.

        Tugas:
        1. Gunakan Google Search untuk mencari fakta/data/tren terbaru tentang "{topic}".
        2. Kembalikan HANYA JSON valid.
        3. Jangan gunakan markdown, jangan pakai ```json, jangan beri penjelasan tambahan.

        Format wajib:
        [
        {{"type": "judul", "teks": "Judul Menarik Di Sini", "keyword_gambar": "keyword pexels"}},
        {{"type": "konten", "teks": "Fakta terbaru poin 1...", "keyword_gambar": "keyword pexels"}}
        ]

        Total item: {num_slides + 1}
        - 1 item type="judul"
        - {num_slides} item type="konten"
        - keyword_gambar harus Bahasa Inggris, maksimal 2 kata
        """
        print(f"🧠 Meminta Gemini riset & membuat konten untuk topik: '{topic}'...")
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
            "query": query, "orientation": "portrait", "size": "large", "per_page": 30,
        })
        search_url = f"https://api.pexels.com/v1/search?{params}"
        req = urllib.request.Request(search_url, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                data = json.load(response)
        except Exception as e:
            print(f"   ⚠️ Error API Pexels saat mencari '{query}': {e}")
            return Image.new('RGB', (1080, 1920), color=(30, 30, 30))
        
        if not data.get('photos'):
            print(f"   ⚠️ Pexels tidak menemukan gambar untuk '{query}'.")
            return Image.new('RGB', (1080, 1920), color=(30, 30, 30))
        
        available_photos = [p for p in data['photos'] if p['id'] not in self.used_pexels_ids]
        if not available_photos:
            print(f"   🔄 Pool gambar untuk '{query}' habis, me-reset history.")
            available_photos = data['photos']
            self.used_pexels_ids.clear()
        
        photo_data = random.choice(available_photos)
        self.used_pexels_ids.add(photo_data['id'])
        
        img_url = photo_data['src']['original']
        download_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        
        try:
            with urllib.request.urlopen(download_req) as response:
                img_data = response.read()
            return Image.open(BytesIO(img_data))
        except Exception as e:
            print(f"   ⚠️ Error saat download gambar '{query}': {e}")
            return Image.new('RGB', (1080, 1920), color=(30, 30, 30))

    # ==========================================
    # MODUL 3: IMAGE PROCESSING (PILLOW)
    # ==========================================
    def process_slide_image(self, img, text, font_size, style):
        target_size = (1080, 1920)
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

        img = img.convert('RGBA')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype(self.font_path, font_size)
        except IOError:
            font = ImageFont.load_default()

        wrapped_text = textwrap.fill(text, width=22)
        bbox = draw.textbbox((0, 0), wrapped_text, font=font, align="center")
        t_width = bbox[2] - bbox[0]
        t_height = bbox[3] - bbox[1]
        
        x_pos = (img.width - t_width) / 2
        y_pos = (img.height - t_height) / 2

        if style == "outline":
            stroke_width = int(font_size * 0.08)
            draw.multiline_text((x_pos, y_pos), wrapped_text, font=font, fill="white", align="center", stroke_width=stroke_width, stroke_fill="black")
        elif style == "box":
            pad = 40
            draw.rounded_rectangle(
                [x_pos-pad, y_pos-pad, x_pos+t_width+pad, y_pos+t_height+pad],
                radius=20,
                fill=(0, 0, 0, 160)
            )
            draw.multiline_text(
                (x_pos, y_pos),
                wrapped_text,
                font=font,
                fill="white",
                align="center"
            )

        return img.convert('RGB')

    # ==========================================
    # PIPELINE EXECUTION
    # ==========================================
    def run(self, topic, num_slides, style):
        # 0. Persiapan (Download font & Buat folder)
        self._download_font_if_missing()
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        try:
            # 1. Minta Gemini buat naskah
            slide_data = self.generate_carousel_content(topic, num_slides)
            
            # 2. Proses setiap slide
            for i, slide in enumerate(slide_data):
                print(f"\n▶️ Memproses Slide {i} ({slide['type']})")
                
                font_size = 90 if slide['type'] == 'judul' else 75
                
                raw_img = self.get_pexels_image(slide['keyword_gambar'])
                final_img = self.process_slide_image(raw_img, slide['teks'], font_size, style)
                
                filename = os.path.join(self.output_dir, f"slide_{i:02d}.jpg")
                final_img.save(filename, quality=95)
                print(f"✅ Berhasil disimpan: {filename}")
                
            print(f"\n🎉 SELESAI! Semua gambar telah disimpan di folder '{self.output_dir}'.")

        except Exception as e:
            print(f"\n❌ Terjadi kesalahan saat eksekusi: {e}")