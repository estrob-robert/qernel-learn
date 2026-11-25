"""lms/qernel_color.py: any colour a customer picks must stay readable.

Plain unittest, no site needed: python -m unittest lms.tests.test_qernel_color
"""

import unittest

from lms.qernel_color import AA, contrast, derive, parse_hex, readable_on, text_on

PAGE_LIGHT = "#f8f3f5"
PAGE_DARK = "#170f13"
TEXT_DARK = "#2a1822"
TEXT_LIGHT = "#f8f1f4"


class TestQernelColor(unittest.TestCase):
	def test_parse_rejects_anything_but_six_hex_digits(self):
		self.assertEqual(parse_hex("#5A1E46"), (0x5A, 0x1E, 0x46))
		self.assertEqual(parse_hex("5a1e46"), (0x5A, 0x1E, 0x46))
		for bad in ("", "#fff", "red", "#5A1E4G", "#5A1E46;}body{", None):
			with self.assertRaises(ValueError):
				parse_hex(bad)

	def test_dark_colour_is_kept_as_text_on_light_page(self):
		colour, moved = readable_on(PAGE_LIGHT, "#5a1e46")
		self.assertEqual(colour, "#5a1e46")
		self.assertFalse(moved)

	def test_light_colour_is_darkened_until_readable(self):
		colour, moved = readable_on(PAGE_LIGHT, "#f2d64b")
		self.assertTrue(moved)
		self.assertGreaterEqual(contrast(parse_hex(PAGE_LIGHT), parse_hex(colour)), AA)

	def test_dark_colour_is_lightened_on_dark_page(self):
		colour, moved = readable_on(PAGE_DARK, "#1f3a5f")
		self.assertTrue(moved)
		self.assertGreaterEqual(contrast(parse_hex(PAGE_DARK), parse_hex(colour)), AA)

	def test_text_on_fill_picks_the_readable_one(self):
		self.assertEqual(text_on("#5a1e46", TEXT_LIGHT, TEXT_DARK), TEXT_LIGHT)
		self.assertEqual(text_on("#f2d64b", TEXT_LIGHT, TEXT_DARK), TEXT_DARK)

	def test_every_derived_pair_is_readable(self):
		for primary in ("#5a1e46", "#f2d64b", "#ffffff", "#000000", "#ff6b35", "#1f5134", "#7fd3ff"):
			colours = derive(primary, PAGE_LIGHT, PAGE_DARK, TEXT_DARK, TEXT_LIGHT)
			for theme, page in (("light", PAGE_LIGHT), ("dark", PAGE_DARK)):
				c = colours[theme]
				self.assertGreaterEqual(
					contrast(parse_hex(page), parse_hex(c["accent"])), AA, f"{primary} accent {theme}"
				)
				# Text on a filled surface: large type and buttons, so 3:1 is the
				# floor even for a mid-tone the customer insists on.
				self.assertGreaterEqual(
					contrast(parse_hex(c["block"]), parse_hex(c["on_block"])), 3, f"{primary} block {theme}"
				)


if __name__ == "__main__":
	unittest.main()
