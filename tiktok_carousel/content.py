import json
import re
import time

from google import genai
from google.genai import types

from . import config

class ContentGenerator:
    """Modul AI Content Generator menggunakan Google Gemini dengan Realtime Search."""

    def __init__(self, api_key: str):
        self.api_key = api_key

        # Gemini Config
        # Akses gratis (Free Tier) saat ini hanya difokuskan pada keluarga model "Flash"
        # yang dirancang untuk kecepatan dan efisiensi.
        self.MODEL = "gemini-2.5-flash"
        # self.MODEL = "gemini-3-flash-preview"
        # self.MODEL = "gemini-3.1-flash-lite-preview"
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

    def _extract_json_from_text(self, text: str) -> dict:
        """
        Fungsi sakti untuk mencari pola JSON (mulai dari { sampai }) 
        di dalam teks yang kotor (berisi basa-basi/markdown).
        """
        if not text:
            raise ValueError("Teks respons kosong.")

        # Cari substring yang dimulai dengan '{' dan diakhiri dengan '}'
        # re.DOTALL memungkinkan titik (.) untuk mencocokkan karakter newline (\n)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Ditemukan kurung kurawal, tapi isinya bukan JSON valid: {e}\nTeks: {json_str}")
        else:
            raise ValueError(f"Tidak dapat menemukan pola JSON (kurung kurawal) pada teks respons:\n{text}")

    def _generate_json_with_retry(self, client, prompt_text):
        last_exc = None
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                print(f"[Gemini] Attempt {attempt}/{self.MAX_ATTEMPTS}...")
                response = client.models.generate_content(
                    model=self.MODEL,
                    contents=prompt_text,
                    config=types.GenerateContentConfig(
                        # MENGGUNAKAN GOOGLE SEARCH
                        tools=[{"google_search": {}}],
                        # PERHATIAN: response_mime_type DIHAPUS agar tools bisa berjalan
                    ),
                )

                # Ekstrak teks dari respons
                raw_text = (response.text or "").strip()
                
                # Gunakan fungsi regex untuk membuang teks basa-basi dan mengambil JSON-nya
                parsed_json = self._extract_json_from_text(raw_text)
                return parsed_json

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
            print(f"📚 Ditemukan context! Mengingatkan AI agar tidak mengulang poin lama...")
            context_instruction = f"""
                PENTING (CONTEXT HISTORY):
                Berikut adalah poin-poin yang SUDAH DIBAHAS pada part/generasi sebelumnya.
                Kamu DILARANG KERAS mengulangi poin, fakta, ide, sudut bahas, atau insight yang ada di bawah ini.
                Berikan poin/fakta yang sepenuhnya BARU untuk topik ini.

                <context_history>
                {previous_context}
                </context_history>
            """

        style_voice_rules = """
            ATURAN KHUSUS GAYA BAHASA (WAJIB, PRIORITAS TINGGI):
            - Tulis isi slide seperti creator TikTok yang sedang ngajelasin sesuatu ke teman sendiri dengan cara santai, sederhana, dan enak diikutin.
            - Gunakan bahasa Indonesia yang natural, ringan, dan conversational.
            - Gunakan sudut pandang "aku" saat perlu, dan boleh menyapa audiens dengan "kamu" atau "kalian" secara natural.
            - Gaya bahasa harus EDUKATIF tapi tetap SANTAI, bukan formal, bukan kaku, dan bukan seperti artikel.
            - Tujuan utama: bikin audiens paham tanpa merasa sedang digurui.

            NUANSA BAHASA YANG DIINGINKAN:
            - Terasa seperti orang yang paham topik, lalu menjelaskan dengan simpel.
            - Bukan gaya dosen, bukan gaya berita, bukan gaya textbook.
            - Harus terasa ringan, hangat, dan mudah dicerna.
            - Boleh terdengar seperti "ngobrol sambil ngajarin", tapi tetap rapi dan bernilai.

            POLA KALIMAT YANG DIINGINKAN:
            - Boleh gunakan pola seperti:
            "Banyak orang kira..."
            "Padahal sebenarnya..."
            "Yang sering bikin salah paham itu..."
            "Jadi simpelnya..."
            "Intinya gini..."
            "Kalau dijelasin gampangnya..."
            "Makanya..."
            - Jangan dipakai terus-menerus di semua slide, tapi nuansanya harus sejenis: santai, jelas, dan mudah diikuti.

            STRUKTUR ISI SLIDE:
            - Panjang isi slide HARUS fleksibel, tergantung kebutuhan isi.
            - Kalau poinnya bisa dijelaskan dengan singkat, cukup 1-3 kalimat saja.
            - Kalau poinnya butuh konteks, contoh, atau penjelasan tambahan, boleh lebih panjang.
            - Tidak semua slide harus punya pembuka, isi, dan penutup lengkap.
            - Ada slide yang cukup berisi 1 insight pendek.
            - Ada slide yang bisa berisi penjelasan + contoh.
            - Prioritaskan kejelasan dan daya kena, BUKAN panjang tulisan.
            - Jangan memaksa semua slide terasa penuh.
            - Kalau sebuah ide sudah jelas dalam kalimat singkat, berhenti di situ. Jangan ditambah filler.
            - Variasikan panjang antar slide supaya hasil terasa lebih natural dan tidak monoton.
            - Setiap slide tetap harus terasa utuh, tapi tidak harus panjang.

            ATURAN BENTUK KALIMAT:
            - Gunakan kalimat pendek sampai menengah.
            - Hindari kalimat berbelit-belit.
            - Pecah kalimat atau paragraf supaya nyaman dibaca di carousel.
            - Jelaskan hal rumit dengan kata-kata sederhana.
            - Lebih baik singkat tapi kuat, daripada panjang tapi bertele-tele.
            - Hindari filler atau pengulangan ide dengan kata berbeda.
            - Jangan memanjangkan kalimat hanya supaya slide terlihat penuh.
            - Boleh ada penekanan pada kata penting dengan HURUF KAPITAL secukupnya, jangan berlebihan.
            - Hindari terlalu banyak istilah teknis. Kalau harus pakai istilah teknis, langsung sederhanakan artinya.

            LARANGAN GAYA BAHASA:
            - Jangan terdengar seperti artikel SEO, blog formal, modul, skripsi, jurnal, atau Wikipedia.
            - Jangan pakai bahasa terlalu kaku seperti:
            "merupakan", "adapun", "oleh karena itu", "hal tersebut", "guna", "berdasarkan", "dapat disimpulkan", "perlu diketahui".
            - Jangan terlalu menggurui.
            - Jangan terlalu salesy, terlalu motivator, atau terlalu heboh.
            - Jangan terasa generik atau seperti template AI.
            - Jangan terlalu curhat personal jika topiknya lebih cocok dijelaskan secara edukatif.

            PATOKAN KUALITAS HASIL:
            - Saat dibaca, audiens harus merasa: "Ohhh, sekarang aku paham."
            - Penjelasan harus simpel, jelas, santai, dan tetap pintar.
            - Harus terasa seperti manusia asli yang paham topik lalu menjelaskan dengan ringan.
            - Setiap slide harus punya nilai edukasi yang jelas, bukan sekadar kata-kata enak dibaca.

            CONTOH RASA YANG BENAR:
            - "Banyak orang kira niche itu penentu utama views. Padahal belum tentu juga."
            - "Yang sering bikin salah paham, orang fokus ke topiknya, tapi lupa cek kualitas isi kontennya."
            - "Jadi simpelnya, bukan cuma bahas apa, tapi gimana cara kamu nyampeinnya."

            CONTOH RASA YANG SALAH:
            - "Niche konten merupakan elemen penting dalam strategi distribusi audiens."
            - "Berdasarkan analisis, kualitas konten memiliki korelasi terhadap performa engagement."
            - "Oleh karena itu, kreator perlu melakukan optimalisasi konten secara konsisten."

            PENTING SEKALI:
            Jangan menulis seperti AI yang sedang membuat artikel.
            Tulis seperti creator yang paham topik, lalu menjelaskan dengan santai, simpel, dan enak dibaca di TikTok.
        """

        # Format-aware density rules
        format_constraint = ""
        # Jika Anda masih memakai config.OUTPUT_FORMAT, aktifkan ini
        # if config.OUTPUT_FORMAT == "square":
        format_constraint = f"""
            PERHATIAN FORMAT SQUARE (1:1):
            - Output format saat ini adalah SQUARE.
            - Maksimal 30 kata per slide.
            - Tulis penjelasan yang cukup agar audiens paham, tapi tetap ringkas.
            - Boleh 2-4 kalimat per slide, asal padat dan bermakna.
            - Jangan terlalu singkat sampai terasa kurang konteks.
        """

        density_rules = f"""
            ATURAN KEPADATAN ISI:
            - Jangan anggap semua slide harus panjang.
            - Beberapa slide boleh sangat singkat jika pesannya sudah kuat.
            - Tulis seperlunya saja.
            - Stop setelah inti poin sudah jelas.
            - Utamakan konten padat, bukan konten panjang.
            - Variasikan panjang isi antar slide agar terasa natural.
            {format_constraint}
        """

        if style == "box-title-content":
            format_wajib = f"""
            Format wajib JSON:
            {{
                "tiktok_title": "Judul Postingan Catchy",
                "tiktok_description": "Deskripsi/caption singkat dan menarik.",
                "tiktok_tags": ["tag1", "tag2", "tag3"],
                "slides": [
                    {{
                        "type": "judul",
                        "teks": "Judul cover TikTok",
                        "keyword_gambar": "keyword pexels"
                    }},
                    {{
                        "type": "konten",
                        "slide_title": "1. JUDUL PENDEK",
                        "teks": "Isi slide yang fleksibel: bisa singkat, bisa sedang, bisa lebih panjang kalau memang perlu.\\n\\nKalau satu insight sudah jelas dalam 1-3 kalimat, jangan dipanjangkan.\\n\\nKalau butuh contoh atau konteks, baru lanjutkan.",
                        "keyword_gambar": "keyword pexels"
                    }}
                ]
            }}

            Aturan khusus "slide_title" (PENTING):
            - WAJIB ada field "slide_title" pada setiap slide konten.
            - "slide_title" harus SINGKAT, PADAT, dan HURUF KAPITAL.
            - Maksimal 2-7 kata.
            - Harus terdengar seperti judul section carousel TikTok, bukan headline berita.
            - Contoh gaya yang diinginkan:
            "NICHE KONTEN"
            "KONTEN CAMPUR-CAMPUR"
            "FOKUS KE KUALITAS"
            "JANGAN SALAH FOKUS"
            - KONSISTENSI PENOMORAN: Evaluasi apakah judul slide lebih baik menggunakan angka (1., 2., dst).
            Jika IYA, berikan angka pada SEMUA `slide_title` konten.
            Jika TIDAK, hapus angka dari SEMUA `slide_title`.
            Jangan campur aduk.

            Aturan khusus field "teks":
            - Teks HARUS edukatif, jelas, dan mudah dipahami.
            - Teks HARUS terasa santai, ringan, dan natural seperti orang yang lagi ngajelasin ke teman.
            - Jangan terlalu personal seperti curhat mendalam, tapi juga jangan terlalu formal.
            - Fokus pada penjelasan yang simpel, relate, dan langsung kena.
            - Panjang teks HARUS fleksibel. Tidak semua slide perlu panjang.
            - Jika inti poin sudah jelas dalam kalimat singkat, jangan tambahkan filler.
            - Pisahkan kalimat atau paragraf dengan dua kali enter (\\n\\n) langsung di JSON.
            """
        else:
            format_wajib = f"""
            Format wajib JSON:
            {{
                "tiktok_title": "Judul Postingan Catchy",
                "tiktok_description": "Deskripsi/caption singkat dan menarik.",
                "tiktok_tags": ["tag1", "tag2", "tag3"],
                "slides": [
                    {{
                        "type": "judul",
                        "teks": "Judul singkat",
                        "keyword_gambar": "keyword pexels"
                    }},
                    {{
                        "type": "konten",
                        "teks": "Isi slide dengan gaya creator yang santai, jelas, dan fleksibel panjangnya. Kalau cukup singkat, jangan dipanjangkan.",
                        "keyword_gambar": "keyword pexels"
                    }}
                ]
            }}
            """

        base_rules = f"""
            Kamu adalah pembuat konten TikTok profesional yang sangat paham cara menulis carousel dengan rasa bahasa manusia asli.

            Tugas:
            1. Gunakan Google Search (wajib) untuk riset data/tren terbaru mengenai topik: {topic}
            2. Kembalikan HANYA format JSON tanpa teks pengantar atau penutup apapun.
            3. Buatkan judul, deskripsi/caption, hashtag, dan isi carousel.

            {context_instruction}
            {style_voice_rules}
            {density_rules}
            {format_wajib}

            ATURAN OUTPUT UMUM:
            - keyword_gambar harus Bahasa Inggris
            - total slide = {num_slides + 1}
            - JANGAN PERNAH memberikan emoji di dalam "teks", "slide_title", atau judul slide agar render aman
            - Kamu sangat disarankan menggunakan emoji yang memikat pada "tiktok_title" dan "tiktok_description"
            - Isi setiap slide harus relevan dengan topik, tidak muter-muter, dan tetap bernilai
            - Hindari pembukaan yang terlalu generik seperti "Pada era digital saat ini"
            - Hindari kalimat yang terlalu rapi dan steril seperti tulisan AI
            - Utamakan rasa: personal, reflektif, hangat, dan relatable
            - Output harus terasa seperti creator asli yang sedang berbagi pengalaman + insight
            - Jangan samakan panjang semua slide
            - Biarkan ada variasi: ada slide yang pendek, ada yang sedang, ada yang sedikit lebih panjang bila dibutuhkan
            - Jangan membuat semua slide terasa seperti paragraf penuh
            
            PENTING: FORMAT OUTPUT WAJIB BERUPA RAW JSON. PASTIKAN TIDAK ADA SYNTAX ERROR.
        """

        print(f"🧠 Meminta Gemini riset (Search) & membuat konten + metadata untuk topik: '{topic}'...")
        return self._generate_json_with_retry(client, base_rules)