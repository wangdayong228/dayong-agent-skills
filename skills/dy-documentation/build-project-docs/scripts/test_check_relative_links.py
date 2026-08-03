from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_relative_links.py")
SPEC = importlib.util.spec_from_file_location("check_relative_links", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
check_relative_links = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_relative_links)


class DestinationTests(unittest.TestCase):
    def test_detects_link_with_nested_brackets_in_label(self) -> None:
        self.assertEqual(
            [(1, "missing.md")],
            check_relative_links.destinations("[outer [inner]](missing.md)"),
        )

    def test_detects_link_with_escaped_closing_bracket_in_label(self) -> None:
        self.assertEqual(
            [(1, "missing.md")],
            check_relative_links.destinations(r"[escaped \] label](missing.md)"),
        )

    def test_ignores_links_inside_inline_code(self) -> None:
        self.assertEqual(
            [],
            check_relative_links.destinations("Use `[example](missing.md)` literally."),
        )

    def test_excludes_parenthesized_link_title_from_destination(self) -> None:
        self.assertEqual(
            [(1, "guide.md")],
            check_relative_links.destinations("[guide](guide.md (Read the guide))"),
        )

    def test_detects_unquoted_html_href_and_src(self) -> None:
        self.assertEqual(
            [(1, "guide.md"), (2, "image.png")],
            check_relative_links.destinations(
                "<a href=guide.md>Guide</a>\n<img src=image.png>"
            ),
        )


class AnchorTests(unittest.TestCase):
    def test_setext_heading_generates_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target.md"
            path.write_text("Setext heading\n==============\n", encoding="utf-8")

            self.assertIn("setext-heading", check_relative_links.anchors(path))

    def test_anchor_suffix_skips_slug_already_used_by_heading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target.md"
            path.write_text("# Foo\n# Foo-1\n# Foo\n", encoding="utf-8")

            self.assertEqual(
                {"foo", "foo-1", "foo-2"}, check_relative_links.anchors(path)
            )


class CheckFileTests(unittest.TestCase):
    def test_any_nonempty_uri_scheme_is_external(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "README.md"
            source.write_text("[resource](custom:missing-item)\n", encoding="utf-8")

            self.assertEqual([], check_relative_links.check_file(root, source))


if __name__ == "__main__":
    unittest.main()
