from PIL import Image, ImageDraw, ImageFont

from . import config


class SlideRenderer:
    """Modul untuk memproses dan merender teks pada gambar slide."""

    def __init__(self, title_font_path: str, content_font_path: str):
        self.title_font_path = title_font_path
        self.content_font_path = content_font_path

    def _load_font(self, font_path: str, font_size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(font_path, font_size)
        except IOError:
            return ImageFont.load_default()

    def _wrap_text_by_pixel_width(self, draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        paragraphs = text.split("\n")
        final_lines = []

        for paragraph in paragraphs:
            words = paragraph.split()
            if not words:
                final_lines.append("")
                continue

            current_line = words[0]
            for word in words[1:]:
                candidate = f"{current_line} {word}"
                bbox = draw.textbbox((0, 0), candidate, font=font)
                candidate_width = bbox[2] - bbox[0]

                if candidate_width <= max_width:
                    current_line = candidate
                else:
                    final_lines.append(current_line)
                    current_line = word

            final_lines.append(current_line)

        return "\n".join(final_lines)

    def _calculate_text_layout(self, draw: ImageDraw.Draw, text: str, font_size: int, style: str, font_type: str = "content") -> dict:
        font_path = self.title_font_path if font_type == "title" else self.content_font_path
        font = self._load_font(font_path, font_size)

        if style in ("box", "box-title-content"):
            max_text_width = config.CANVAS_WIDTH - (config.TEXT_SIDE_MARGIN * 2) - (config.BOX_PADDING_X * 2)
        else:
            max_text_width = config.CANVAS_WIDTH - (config.TEXT_SIDE_MARGIN * 2)

        wrapped_text = self._wrap_text_by_pixel_width(draw, text, font, max_text_width)

        bbox = draw.multiline_textbbox(
            (0, 0),
            wrapped_text,
            font=font,
            align="center",
            spacing=config.TEXT_LINE_SPACING
        )

        t_width = bbox[2] - bbox[0]
        t_height = bbox[3] - bbox[1]

        if style in ("box", "box-title-content"):
            final_height = t_height + (config.BOX_PADDING_Y * 2)
        else:
            final_height = t_height

        return {
            "font": font,
            "wrapped_text": wrapped_text,
            "text_width": t_width,
            "text_height": t_height,
            "block_height": final_height,
            "offset_x": bbox[0],
            "offset_y": bbox[1],
        }

    def _get_best_fitting_layout(self, draw: ImageDraw.Draw, text: str, initial_font_size: int, style: str, font_type: str = "content"):
        layout = self._calculate_text_layout(draw, text, initial_font_size, style, font_type)

        if not config.AUTO_SHRINK_TEXT:
            return initial_font_size, layout

        max_allowed_height = config.CANVAS_HEIGHT - (config.SAFE_TOP_BOTTOM_MARGIN * 2)

        current_size = initial_font_size
        best_layout = layout

        while current_size > config.AUTO_SHRINK_MIN_FONT_SIZE and best_layout["block_height"] > max_allowed_height:
            current_size -= config.AUTO_SHRINK_STEP
            best_layout = self._calculate_text_layout(draw, text, current_size, style, font_type)

        return current_size, best_layout

    def _calculate_box_title_content_layout(self, draw: ImageDraw.Draw, text: str, title_text: str,
                                            title_font_size: int, content_font_size: int) -> dict:
        """Hitung layout lengkap untuk style box-title-content (judul + paragraf konten)."""
        title_font = self._load_font(self.title_font_path, title_font_size)
        content_font = self._load_font(self.content_font_path, content_font_size)
        max_p_width = config.CANVAS_WIDTH - (config.TEXT_SIDE_MARGIN * 2) - (config.BOX_PADDING_X * 2)

        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        wrapped_title = self._wrap_text_by_pixel_width(draw, title_text, title_font, max_p_width)

        title_bbox = draw.multiline_textbbox(
            (0, 0), wrapped_title, font=title_font, align="center", spacing=config.TEXT_LINE_SPACING
        )
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]
        title_box_height = title_height + (config.BOX_PADDING_Y * 2)

        wrapped_paragraphs = []
        total_height = title_box_height + config.TITLE_CONTENT_SPACING
        for paragraph in paragraphs:
            wrapped_paragraph = self._wrap_text_by_pixel_width(draw, paragraph, content_font, max_p_width)
            paragraph_bbox = draw.multiline_textbbox(
                (0, 0), wrapped_paragraph, font=content_font, spacing=config.TEXT_LINE_SPACING
            )
            paragraph_width = paragraph_bbox[2] - paragraph_bbox[0]
            paragraph_height = paragraph_bbox[3] - paragraph_bbox[1]
            wrapped_paragraphs.append({
                "text": wrapped_paragraph,
                "width": paragraph_width,
                "height": paragraph_height,
                "offset_x": paragraph_bbox[0],
                "offset_y": paragraph_bbox[1],
            })
            total_height += paragraph_height + (config.BOX_PADDING_Y * 2) + config.PARAGRAPH_SPACING

        if wrapped_paragraphs:
            total_height -= config.PARAGRAPH_SPACING

        return {
            "title_font": title_font,
            "content_font": content_font,
            "wrapped_title": wrapped_title,
            "title_width": title_width,
            "title_height": title_height,
            "title_offset_x": title_bbox[0],
            "title_offset_y": title_bbox[1],
            "title_box_height": title_box_height,
            "paragraphs": wrapped_paragraphs,
            "total_height": total_height,
            "title_font_size": title_font_size,
            "content_font_size": content_font_size,
        }

    def _get_best_fitting_box_title_content_layout(self, draw: ImageDraw.Draw, text: str, title_text: str,
                                                   initial_title_font_size: int, initial_content_font_size: int) -> dict:
        """Auto-shrink loop: kecilkan font title + content bersamaan sampai muat di canvas."""
        layout = self._calculate_box_title_content_layout(
            draw, text, title_text, initial_title_font_size, initial_content_font_size
        )

        if not config.AUTO_SHRINK_TEXT:
            return layout

        max_allowed_height = config.CANVAS_HEIGHT - (config.SAFE_TOP_BOTTOM_MARGIN * 2)
        current_title_size = initial_title_font_size
        current_content_size = initial_content_font_size
        best_layout = layout

        while (
            current_content_size > config.AUTO_SHRINK_MIN_FONT_SIZE
            and best_layout["total_height"] > max_allowed_height
        ):
            current_title_size -= config.AUTO_SHRINK_STEP
            current_content_size -= config.AUTO_SHRINK_STEP
            best_layout = self._calculate_box_title_content_layout(
                draw, text, title_text, current_title_size, current_content_size
            )

        return best_layout

    def process_slide(self, img: Image.Image, text: str, font_size: int, style: str, title_text: str = "", is_title: bool = False) -> Image.Image:
        """Proses gambar slide: resize/crop sesuai preset, lalu render teks sesuai style."""
        target_size = (config.CANVAS_WIDTH, config.CANVAS_HEIGHT)
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

        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)

        if style == "box-title-content" and title_text:
            title_text = title_text.upper()
            layout = self._get_best_fitting_box_title_content_layout(
                draw,
                text,
                title_text,
                font_size + config.TITLE_BOX_FONT_BONUS,
                font_size,
            )

            start_y = (img.height - layout["total_height"]) / 2

            # 1. Gambar block judul
            title_x = (img.width - layout["title_width"]) / 2
            title_y = start_y + config.BOX_PADDING_Y

            title_box_left = title_x - config.BOX_PADDING_X
            title_box_top = start_y
            title_box_right = title_x + layout["title_width"] + config.BOX_PADDING_X
            title_box_bottom = start_y + layout["title_box_height"]

            draw.rounded_rectangle(
                [title_box_left, title_box_top, title_box_right, title_box_bottom],
                radius=config.BOX_RADIUS,
                fill=config.BOX_FILL
            )
            draw.multiline_text(
                (title_x - layout["title_offset_x"], title_y - layout["title_offset_y"]),
                layout["wrapped_title"],
                font=layout["title_font"],
                fill=config.BOX_TEXT_FILL,
                align="center",
                spacing=config.TEXT_LINE_SPACING,
            )

            content_y = title_box_bottom + config.TITLE_CONTENT_SPACING

            # 2. Gambar block konten
            for paragraph in layout["paragraphs"]:
                px = config.TEXT_SIDE_MARGIN + config.BOX_PADDING_X
                py = content_y + config.BOX_PADDING_Y

                box_left = px - config.BOX_PADDING_X
                box_top = content_y
                box_right = px + max(paragraph["width"], 10) + config.BOX_PADDING_X
                box_bottom = content_y + paragraph["height"] + (config.BOX_PADDING_Y * 2)

                draw.rounded_rectangle([box_left, box_top, box_right, box_bottom], radius=config.BOX_RADIUS, fill=config.BOX_FILL)
                draw.multiline_text(
                    (px - paragraph["offset_x"], py - paragraph["offset_y"]),
                    paragraph["text"],
                    font=layout["content_font"],
                    fill=config.BOX_TEXT_FILL,
                    align="left",
                    spacing=config.TEXT_LINE_SPACING,
                )

                content_y = box_bottom + config.PARAGRAPH_SPACING

            return img.convert("RGB")

        font_type = "title" if is_title else "content"
        final_font_size, layout = self._get_best_fitting_layout(draw, text, font_size, style, font_type)
        font = layout["font"]
        wrapped_text = layout["wrapped_text"]
        text_width = layout["text_width"]
        text_height = layout["text_height"]
        text_offset_x = layout["offset_x"]
        text_offset_y = layout["offset_y"]

        x_pos = (img.width - text_width) / 2
        y_pos = ((img.height - text_height) / 2) + config.TEXT_VERTICAL_OFFSET

        if style == "outline":
            stroke_width = max(2, int(final_font_size * config.OUTLINE_STROKE_RATIO))
            draw.multiline_text(
                (x_pos - text_offset_x, y_pos - text_offset_y),
                wrapped_text,
                font=font,
                fill=config.OUTLINE_TEXT_FILL,
                align="center",
                spacing=config.TEXT_LINE_SPACING,
                stroke_width=stroke_width,
                stroke_fill=config.OUTLINE_STROKE_FILL
            )

        elif style in ("box", "box-title-content"):
            box_left = x_pos - config.BOX_PADDING_X
            box_top = y_pos - config.BOX_PADDING_Y
            box_right = x_pos + text_width + config.BOX_PADDING_X
            box_bottom = y_pos + text_height + config.BOX_PADDING_Y

            draw.rounded_rectangle(
                [box_left, box_top, box_right, box_bottom],
                radius=config.BOX_RADIUS,
                fill=config.BOX_FILL
            )

            draw.multiline_text(
                (x_pos - text_offset_x, y_pos - text_offset_y),
                wrapped_text,
                font=font,
                fill=config.BOX_TEXT_FILL,
                align="center",
                spacing=config.TEXT_LINE_SPACING
            )

        return img.convert("RGB")
