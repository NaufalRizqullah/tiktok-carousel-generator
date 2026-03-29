# =========================================================
# KONFIGURASI GLOBAL
# Semua yang sering di-custom ditaruh di sini
# =========================================================

# File untuk menyimpan memori/konteks agar tidak mengulang poin di Part selanjutnya
CONTEXT_FILE = "context.txt"

# Ukuran canvas output
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# Ukuran font default
TITLE_FONT_SIZE = 80
CONTENT_FONT_SIZE = 65

# Auto shrink font
AUTO_SHRINK_TEXT = False
AUTO_SHRINK_MIN_FONT_SIZE = 45
AUTO_SHRINK_STEP = 2

# Area aman atas/bawah agar box tidak terlalu mentok ke tepi
SAFE_TOP_BOTTOM_MARGIN = 140

# Jarak teks dari tepi kiri/kanan gambar
TEXT_SIDE_MARGIN = 40

# Jarak dalam box putih
BOX_PADDING_X = 40
BOX_PADDING_Y = 40

# Radius sudut box
BOX_RADIUS = 20

# Warna style box
BOX_FILL = (255, 255, 255, 235)   # putih
BOX_TEXT_FILL = (0, 0, 0)         # hitam

# Warna style outline
OUTLINE_TEXT_FILL = "white"
OUTLINE_STROKE_FILL = "black"
OUTLINE_STROKE_RATIO = 0.08

# Spasi antar baris
TEXT_LINE_SPACING = 10

# Geser posisi teks secara vertikal (0 = pas tengah)
TEXT_VERTICAL_OFFSET = 0

# Kualitas JPG output
JPG_QUALITY = 95

# Gemini Point text image
POINTS_ONLY_TEXT = True
MAX_WORDS_PER_SLIDE = 25
