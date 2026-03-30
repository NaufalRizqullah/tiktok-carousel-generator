import json
import re
import time

from google import genai
from google.genai import types

from . import config


class ContentGenerator:
    """Modul AI Content Generator menggunakan Google Gemini."""

    def __init__(self, api_key: str):
        self.api_key = api_key

        # Gemini Config
        self.MODEL = "gemini-2.5-flash"
        self.MAX_ATTEMPTS = 10
        self.INITIAL_WAIT_SECONDS = 60
        self.WAIT_INCREMENT_SECONDS = 30
        self.REQUEST_TIMEOUT_MS = 15 * 60 * 1000
        self.RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

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

    def generate(self, topic: str, num_slides: int, style: str = "outline", previous_context: str = "") -> dict:
        """Generate konten carousel dari Gemini AI berdasarkan topik."""
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY tidak ditemukan. Set di .env atau parameter.")

        client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                timeout=self.REQUEST_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

        # Cek apakah ada context dari part sebelumnya
        context_instruction = ""
        if previous_context:
            print(f"📚 Ditemukan {config.CONTEXT_FILE}! Mengingatkan AI agar tidak mengulang poin lama...")
            context_instruction = f"""
            PENTING (CONTEXT HISTORY):
            Berikut adalah poin-poin yang SUDAH DIBAHAS pada part/generasi sebelumnya.
            Kamu DILARANG KERAS mengulangi poin, fakta, atau ide yang ada di bawah ini.
            Berikan poin/fakta yang sepenuhnya BARU untuk topik ini.
            
            <context_history>
            {previous_context}
            </context_history>
            """

        if style == "box-title-content":
            format_wajib = f"""
        Format wajib:
        {{
            "tiktok_title": "Judul Postingan Catchy",
            "tiktok_description": "Deskripsi/caption singkat dan menarik.",
            "tiktok_tags": ["tag1", "tag2", "tag3"],
            "slides": [
                {{"type": "judul", "teks": "Judul cover TikTok", "keyword_gambar": "keyword pexels"}},
                {{"type": "konten", "slide_title": "1. JUDUL PENDEK", "teks": "Fakta penting yang perlu kamu ketahui adalah...\\n\\nHal ini terjadi karena...\\n\\nOleh karena itu, cara mengatasinya adalah...", "keyword_gambar": "keyword pexels"}}
            ]
        }}
        
        Aturan khusus teks (PENTING):
        - WAJIB tambahkan field "slide_title" yang SUPER SINGKAT dan HURUF KAPITAL (UPPERCASE) pada slide konten.
        - KONSISTENSI PENOMORAN: Evaluasi apakah judul slide lebih baik menggunakan angka (1., 2., dst). Jika IYA, berikan angka pada SEMUA `slide_title` konten. Jika TIDAK, hapus angka dari SEMUA `slide_title`. Jangan campur aduk.
        - Teks "teks" HARUS informatif, edukatif, dan memuat fakta/informasi yang jelas secara natural, TAPI TETAP ASIK DIBACA.
        - Pisahkan kalimat demi kalimat dalam field "teks" dengan dua kali enter (\\n\\n) langsung di JSON sebagai pemisah alinea/paragraf.
            """
        else:
            format_wajib = f"""
        Format wajib:
        {{
            "tiktok_title": "Judul Postingan Catchy",
            "tiktok_description": "Deskripsi/caption singkat dan menarik.",
            "tiktok_tags": ["tag1", "tag2", "tag3"],
            "slides": [
                {{"type": "judul", "teks": "Judul singkat", "keyword_gambar": "keyword pexels"}},
                {{"type": "konten", "teks": "Isi slide 1", "keyword_gambar": "keyword pexels"}}
            ]
        }}
            """
            if config.POINTS_ONLY_TEXT:
                format_wajib += f"""
        Aturan khusus teks slide:
        - Isi teks slide harus POINT SINGKAT saja.
        - Setiap konten hanya boleh berisi 1 poin utama.
        - Maksimal {config.MAX_WORDS_PER_SLIDE} kata per slide.
        - Gunakan bahasa Indonesia singkat, tajam, dan enak dibaca.
                """
            else:
                format_wajib += """
        Aturan khusus teks:
        - Teks harus memuat fakta/data, jelas, dan padat.
                """

        base_rules = f"""
        Kamu adalah pembuat konten TikTok profesional.

        Tugas:
        1. Gunakan Google Search untuk riset {topic}.
        2. Kembalikan JSON (OBJECT) tanpa markdown ```json.
        3. Buatkan judul, deskripsi, hashtag.

        {context_instruction}

        {format_wajib}

        Aturan output umum:
        - keyword_gambar harus Bahasa Inggris
        - total slide = {num_slides + 1}
        - JANGAN PERNAH memberikan emoji di dalam "teks", "slide_title", "judul" agar gambar tidak error kotak-kotak. Kamu sangat disarankan menggunakan banyak emoji memikat pada "tiktok_title" dan "tiktok_description".
        """

        print(f"🧠 Meminta Gemini riset & membuat konten + metadata untuk topik: '{topic}'...")
        return self._generate_json_with_retry(client, base_rules)
