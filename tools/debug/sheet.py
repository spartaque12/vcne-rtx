# contact sheet of a run's screenshots: python sheet.py <tag> [cols=4]  -> sheet_<tag>.png
import sys, glob, os
from PIL import Image, ImageDraw
tag = sys.argv[1]; cols = int(sys.argv[2]) if len(sys.argv) > 2 else 4
d = os.path.dirname(os.path.abspath(__file__))
fs = sorted(glob.glob(os.path.join(d, 'shot_%s_*.png' % tag)))
w, h = 480, 270
rows = (len(fs) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w, rows * h))
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB').resize((w, h))
    ImageDraw.Draw(im).text((4, 4), os.path.basename(f)[5:-4], fill=(255, 255, 0))
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(os.path.join(d, 'sheet_%s.png' % tag)); print(len(fs), 'shots')
