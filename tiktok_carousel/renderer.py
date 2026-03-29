from PIL import Image, ImageDraw, ImageFont

from . import config


class SlideRenderer:
    """Modul untuk memproses dan merender teks pada gambar slide."""

    def __init__(self, font_path: str):
        self.font_path = font_path

    def _load_font(self, font_size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(self.font_path, font_size)
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

    def _calculate_text_layout(self, draw: ImageDraw.Draw, text: str, font_size: int, style: str) -> dict:
        font = self._load_font(font_size)

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

    def _get_best_fitting_layout(self, draw: ImageDraw.Draw, text: str, initial_font_size: int, style: str):
        layout = self._calculate_text_layout(draw, text, initial_font_size, style)

        if not config.AUTO_SHRINK_TEXT:
            return initial_font_size, layout

        max_allowed_height = config.CANVAS_HEIGHT - (config.SAFE_TOP_BOTTOM_MARGIN * 2)

        current_size = initial_font_size
        best_layout = layout

        while current_size > config.AUTO_SHRINK_MIN_FONT_SIZE and best_layout["block_height"] > max_allowed_height:
            current_size -= config.AUTO_SHRINK_STEP
            best_layout = self._calculate_text_layout(draw, text, current_size, style)

        return current_size, best_layout

    def process_slide(self, img: Image.Image, text: str, font_size: int, style: str, title_text: str = "") -> Image.Image:
        """Proses gambar slide: resize/crop ke 9:16, lalu render teks sesuai style."""
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
            title_font = self._load_font(font_size + 5)
            c_font = self._load_font(font_size)
            max_p_width = config.CANVAS_WIDTH - (config.TEXT_SIDE_MARGIN * 2) - (config.BOX_PADDING_X * 2)

            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

            # Wrap titlenya juga agar kalau kepanjangan bisa turun ke bawah
            wrapped_title = self._wrap_text_by_pixel_width(draw, title_text, title_font, max_p_width)

            # 1. Hitung total tinggi
            t_bbox = draw.multiline_textbbox((0, 0), wrapped_title, font=title_font, align="center", spacing=config.TEXT_LINE_SPACING)
            tt_w = t_bbox[2] - t_bbox[0]
            tt_h = t_bbox[3] - t_bbox[1]
            title_offset_x = t_bbox[0]
            title_offset_y = t_bbox[1]
            title_box_h = tt_h + (config.BOX_PADDING_Y * 2)

            total_h = title_box_h
            SPACING_TITLE_CONTENT = 60
            SPACING_PARAGRAPHS = 25

            total_h += SPACING_TITLE_CONTENT

            wrapped_paragraphs = []
            for p in paragraphs:
                wp = self._wrap_text_by_pixel_width(draw, p, c_font, max_p_width)
                p_bbox = draw.multiline_textbbox((0, 0), wp, font=c_font, spacing=config.TEXT_LINE_SPACING)
                pw = p_bbox[2] - p_bbox[0]
                ph = p_bbox[3] - p_bbox[1]
                wrapped_paragraphs.append((wp, pw, ph, p_bbox[0], p_bbox[1]))
                total_h += ph + (config.BOX_PADDING_Y * 2) + SPACING_PARAGRAPHS

            if paragraphs:
                total_h -= SPACING_PARAGRAPHS

            start_y = (img.height - total_h) / 2

            # 2. Gambar block judul
            t_x = (img.width - tt_w) / 2
            t_y = start_y + config.BOX_PADDING_Y

            title_box_left = t_x - config.BOX_PADDING_X
            title_box_top = start_y
            title_box_right = t_x + tt_w + config.BOX_PADDING_X
            title_box_bottom = start_y + title_box_h

            draw.rounded_rectangle(
                [title_box_left, title_box_top, title_box_right, title_box_bottom],
                radius=config.BOX_RADIUS,
                fill=config.BOX_FILL
            )
            draw.multiline_text((t_x - title_offset_x, t_y - title_offset_y), wrapped_title, font=title_font, fill=config.BOX_TEXT_FILL, align="center", spacing=config.TEXT_LINE_SPACING)

            content_y = title_box_bottom + SPACING_TITLE_CONTENT

            # 3. Gambar block konten
            for wp, pw, ph, p_offset_x, p_offset_y in wrapped_paragraphs:
                px = config.TEXT_SIDE_MARGIN + config.BOX_PADDING_X
                py = content_y + config.BOX_PADDING_Y

                b_left = px - config.BOX_PADDING_X
                b_top = content_y
                b_right = px + max(pw, 10) + config.BOX_PADDING_X
                b_bottom = content_y + ph + (config.BOX_PADDING_Y * 2)

                draw.rounded_rectangle([b_left, b_top, b_right, b_bottom], radius=config.BOX_RADIUS, fill=config.BOX_FILL)
                draw.multiline_text((px - p_offset_x, py - p_offset_y), wp, font=c_font, fill=config.BOX_TEXT_FILL, align="left", spacing=config.TEXT_LINE_SPACING)

                content_y = b_bottom + SPACING_PARAGRAPHS

            return img.convert("RGB")

        final_font_size, layout = self._get_best_fitting_layout(draw, text, font_size, style)
        font = layout["font"]
        wrapped_text = layout["wrapped_text"]
        t_width = layout["text_width"]
        t_height = layout["text_height"]
        t_offset_x = layout["offset_x"]
        t_offset_y = layout["offset_y"]

        x_pos = (img.width - t_width) / 2
        y_pos = ((img.height - t_height) / 2) + config.TEXT_VERTICAL_OFFSET

        if style == "outline":
            stroke_width = max(2, int(final_font_size * config.OUTLINE_STROKE_RATIO))
            draw.multiline_text(
                (x_pos - t_offset_x, y_pos - t_offset_y),
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
            box_right = x_pos + t_width + config.BOX_PADDING_X
            box_bottom = y_pos + t_height + config.BOX_PADDING_Y

            draw.rounded_rectangle(
                [box_left, box_top, box_right, box_bottom],
                radius=config.BOX_RADIUS,
                fill=config.BOX_FILL
            )

            draw.multiline_text(
                (x_pos - t_offset_x, y_pos - t_offset_y),
                wrapped_text,
                font=font,
                fill=config.BOX_TEXT_FILL,
                align="center",
                spacing=config.TEXT_LINE_SPACING
            )

        return img.convert("RGB")
