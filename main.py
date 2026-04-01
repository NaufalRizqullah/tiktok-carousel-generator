import os
import argparse
from dotenv import load_dotenv

# Import Class dari package tiktok_carousel
from tiktok_carousel import TikTokCarouselGenerator

def main():
    # Load environment variables dari file .env jika ada
    load_dotenv()

    # Parsing argumen CLI
    parser = argparse.ArgumentParser(description="TikTok Carousel Image Generator")
    parser.add_argument("-t", "--topic", type=str, required=True, help="Topik pembahasan untuk di-generate AI")
    parser.add_argument("-s", "--slides", type=int, default=5, help="Jumlah slide konten (default: 5)")
    parser.add_argument("--style", type=str, choices=['outline', 'box', 'box-title-content'], default="outline", help="Gaya teks (outline/box/box-title-content)")
    parser.add_argument("--format", type=str, choices=['portrait', 'square'], default="portrait", help="Format output gambar (portrait=9:16, square=1:1)")
    parser.add_argument("--title-family", type=str, default=None, help="Family font judul (contoh: LeagueSpartan)")
    parser.add_argument("--title-weight", type=int, default=None, help="Weight font judul (100-900, default di config)")
    parser.add_argument("--content-family", type=str, default=None, help="Family font konten (contoh: Poppins)")
    parser.add_argument("--content-weight", type=int, default=None, help="Weight font konten (100-900, default di config)")
    parser.add_argument("-o", "--output", type=str, default="output", help="Nama folder output (default: output)")

    args = parser.parse_args()

    # Ambil API Key (Prioritas dari System Environment, lalu file .env)
    pexels_api_key = os.getenv("PEXELS_API_KEY", "")
    google_api_key = os.getenv("GOOGLE_API_KEY", "")

    # Inisialisasi Generator
    app = TikTokCarouselGenerator(
        pexels_key=pexels_api_key,
        gemini_key=google_api_key,
        title_font_family=args.title_family,
        title_font_weight=args.title_weight,
        content_font_family=args.content_family,
        content_font_weight=args.content_weight,
        output_dir=args.output,
        output_format=args.format,
    )

    # Jalankan proses
    app.run(
        topic=args.topic, 
        num_slides=args.slides, 
        style=args.style
    )

if __name__ == "__main__":
    main()