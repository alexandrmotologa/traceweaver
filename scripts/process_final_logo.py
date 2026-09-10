import os
import base64
from PIL import Image, ImageDraw

def process_logo():
    src = r"C:\Users\alexander\.gemini\antigravity-ide\brain\045b334f-397d-46c6-b7b0-21cd830a547d\traceweaver_logo_concept_b_1789073683794.jpg"
    im = Image.open(src).convert("RGBA")

    # Perfectly centered square crop around the squircle icon
    cx, cy = 505, 450
    half = 370
    box = (cx - half, cy - half, cx + half, cy + half)
    cropped = im.crop(box)
    logo_1024 = cropped.resize((1024, 1024), Image.LANCZOS)

    out_dir = r"C:\Users\alexander\.gemini\antigravity-ide\scratch\traceweaver\docs\images"
    os.makedirs(out_dir, exist_ok=True)

    # Primary logo files
    logo_1024.save(os.path.join(out_dir, "logo.png"), "PNG")
    logo_1024.save(os.path.join(out_dir, "logo-1024.png"), "PNG")

    # Scaled icons
    logo_256 = logo_1024.resize((256, 256), Image.LANCZOS)
    logo_256.save(os.path.join(out_dir, "logo-256.png"), "PNG")

    logo_128 = logo_1024.resize((128, 128), Image.LANCZOS)
    logo_128.save(os.path.join(out_dir, "logo-128.png"), "PNG")

    logo_32 = logo_1024.resize((32, 32), Image.LANCZOS)
    logo_32.save(os.path.join(out_dir, "logo-32.png"), "PNG")

    # Create transparent squircle version (masking the outer background outside the squircle)
    # The squircle border in the 1024 image starts around x=65, y=55 and ends around x=955, y=965
    # Let's create a rounded rectangle mask with smooth antialiased corners
    mask = Image.new("L", (1024, 1024), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(65, 55), (955, 965)], radius=220, fill=255)

    transparent_logo = logo_1024.copy()
    transparent_logo.putalpha(mask)
    transparent_logo.save(os.path.join(out_dir, "logo-transparent.png"), "PNG")

    # Also generate logo.svg containing the high-res PNG embedded for vector-compatible pipelines
    with open(os.path.join(out_dir, "logo.png"), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <image href="data:image/png;base64,{b64}" width="1024" height="1024" />
</svg>'''
    with open(os.path.join(out_dir, "logo.svg"), "w", encoding="utf-8") as f:
        f.write(svg_content)

    print("All production assets generated successfully.")

if __name__ == "__main__":
    process_logo()
