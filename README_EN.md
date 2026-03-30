# 🚀 TikTok Carousel Image Generator (Auto-Content Creator)

> 🌐 **Language:** [🇮🇩 Bahasa Indonesia](README.md) | 🇬🇧 English

An *open-source* Python project to automate the creation of Carousel (Slideshow) content for TikTok, Instagram Reels, and YouTube Shorts.

Just provide a single topic/idea, and the system will research the internet, write the content script, find high-resolution *background* images, render TikTok-style text, and prepare ready-to-upload metadata (Caption & Hashtags).

## 🎯 Project Goal
To make it easy for *Content Creators* and *Affiliate Marketers* to produce educational or tip-based *slideshow* content at scale, consistently, and in high quality — without having to manually design each slide one by one.

## ✨ Key Features
1. **🤖 AI Content Research & Copywriting:** Powered by **Google Gemini AI** with *Google Search Grounding*. The system searches for the most *up-to-date* facts and trends from the internet before writing slide text.
2. **🖼️ Auto-Sourcing Background:** Integrated with **Pexels API** to automatically search and download high-quality portrait images. Includes *Anti-Duplicate* logic to prevent image repetition.
3. **🎨 Smart Image Processing (Pillow):**
   - Automatically *crop* and *resize* images to 9:16 ratio (1080x1920).
   - Add precision text *overlay* centered on screen.
   - **Auto-shrink Text:** Font size automatically shrinks if the text is too long, preventing overflow.
4. **💅 Three TikTok Text Visual Styles:**
   - `outline`: Bold white text with thick black *stroke* (Classic TikTok style).
   - `box`: Text inside a semi-transparent rounded rectangle box.
   - `box-title-content`: Storytelling-style text (personal) with an *uppercase* title in a separate box on top, and content paragraphs split into floating boxes.
5. **🧠 Smart Context Memory (Multi-part Series):** Automatically saves generation history to `context.txt`. When creating "Part 2", the AI reads this file and **won't repeat** the same points from "Part 1".
6. **📦 Auto-Metadata Generation:** Produces a `metadata.json` file containing a Catchy Title, Description/Caption, and Hashtags ready to *copy-paste* when uploading.
7. **🅰️ Auto-Download Font:** Don't have a *bold* font? The system will automatically download **Montserrat-Black** if the font file is not found on your machine.

---

## 🛠️ Setup & Installation

**1. Clone the Repository & Enter the Folder**
```bash
git clone https://github.com/NaufalRizqullah/tiktok-carousel-generator
cd tiktok-carousel-generator
```

**2. Install Dependencies**
You can use `pip` or `uv` (recommended for speed).
```bash
# Using uv
uv venv
uv pip install -r requirements.txt

# Using standard pip
pip install -r requirements.txt
```

