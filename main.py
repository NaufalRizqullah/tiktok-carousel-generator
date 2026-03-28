import os
import argparse
import json
import textwrap
import requests
import re
import time
import urllib.parse
import urllib.request
import shutil
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables dari file .env jika ada
load_dotenv()

# Konfigurasi API Keys (Bisa dari .env atau default kosong/opsional jika di-handle di env host)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ==========================================
# MODUL 1: AI CONTENT GENERATOR (GEMINI)
# ==========================================
# Ganti implementasi sederhana dengan retry logic untuk menangani sibnut / transient errors
MODEL = "gemini-3-flash-preview"

MAX_ATTEMPTS = 10
INITIAL_WAIT_SECONDS = 60
WAIT_INCREMENT_SECONDS = 30
REQUEST_TIMEOUT_MS = 15 * 60 * 1000  # 15 menit
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def extract_status_code(exc: Exception):
    for attr in ("status_code", "code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    match = re.search(r"\b(408|429|500|502|503|504)\b", str(exc))
    return int(match.group(1)) if match else None


def is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, json.JSONDecodeError):
        return True
    status_code = extract_status_code(exc)
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    msg = str(exc).lower()
    transient_keywords = (
        "timeout",
        "temporarily unavailable",
        "deadline",
        "connection reset",
        "connection aborted",
        "service unavailable",
    )
    return any(k in msg for k in transient_keywords)


def generate_json_with_retry(client, model, prompt_text):
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(f"[Gemini] Attempt {attempt}/{MAX_ATTEMPTS}...")
            response = client.models.generate_content(
                model=model,
                contents=prompt_text,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )

            text = getattr(response, "text", None)
            if not text or not text.strip():
                # some SDK returns nested structure; try to coerce to string
                text = str(response)
            return json.loads(text.strip().removeprefix('```json').removesuffix('```').strip())

        except Exception as exc:
            last_exc = exc
            status_code = extract_status_code(exc)
            retryable = is_retryable_exception(exc)

            print(f"[Gemini] Attempt {attempt}/{MAX_ATTEMPTS} gagal | status={status_code} | error={exc}")

            if (not retryable) or attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Gagal memanggil Gemini setelah {attempt} percobaan. status={status_code}, error={exc}"
                ) from exc

            wait_seconds = INITIAL_WAIT_SECONDS + ((attempt - 1) * WAIT_INCREMENT_SECONDS)
            print(f"[Gemini] Retry lagi dalam {wait_seconds} detik...")
            time.sleep(wait_seconds)

    raise RuntimeError(f"Gagal memanggil Gemini. Error terakhir: {last_exc}") from last_exc


