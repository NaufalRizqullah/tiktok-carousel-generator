import os
import re
import requests


def download_font_if_missing(font_path: str) -> None:
    """Mengecek dan mendownload font default jika belum ada di lokal."""
    if not os.path.exists(font_path):
        print(f"📥 Font '{font_path}' tidak ditemukan. Mengunduh font default (Montserrat-Black)...")
        url = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Black.ttf"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            with open(font_path, "wb") as f:
                f.write(response.content)
            print("✅ Font berhasil diunduh dan siap digunakan!")
        except Exception as e:
            print(f"⚠️ Gagal mengunduh font: {e}")
            print("⚠️ Akan menggunakan font default sistem (tampilan mungkin kurang maksimal).")


def read_context(filepath: str) -> str:
    """Membaca file context history jika ada."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def append_context(filepath: str, topic: str, slides: list) -> None:
    """Menyimpan poin-poin yang baru di-generate ke file context."""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n[TOPIK: {topic}]\n")
        for slide in slides:
            if slide.get("type") == "konten":
                teks = slide.get("teks", "").replace("\n", " ")
                f.write(f"- {teks}\n")


def sanitize_text(text: str) -> str:
    """Bersihkan emoji atau simbol non-BMP agar tidak menjadi kotak saat di-render."""
    return re.sub(r'[^\u0000-\uFFFF]', '', text)
