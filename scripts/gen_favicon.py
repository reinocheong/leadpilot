#!/usr/bin/env python3
"""Generate favicon + Apple Touch Icon from STP logo"""
import sys
from PIL import Image

src = sys.argv[1]
outdir = sys.argv[2]

img = Image.open(src)
# Ensure it's square
size = min(img.size)
img = img.crop(((img.width - size)//2, (img.height - size)//2,
                (img.width + size)//2, (img.height + size)//2))

# PNG favicon (16, 32, 48, 64, 96)
for s in [16, 32, 48, 64, 96]:
    resized = img.resize((s, s), Image.LANCZOS)
    resized.save(f"{outdir}/favicon-{s}.png")

# 180x180 Apple Touch Icon
apple = img.resize((180, 180), Image.LANCZOS)
apple.save(f"{outdir}/apple-touch-icon.png")

# 192x192 Android Chrome
android = img.resize((192, 192), Image.LANCZOS)
android.save(f"{outdir}/android-chrome-192x192.png")

# 512x512 Android Chrome
android_big = img.resize((512, 512), Image.LANCZOS)
android_big.save(f"{outdir}/android-chrome-512x512.png")

# Create .ico with multiple sizes
ico_sizes = [16, 32, 48, 64]
ico_images = [img.resize((s, s), Image.LANCZOS) for s in ico_sizes]
ico_images[0].save(f"{outdir}/favicon.ico", format='ICO', sizes=[(s,s) for s in ico_sizes])

print("✅ Favicons generated in", outdir)
