import os
import re
import requests


def get_font_path(family: str, weight: int) -> str:
    """Mengembalikan path font berdasarkan family dan numerik weight (100-900).
    Jika weight tidak ada, akan fallback ke Regular atau font pertama yang ada di folder.
    """
    weight_map = {
        100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
        500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"
    }
    weight_name = weight_map.get(weight, "Regular")
    
    base_dir = os.path.join("fonts", family)
    ideal_path = os.path.join(base_dir, f"{family}-{weight_name}.ttf")
    
    if os.path.exists(ideal_path):
        return ideal_path
        
    regular_path = os.path.join(base_dir, f"{family}-Regular.ttf")
    if os.path.exists(regular_path):
        return regular_path
        
    # Fallback to any .ttf file in the folder
    if os.path.exists(base_dir):
        for file in os.listdir(base_dir):
            if file.endswith(".ttf") or file.endswith(".otf"):
                return os.path.join(base_dir, file)
                
    return ideal_path


def download_font_if_missing(font_path: str, default_url: str = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Black.ttf") -> None:
    """Mengecek dan mendownload font default jika belum ada di lokal."""
    if not os.path.exists(font_path):
        print(f"📥 Font '{font_path}' tidak ditemukan. Mengunduh font default...")
        try:
            response = requests.get(default_url, timeout=15)
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
