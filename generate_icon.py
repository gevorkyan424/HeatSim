from PIL import Image, ImageDraw
import os


def make_icon():
    size = 512
    os.makedirs(os.path.join(os.path.dirname(__file__), "assets"), exist_ok=True)
    path_png = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    path_ico = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    draw.ellipse((0, 0, size - 1, size - 1), fill=(250, 250, 250, 255))

    # Left (hot) and right (cold) halves
    draw.pieslice((0, 0, size, size), 90, 270, fill=(220, 70, 50, 255))
    draw.pieslice((0, 0, size, size), 270, 90, fill=(45, 120, 220, 255))

    # Soft white S-shape to separate halves
    draw.ellipse(
        (size * 0.45, size * 0.12, size * 0.92, size * 0.52), fill=(255, 255, 255, 220)
    )
    draw.ellipse(
        (size * 0.08, size * 0.48, size * 0.55, size * 0.88), fill=(255, 255, 255, 220)
    )

    # Small highlights
    draw.ellipse(
        (size * 0.62, size * 0.18, size * 0.7, size * 0.26), fill=(255, 255, 255, 200)
    )
    draw.ellipse(
        (size * 0.22, size * 0.72, size * 0.3, size * 0.8), fill=(255, 255, 255, 200)
    )

    img.save(path_png, format="PNG")
    # Save .ico with multiple sizes for Windows
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(path_ico, format="ICO", sizes=icon_sizes)
    print(f"Icon generated: {path_ico}")


if __name__ == "__main__":
    try:
        make_icon()
    except Exception as e:
        print("Failed to generate icon:", e)
