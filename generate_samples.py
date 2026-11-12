import os
import math
from PIL import Image, ImageDraw, ImageFilter
from app.engine.cache import register_hash, get_hash

def draw_avocado_cross_section(flesh_rgb, inner_flesh_rgb, seed_rgb, seed_outline_rgb, filename):
    width, height = 640, 640
    # Clean neutral background (outdoor cutting board tone)
    img = Image.new("RGB", (width, height), (236, 233, 225))
    draw = ImageDraw.Draw(img)

    center_x, center_y = 320, 340
    outer_rx, outer_ry = 190, 240

    # Draw dark pebbled skin (dark green/black)
    skin_color = (28, 38, 26)
    draw.ellipse(
        [center_x - outer_rx, center_y - outer_ry, center_x + outer_rx, center_y + outer_ry],
        fill=skin_color
    )

    # Outer flesh rim (darker green)
    rim_color = (82, 115, 52)
    draw.ellipse(
        [center_x - outer_rx + 8, center_y - outer_ry + 8, center_x + outer_rx - 8, center_y + outer_ry - 8],
        fill=rim_color
    )

    # Main flesh body
    draw.ellipse(
        [center_x - outer_rx + 22, center_y - outer_ry + 22, center_x + outer_rx - 22, center_y + outer_ry - 22],
        fill=flesh_rgb
    )

    # Inner soft flesh near seed cavity (warmer glow)
    draw.ellipse(
        [center_x - 110, center_y - 120, center_x + 110, center_y + 120],
        fill=inner_flesh_rgb
    )

    # Seed cavity / Seed coat
    seed_rx, seed_ry = 75, 85
    draw.ellipse(
        [center_x - seed_rx, center_y - seed_ry, center_x + seed_rx, center_y + seed_ry],
        fill=seed_rgb,
        outline=seed_outline_rgb,
        width=4
    )

    # Soft subtle blur for organic texture
    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))

    img.save(filename, "JPEG", quality=92)
    return img

def main():
    samples_dir = os.path.join(os.path.dirname(__file__), "media", "samples")
    os.makedirs(samples_dir, exist_ok=True)

    configs = [
        # Unripe: pale watery lime green, white seed
        ("sample_unripe_1.jpg", (162, 196, 108), (188, 214, 138), (248, 248, 242), (225, 225, 215), "sample_unripe_1"),
        ("sample_unripe_2.jpg", (155, 190, 102), (180, 208, 130), (242, 242, 238), (218, 218, 208), "sample_unripe_2"),
        # Borderline: light golden green, tan seed
        ("sample_borderline_1.jpg", (205, 216, 110), (224, 226, 125), (198, 168, 130), (165, 138, 102), "sample_borderline_1"),
        ("sample_borderline_2.jpg", (198, 210, 105), (218, 220, 120), (190, 160, 122), (158, 130, 95), "sample_borderline_2"),
        # Mature: rich buttery golden yellow, dark brown seed cleanly detached
        ("sample_mature_1.jpg", (228, 212, 80), (238, 224, 98), (92, 50, 26), (62, 32, 16), "sample_mature_1"),
        ("sample_mature_2.jpg", (224, 208, 76), (234, 220, 92), (88, 48, 24), (58, 30, 14), "sample_mature_2")
    ]

    for filename, flesh, inner, seed, outline, key in configs:
        filepath = os.path.join(samples_dir, filename)
        draw_avocado_cross_section(flesh, inner, seed, outline, filepath)
        with open(filepath, "rb") as f:
            b = f.read()
            h = get_hash(b)
            register_hash(h, key)
        print(f"Generated sample: {filename} (hash: {h[:8]}...) -> {key}")

if __name__ == "__main__":
    main()