def generate_carousel_content(topic, num_slides):
    """Menghasilkan struktur teks dan keyword gambar menggunakan Gemini dengan retry jika sibnut"""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY tidak ditemukan. Set di .env atau environment variable.")

    client = genai.Client(
        api_key=GOOGLE_API_KEY,
        http_options=types.HttpOptions(
            timeout=REQUEST_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    prompt = f"""
    Kamu adalah pembuat konten TikTok profesional. Buat konten karosel (slideshow) tentang topik: "{topic}".
    Total ada {num_slides + 1} slide (1 slide judul + {num_slides} slide konten).

    Teks harus singkat, menarik (hook kuat), dan mudah dibaca.
    Berikan 'keyword_gambar' dalam Bahasa Inggris (maksimal 2 kata) yang sangat relevan dengan teks tersebut untuk dicari di Pexels (misal: "neon city", "laptop dark", "confused person").

    Keluarkan HANYA format JSON valid dengan struktur array of object seperti ini tanpa format markdown (```json):
    [
      {{"type": "judul", "teks": "Judul Menarik Di Sini", "keyword_gambar": "keyword pexels"}},
      {{"type": "konten", "teks": "Poin 1 yang sangat berguna...", "keyword_gambar": "keyword pexels"}}
    ]
    """

    print(f"🧠 Meminta Gemini membuat konten untuk topik: '{topic}'...")
    return generate_json_with_retry(client=client, model=MODEL, prompt_text=prompt)

# ==========================================
# MODUL 2: IMAGE SOURCING (PEXELS)
# ==========================================
# ==========================================
# MODUL 2: IMAGE SOURCING (PEXELS)
# ==========================================
# 🌟 VARIABEL GLOBAL: Untuk mengingat ID gambar yang sudah terpakai
USED_PEXELS_IDS = set()

def get_pexels_image(query):
    """Mendapatkan gambar vertikal dari Pexels dengan anti-duplikat"""
    global USED_PEXELS_IDS
    
    if not PEXELS_API_KEY:
        raise ValueError("PEXELS_API_KEY tidak ditemukan.")
    
    print(f"🔍 Mencari gambar di Pexels untuk keyword: '{query}'")
    
    headers = {"Authorization": PEXELS_API_KEY, "User-Agent": "Mozilla/5.0"}
    
    params = urllib.parse.urlencode({
        "query": query,
        "orientation": "portrait",
        "size": "large",
        "per_page": 30,  # 🌟 Ambil 30 gambar sekaligus sebagai kolam pilihan
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
    
    # 🌟 LOGIKA BARU: Filter gambar yang belum pernah dipakai sebelumnya
    available_photos = [p for p in data['photos'] if p['id'] not in USED_PEXELS_IDS]
    
    # Jika kebetulan semua gambar sudah dipakai, fallback pakai semua
    if not available_photos:
        print(f"   🔄 Pool gambar untuk '{query}' habis, me-reset history.")
        available_photos = data['photos']
        USED_PEXELS_IDS.clear()
    
    # 🌟 LOGIKA BARU: Pilih secara acak dari kolam yang tersedia
    photo_data = random.choice(available_photos)
    
    # Catat ID gambar ini agar tidak terpakai lagi
    USED_PEXELS_IDS.add(photo_data['id'])
    
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
def process_slide_image(img, text, font_path, font_size, style):
    """Crop gambar ke 9:16 dan tambahkan teks"""
    # 1. Resize & Crop
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

    # 2. Add Text
    img = img.convert('RGBA')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
        print("⚠️ Font tidak ditemukan, menggunakan font default sistem.")

    wrapped_text = textwrap.fill(text, width=22)
    bbox = draw.textbbox((0, 0), wrapped_text, font=font, align="center")
    t_width = bbox[2] - bbox[0]
    t_height = bbox[3] - bbox[1]
    
    x_pos = (img.width - t_width) / 2
    y_pos = (img.height - t_height) / 2

    if style == "outline":
        stroke_width = int(font_size * 0.08)
        draw.multiline_text((x_pos, y_pos), wrapped_text, font=font, fill="white", align="center",
                            stroke_width=stroke_width, stroke_fill="black")
    elif style == "box":
        pad = 40
        draw.rectangle([x_pos-pad, y_pos-pad, x_pos+t_width+pad, y_pos+t_height+pad], fill=(0,0,0,160), radius=20)
        draw.multiline_text((x_pos, y_pos), wrapped_text, font=font, fill="white", align="center")

    return img.convert('RGB')

# ==========================================
# FUNGSI UTAMA & ARGPARSE
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="TikTok Carousel Image Generator")
    
    # Argumen yang bisa di-passing melalui command line
    parser.add_argument("-t", "--topic", type=str, required=True, help="Topik pembahasan untuk di-generate AI")
    parser.add_argument("-s", "--slides", type=int, default=5, help="Jumlah slide konten (default: 5)")
    parser.add_argument("--style", type=str, choices=['outline', 'box'], default="outline", help="Gaya teks (outline/box)")
    parser.add_argument("--font", type=str, default="font.ttf", help="Path ke file font (default: font.ttf)")
    parser.add_argument("-o", "--output", type=str, default="output", help="Nama folder output (default: output)")

    args = parser.parse_args()

    # Siapkan folder output
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    try:
        # 1. Minta Gemini buat naskah
        slide_data = generate_carousel_content(args.topic, args.slides)
        
        # 2. Proses setiap slide
        for i, slide in enumerate(slide_data):
            print(f"\n▶️ Memproses Slide {i} ({slide['type']})")
            
            # Tentukan ukuran font (Judul lebih besar)
            font_size = 90 if slide['type'] == 'judul' else 75
            
            # Ambil gambar & tempel teks
            raw_img = get_pexels_image(slide['keyword_gambar'])
            final_img = process_slide_image(raw_img, slide['teks'], args.font, font_size, args.style)
            
            # Simpan file
            filename = os.path.join(args.output, f"slide_{i:02d}.jpg")
            final_img.save(filename, quality=95)
            print(f"✅ Berhasil disimpan: {filename}")
            
        print(f"\n🎉 SELESAI! Semua gambar telah disimpan di folder '{args.output}'.")

    except Exception as e:
        print(f"\n❌ Terjadi kesalahan: {e}")

if __name__ == "__main__":
    main()