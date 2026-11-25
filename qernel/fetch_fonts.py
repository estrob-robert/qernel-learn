"""Fetch the fonts Qernel Learn serves itself, from Google Fonts, once.

A customer's site never loads a font from Google while it runs (the learner's
IP would go there), so the woff2 files live in lms/public/fonts and are served
from our own domain. Run this when the list below changes, from the repo root:

    python qernel/fetch_fonts.py

It writes lms/public/fonts/<id>/*.woff2 and lms/public/fonts/fonts.json, which
lms/qernel_design.py reads. Only the latin and latin-ext subsets are kept, which
cover Norwegian and the rest of Western and Central Europe. All fonts here are
under the SIL Open Font License, which allows serving them.
"""

import json
import re
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "lms" / "public" / "fonts"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SUBSETS = ("latin", "latin-ext")

# id: (Google family query, category, fallback stack)
FONTS = {
	"archivo": ("Archivo:wdth,wght@62..125,400..900", "sans", "Arial, sans-serif"),
	"bodoni-moda": (
		"Bodoni+Moda:ital,opsz,wght@0,6..96,400..700;1,6..96,400..700",
		"serif",
		"Georgia, serif",
	),
	"libre-caslon-display": ("Libre+Caslon+Display", "serif", "Georgia, serif"),
	"source-serif-4": (
		"Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400..700",
		"serif",
		"Georgia, serif",
	),
	"schibsted-grotesk": (
		"Schibsted+Grotesk:ital,wght@0,400..900;1,400..900",
		"sans",
		"system-ui, sans-serif",
	),
	"inter": ("Inter:ital,opsz,wght@0,14..32,400..800;1,14..32,400..800", "sans", "system-ui, sans-serif"),
	"manrope": ("Manrope:wght@400..800", "sans", "system-ui, sans-serif"),
	"montserrat": ("Montserrat:ital,wght@0,400..900;1,400..900", "sans", "system-ui, sans-serif"),
	"lora": ("Lora:ital,wght@0,400..700;1,400..700", "serif", "Georgia, serif"),
	"playfair-display": ("Playfair+Display:ital,wght@0,400..900;1,400..900", "serif", "Georgia, serif"),
	"eb-garamond": ("EB+Garamond:ital,wght@0,400..800;1,400..800", "serif", "Georgia, serif"),
}

BLOCK = re.compile(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{(.*?)\}", re.S)


def _get(url: str) -> bytes:
	request = urllib.request.Request(url, headers={"User-Agent": UA})
	with urllib.request.urlopen(request, timeout=30) as response:
		return response.read()


def _prop(block: str, name: str) -> str:
	match = re.search(rf"{name}\s*:\s*([^;]+);", block)
	return match.group(1).strip() if match else ""


def fetch(font_id: str, query: str, category: str, fallback: str) -> dict:
	css = _get(f"https://fonts.googleapis.com/css2?family={query}&display=swap").decode()
	folder = ROOT / font_id
	if folder.exists():
		shutil.rmtree(folder)
	folder.mkdir(parents=True)
	family = ""
	files = []
	for subset, block in BLOCK.findall(css):
		if subset not in SUBSETS:
			continue
		family = _prop(block, "font-family").strip("'\"")
		style = _prop(block, "font-style") or "normal"
		src = re.search(r"url\((https://[^)]+\.woff2)\)", block)
		if not src:
			continue
		name = f"{font_id}-{style}-{subset}"
		if any(f["file"].endswith(f"/{name}.woff2") for f in files):
			name += f"-{len(files)}"
		(folder / f"{name}.woff2").write_bytes(_get(src.group(1)))
		files.append(
			{
				"file": f"fonts/{font_id}/{name}.woff2",
				"style": style,
				"weight": _prop(block, "font-weight") or "400",
				"stretch": _prop(block, "font-stretch") or "",
				"unicode_range": _prop(block, "unicode-range"),
			}
		)
	if not files:
		sys.exit(f"{font_id}: Google Fonts returned no latin woff2 files")
	return {"id": font_id, "family": family, "category": category, "fallback": fallback, "files": files}


def main():
	manifest = [fetch(font_id, *spec) for font_id, spec in FONTS.items()]
	(ROOT / "fonts.json").write_text(
		json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
	)
	for font in manifest:
		print(font["id"], font["family"], len(font["files"]), "files")


if __name__ == "__main__":
	main()
