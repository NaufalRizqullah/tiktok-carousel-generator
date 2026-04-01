# =========================================================
# KONFIGURASI GLOBAL
# Semua yang sering di-custom ditaruh di sini
# =========================================================

# File untuk menyimpan memori/konteks agar tidak mengulang poin di Part selanjutnya
CONTEXT_FILE = "context.txt"

# Pengaturan Font (Family dan Numeral Weight 100-900)
# Weight: 100=Thin, 200=ExtraLight, 300=Light, 400=Regular
#         500=Medium, 600=SemiBold, 700=Bold, 800=ExtraBold, 900=Black
TITLE_FONT_FAMILY = "LeagueSpartan"
TITLE_FONT_WEIGHT = 700

CONTENT_FONT_FAMILY = "Poppins"
CONTENT_FONT_WEIGHT = 400

# Preset output agar layout bisa responsif terhadap format gambar.
# "portrait" = 9:16 (default), "square" = 1:1.
OUTPUT_FORMAT = "portrait"

_BASE_LAYOUT_DEFAULTS = {
    # Ukuran canvas output
    "CANVAS_WIDTH": 1080,
    "CANVAS_HEIGHT": 1920,

    # Ukuran font default
    "TITLE_FONT_SIZE": 65,
    "CONTENT_FONT_SIZE": 50,

    # Auto shrink font
    "AUTO_SHRINK_TEXT": False,
    "AUTO_SHRINK_MIN_FONT_SIZE": 45,
    "AUTO_SHRINK_STEP": 2,

    # Area aman atas/bawah agar box tidak terlalu mentok ke tepi
    "SAFE_TOP_BOTTOM_MARGIN": 140,

    # Jarak teks dari tepi kiri/kanan gambar
    "TEXT_SIDE_MARGIN": 60,

    # Jarak dalam box putih (Inner R)
    "BOX_INNER_PADDING": 16,
    "BOX_RADIUS_EXTRA": 18,

    # Spasi antar baris
    "TEXT_LINE_SPACING": 10,

    # Bonus ukuran font title pada style box-title-content
    "TITLE_BOX_FONT_BONUS": 5,

    # Jarak antar elemen khusus style box-title-content
    "TITLE_CONTENT_SPACING": 60,
    "PARAGRAPH_SPACING": 25,

    # Geser posisi teks secara vertikal (0 = pas tengah)
    "TEXT_VERTICAL_OFFSET": 0,

    # Gemini point text image
    "POINTS_ONLY_TEXT": True,
    "MAX_WORDS_PER_SLIDE": 25,
}

OUTPUT_PRESETS = {
    "portrait": {},
    "square": {
        "CANVAS_WIDTH": 1080,
        "CANVAS_HEIGHT": 1080,
        "TITLE_FONT_SIZE": 58,
        "CONTENT_FONT_SIZE": 42,
        "AUTO_SHRINK_TEXT": True,
        "AUTO_SHRINK_MIN_FONT_SIZE": 30,
        "SAFE_TOP_BOTTOM_MARGIN": 70,
        "TEXT_SIDE_MARGIN": 42,
        "BOX_INNER_PADDING": 14,
        "BOX_RADIUS_EXTRA": 14,
        "TEXT_LINE_SPACING": 8,
        "TITLE_CONTENT_SPACING": 34,
        "PARAGRAPH_SPACING": 16,
        "MAX_WORDS_PER_SLIDE": 16,
    },
}


def apply_output_preset(preset_name: str = "portrait") -> None:
    """Terapkan preset canvas + layout supaya renderer responsif per format."""
    global OUTPUT_FORMAT

    if preset_name not in OUTPUT_PRESETS:
        raise ValueError(f"Preset output tidak dikenal: {preset_name}")

    merged = dict(_BASE_LAYOUT_DEFAULTS)
    merged.update(OUTPUT_PRESETS[preset_name])

    OUTPUT_FORMAT = preset_name
    for key, value in merged.items():
        globals()[key] = value

    # Nilai turunan yang dipakai renderer
    globals()["BOX_PADDING_X"] = merged["BOX_INNER_PADDING"]
    globals()["BOX_PADDING_Y"] = merged["BOX_INNER_PADDING"]
    globals()["BOX_RADIUS"] = merged["BOX_INNER_PADDING"] + merged["BOX_RADIUS_EXTRA"]


# Terapkan preset default saat module di-import.
apply_output_preset(OUTPUT_FORMAT)

# Warna style box
BOX_FILL = (255, 255, 255, 235)   # putih
BOX_TEXT_FILL = (0, 0, 0)         # hitam

# Warna style outline
OUTLINE_TEXT_FILL = "white"
OUTLINE_STROKE_FILL = "black"
OUTLINE_STROKE_RATIO = 0.08

# Kualitas JPG output
JPG_QUALITY = 95
