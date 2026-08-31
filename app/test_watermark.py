"""Quick visual test for add_watermark — no server or ML model needed."""
from PIL import Image, ImageDraw, ImageFont


def add_watermark(img: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(img)
    text = "AI-GENERATED"
    font_size = max(18, img.width // 40)
    font = None
    for path in ["arial.ttf", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]
    margin = 14
    x = margin
    y = img.height - text_h - bbox[1] - margin
    draw.text((x, y), text, font=font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    return img


if __name__ == "__main__":
    # Create a gradient-like test image to simulate a generated image
    img = Image.new("RGB", (1024, 1024))
    draw = ImageDraw.Draw(img)
    for y in range(1024):
        r = int(y * 100 / 1024) + 30
        g = int(y * 60 / 1024) + 20
        b = int(200 - y * 80 / 1024)
        draw.line([(0, y), (1024, y)], fill=(r, g, b))

    img = add_watermark(img)
    out = "watermark_test_output.png"
    img.save(out)
    print(f"Saved: {out}  — open it to verify the watermark.")