**3. Setup API Keys (.env)**
Create a file named `.env` in the project *root folder*, then enter your API keys:
```env
PEXELS_API_KEY=your_pexels_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here
```
*(Get free keys at [Pexels API](https://www.pexels.com/api/) and [Google AI Studio](https://aistudio.google.com/))*

---

## 🚀 Usage

Run the `main.py` script from your terminal/command prompt.

**Example 1: Basic Run (Outline Style)**
```bash
python main.py -t "Beginner Diet Tips"
```
*(Automatically creates 6 images: 1 Title + 5 Content slides in the `output` folder)*

**Example 2: Custom Parameters (Box Style, 7 Slides, Custom Folder)**
```bash
python main.py -t "SEO Optimization Tips 2026" -s 7 --style box -o "seo_content"
```

**Example 3: Creating a Content Series (Part 1 & Part 2)**
Thanks to the *Context Memory* feature, you can create serial content without worrying about repetitive material:
```bash
# First run
python main.py -t "Small Business Ideas part 1" -o "business_p1"

# Second run (AI will read context.txt and generate NEW ideas)
python main.py -t "Small Business Ideas part 2" -o "business_p2"
```
> ⚠️ **IMPORTANT:** If you want to switch to a **completely different** topic (e.g., from "Business Ideas" to "Cooking Recipes"), make sure to **DELETE** the `context.txt` file first so the AI doesn't get confused!

---

## ⚙️ CLI Parameters (Arguments)

| Short Arg | Long Arg | Description | Default |
| :--- | :--- | :--- | :--- |
| `-t` | `--topic` | **(Required)** Topic for AI to generate content about | *None* |
| `-s` | `--slides` | Number of content slides (excluding the title slide) | `5` |
| `--style` | `--style` | Text visual style (`outline`, `box`, or `box-title-content`) | `outline` |
| `--title-family`| `--title-family`| Font family for title (e.g., `LeagueSpartan`) | *from config* |
| `--title-weight`| `--title-weight`| Title font weight (`100` - `900`) | *from config* |
| `--content-family`| `--content-family`| Font family for content (e.g., `Poppins`) | *from config* |
| `--content-weight`| `--content-weight`| Content font weight (`100` - `900`) | *from config* |
| `-o` | `--output` | Name of the folder to save output images and metadata | `output` |

---

## 📁 Output Structure

After the script finishes running, your chosen output folder (default: `output/`) will contain:

```text
output/
├── slide_00.jpg        # Cover/Title Slide
├── slide_01.jpg        # Content Slide 1
├── slide_02.jpg        # Content Slide 2
├── ...
└── metadata.json       # Contains TikTok Title, Caption, and Hashtags
```

Additionally, a `context.txt` file will be created/updated in the *root folder*, storing the history of previously discussed points.

---

## 📂 Project Structure

This project uses a modular architecture. All core logic is separated into the `tiktok_carousel/` *package* for easier maintenance, extension, and testing.

```text
tiktok-image-gen/
├── main.py                          # CLI entry point (argparse + load .env)
├── tiktok_carousel/                 # Main package
│   ├── __init__.py                  # Re-export TikTokCarouselGenerator
│   ├── config.py                    # All configuration constants (canvas, font, colors, etc.)
│   ├── utils.py                     # Utilities: font download, context memory, text sanitization
│   ├── content.py                   # AI Content Generator module (Google Gemini)
│   ├── image_source.py              # Image Sourcing module (Pexels API)
│   ├── renderer.py                  # Image Processing & Text Rendering module (Pillow)
│   └── generator.py                 # Orchestrator: combines all modules into a pipeline
├── .env                             # API Keys (not committed)
├── .env.example                     # Example .env format
├── context.txt                      # Auto-generated: context memory between Parts
├── fonts/                           # Directory for storing custom font files (.ttf)
├── output/                          # Output folder for images & metadata
├── pyproject.toml                   # Python project configuration
├── requirements.txt                 # Dependency list
└── README.md
```

### Module Descriptions

| Module | Description |
| :--- | :--- |
| `config.py` | Contains all global configuration variables (canvas size, font, box/outline colors, margins, JPG quality, etc.). Edit this file to *tweak* the appearance without touching the logic. |
| `utils.py` | Pure utility functions: auto-download Montserrat-Black font, read/write `context.txt` for the *memory* feature, and text sanitization (remove emoji/non-BMP characters). |
| `content.py` | `ContentGenerator` class — handles communication with Google Gemini AI, including *prompt engineering*, *retry logic* with *exponential backoff*, and JSON response parsing. |
| `image_source.py` | `PexelsImageSource` class — searches & downloads *portrait* images from the Pexels API, with *anti-duplicate* logic to prevent image repetition. |
| `renderer.py` | `SlideRenderer` class — processes images (*resize/crop* to 9:16), renders text in various styles (`outline`, `box`, `box-title-content`), including *auto-shrink* and *text wrapping*. |
| `generator.py` | `TikTokCarouselGenerator` class — *Orchestrator* that unifies all modules into a single *pipeline*: generate content → fetch images → render slides → save files. |

---

## 🛠️ Advanced Configuration (Tweaking)

The system is designed to be highly flexible. You can change the layout, colors, sizes, and even AI *behavior* by modifying the variables in `tiktok_carousel/config.py`.

Here is the complete list of customizable variables:

### ⚙️ AI & System Settings
| Variable | Description | Default |
| :--- | :--- | :--- |
| `CONTEXT_FILE` | Text file name for storing memory/context so the AI doesn't repeat points in the next *Part*. | `"context.txt"` |
| `POINTS_ONLY_TEXT` | If `True`, forces AI to write only short bullet points (not paragraphs). | `True` |
| `MAX_WORDS_PER_SLIDE`| Maximum number of words that AI can generate per content slide. | `30` |

### 📐 Canvas & Margin Settings
| Variable | Description | Default |
| :--- | :--- | :--- |
| `CANVAS_WIDTH` | Output image width resolution (pixels). | `1080` |
| `CANVAS_HEIGHT` | Output image height resolution (pixels). | `1920` |
| `SAFE_TOP_BOTTOM_MARGIN`| Vertical safe area to prevent text from being covered by TikTok UI (username, caption, *like* button). | `180` |
| `TEXT_SIDE_MARGIN` | Safe distance of text from left and right edges. | `80` |
| `TEXT_VERTICAL_OFFSET`| Shift text position vertically. `0` = perfectly centered. | `0` |

### 🔠 Typography Settings (Font)
| Variable | Description | Default |
| :--- | :--- | :--- |
| `TITLE_FONT_FAMILY`| Font family/folder name for Title Slide. | `"LeagueSpartan"` |
| `TITLE_FONT_WEIGHT`| Title font weight (100=Thin... 400=Regular... 900=Black). | `700` |
| `CONTENT_FONT_FAMILY`| Font family/folder name for Content Slide. | `"Poppins"` |
| `CONTENT_FONT_WEIGHT`| Content font weight (100=Thin... 400=Regular... 900=Black). | `400` |
| `TITLE_FONT_SIZE` | Main font size for the Title/Cover Slide. | `85` |
| `CONTENT_FONT_SIZE` | Main font size for Content Slides. | `68` |
| `TEXT_LINE_SPACING` | Line spacing between text lines (*line height*). | `10` |
| `AUTO_SHRINK_TEXT` | If `True`, font size automatically shrinks when AI text is too long and exceeds the safe boundary. | `False` |
| `AUTO_SHRINK_MIN_FONT_SIZE`| Minimum font size limit when *auto-shrink* mode is active. | `42` |
| `AUTO_SHRINK_STEP` | Font size reduction amount per shrink iteration. | `2` |

### 🎨 Visual Style: Box (Text Box)
| Variable | Description | Default |
| :--- | :--- | :--- |
| `BOX_PADDING_X` | Horizontal spacing between text and inner box edge. | `55` |
| `BOX_PADDING_Y` | Vertical spacing between text and inner box edge. | `35` |
| `BOX_RADIUS` | Corner rounding level (*rounded rectangle*). | `28` |
| `BOX_FILL` | Box background color in `(R, G, B, Opacity)` format. Default is semi-transparent white. | `(255, 255, 255, 235)` |
| `BOX_TEXT_FILL` | Text color inside the box. Default is black. | `(0, 0, 0)` |

### 🖌️ Visual Style: Outline (Stroke)
| Variable | Description | Default |
| :--- | :--- | :--- |
| `OUTLINE_TEXT_FILL` | Main text color. | `"white"` |
| `OUTLINE_STROKE_FILL`| Stroke/outline edge color. | `"black"` |
| `OUTLINE_STROKE_RATIO`| Stroke thickness ratio relative to font size (e.g., `0.08` × font `85`). | `0.08` |

### 💾 Output Settings
| Variable | Description | Default |
| :--- | :--- | :--- |
| `JPG_QUALITY` | JPG image compression quality (scale 1-100). | `95` |

---

## 📸 Example Results

Here are example images generated by this system for each visual style:

### 🖌️ Style: `outline`

| Slide 00 | Slide 01 |
| :---: | :---: |
| ![Slide 00](src/images/outline/slide_00.jpg) | ![Slide 01](src/images/outline/slide_01.jpg) |
| **Slide 02** | **Slide 03** |
| ![Slide 02](src/images/outline/slide_02.jpg) | ![Slide 03](src/images/outline/slide_03.jpg) |

### 📦 Style: `box`

| Slide 00 | Slide 01 |
| :---: | :---: |
| ![Slide 00](src/images/box/slide_00.jpg) | ![Slide 01](src/images/box/slide_01.jpg) |
| **Slide 02** | **Slide 03** |
| ![Slide 02](src/images/box/slide_02.jpg) | ![Slide 03](src/images/box/slide_03.jpg) |

### 📝 Style: `box-title-content`

| Slide 00 | Slide 01 |
| :---: | :---: |
| ![Slide 00](src/images/box-title-content/slide_00.jpg) | ![Slide 01](src/images/box-title-content/slide_01.jpg) |
| **Slide 02** | **Slide 03** |
| ![Slide 02](src/images/box-title-content/slide_02.jpg) | ![Slide 03](src/images/box-title-content/slide_03.jpg) |
