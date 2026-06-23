import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from core.chapters import build_ffmetadata, probe_chapters, rewrite_chapters


class ChapterMetadataTests(unittest.TestCase):
    def test_titles_are_escaped_for_ffmetadata(self):
        chapters = [{"start": 0, "end": 1000, "time_base": "1/1000"}]
        metadata = build_ffmetadata(chapters, ["Part = 1; #intro\\draft\ncontinued"])

        self.assertIn(r"title=Part \= 1\; \#intro\\draft continued", metadata)

    @patch("core.chapters.shutil.which", return_value=None)
    def test_missing_ffprobe_has_actionable_error(self, _which):
        with self.assertRaisesRegex(RuntimeError, "README"):
            probe_chapters("book.m4b")

    @patch("core.chapters.probe_chapters", return_value=[{"start": 0, "end": 1}])
    @patch("core.chapters.MP4")
    @patch("core.chapters.media_tools_available", return_value=(True, ""))
    def test_rewrite_replaces_original_only_after_valid_output(self, _tools, _mp4, _probe):
        with TemporaryDirectory() as root:
            source = Path(root) / "book.m4b"
            source.write_bytes(b"original")

            def fake_run(command, **_kwargs):
                Path(command[-1]).write_bytes(b"rewritten")
                return Mock(returncode=0, stderr="")

            with patch("core.chapters.subprocess.run", side_effect=fake_run):
                self.assertTrue(rewrite_chapters(
                    str(source), [{"start": 0, "end": 1}], ["Chapter 1"]
                ))

            self.assertEqual(source.read_bytes(), b"rewritten")


if __name__ == "__main__":
    unittest.main()
