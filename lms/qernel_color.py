"""Qernel Learn: the colours a template derives from the customer's one colour.

A customer picks a single primary colour in Qernel's design guide. Everything
else (the text on a coloured surface, the colour used for text on the page,
the surface in dark mode) is worked out here, so any colour a customer picks
stays readable (WCAG AA, 4.5:1 for text). No Frappe import, so it can be tested
anywhere.
"""

import re

HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
AA = 4.5


def parse_hex(value: str) -> tuple[int, int, int]:
	match = HEX.match((value or "").strip())
	if not match:
		raise ValueError(f"not a #rrggbb colour: {value!r}")
	digits = match.group(1)
	return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb: tuple[int, int, int]) -> str:
	return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def luminance(rgb: tuple[int, int, int]) -> float:
	def channel(c: float) -> float:
		c /= 255
		return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

	r, g, b = (channel(c) for c in rgb)
	return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
	la, lb = sorted((luminance(a), luminance(b)), reverse=True)
	return (la + 0.05) / (lb + 0.05)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
	"""`amount` of b into a, 0 to 1."""
	return tuple(round(x + (y - x) * amount) for x, y in zip(a, b, strict=True))


def readable_on(background: str, colour: str, minimum: float = AA) -> tuple[str, bool]:
	"""`colour` as text on `background`, moved toward black or white (whichever
	side of the background it is not on) just far enough to be read. Returns the
	colour and whether it had to move."""
	bg, fg = parse_hex(background), parse_hex(colour)
	if contrast(bg, fg) >= minimum:
		return to_hex(fg), False
	toward = BLACK if luminance(bg) > 0.18 else WHITE
	for step in range(1, 21):
		moved = mix(fg, toward, step / 20)
		if contrast(bg, moved) >= minimum:
			return to_hex(moved), True
	return to_hex(toward), True


def text_on(fill: str, light: str, dark: str) -> str:
	"""Whichever of the template's light and dark text reads best on `fill`."""
	surface = parse_hex(fill)
	return light if contrast(surface, parse_hex(light)) >= contrast(surface, parse_hex(dark)) else dark


def derive(primary: str, page_light: str, page_dark: str, text_dark: str, text_light: str) -> dict:
	"""The colour variables a template paints with, for both themes.

	`page_light` and `page_dark` are the template's page backgrounds;
	`text_dark` and `text_light` its dark and light text colours.
	block: a surface in the customer's colour. on_block: text on that surface.
	accent: the customer's colour used as text or a thin mark on the page.
	In dark mode the surface is lifted a little, so it does not sink into the
	page."""
	base = parse_hex(primary)
	block_light = to_hex(base)
	block_dark = to_hex(mix(base, WHITE, 0.12))
	accent_light, moved_light = readable_on(page_light, block_light)
	accent_dark, moved_dark = readable_on(page_dark, block_dark)
	return {
		"light": {
			"block": block_light,
			"on_block": text_on(block_light, text_light, text_dark),
			"accent": accent_light,
		},
		"dark": {
			"block": block_dark,
			"on_block": text_on(block_dark, text_light, text_dark),
			"accent": accent_dark,
		},
		"adjusted": {"light": moved_light, "dark": moved_dark},
	}
