import json
import random
import urllib.parse
import urllib.request
from io import BytesIO

from PIL import Image

from . import config


class PexelsImageSource:
    """Modul untuk mencari dan mengunduh gambar dari Pexels API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.used_ids = set()

    def get_image(self, query: str) -> Image.Image:
        """Cari dan download gambar portrait dari Pexels berdasarkan keyword."""
        if not self.api_key:
            raise ValueError("PEXELS_API_KEY tidak ditemukan.")

        print(f"🔍 Mencari gambar di Pexels untuk keyword: '{query}'")
        headers = {"Authorization": self.api_key, "User-Agent": "Mozilla/5.0"}
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
            return Image.new("RGB", (config.CANVAS_WIDTH, config.CANVAS_HEIGHT), color=(30, 30, 30))

        if not data.get("photos"):
            print(f"   ⚠️ Pexels tidak menemukan gambar untuk '{query}'.")
            return Image.new("RGB", (config.CANVAS_WIDTH, config.CANVAS_HEIGHT), color=(30, 30, 30))

        available_photos = [p for p in data["photos"] if p["id"] not in self.used_ids]
        if not available_photos:
            print(f"   🔄 Pool gambar untuk '{query}' habis, me-reset history.")
            available_photos = data["photos"]
            self.used_ids.clear()

        photo_data = random.choice(available_photos)
        self.used_ids.add(photo_data["id"])

        img_url = photo_data["src"]["original"]
        download_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})

        try:
            with urllib.request.urlopen(download_req) as response:
                img_data = response.read()
            return Image.open(BytesIO(img_data))
        except Exception as e:
            print(f"   ⚠️ Error saat download gambar '{query}': {e}")
            return Image.new("RGB", (config.CANVAS_WIDTH, config.CANVAS_HEIGHT), color=(30, 30, 30))
