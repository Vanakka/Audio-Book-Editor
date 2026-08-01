import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.media_tools import resolve_tool, set_tool_paths


class MediaToolResolutionTests(unittest.TestCase):
    def setUp(self):
        set_tool_paths("", "")

    def test_explicit_override_is_used(self):
        with TemporaryDirectory() as root:
            ffprobe = Path(root) / "ffprobe.exe"
            ffprobe.write_bytes(b"")
            set_tool_paths(str(ffprobe), "")
            with patch("core.media_tools.shutil.which", return_value=None), \
                    patch("core.media_tools._candidate_paths", return_value=[]):
                self.assertEqual(resolve_tool("ffprobe"), str(ffprobe))

    def test_winget_links_candidate_is_discovered(self):
        with TemporaryDirectory() as root:
            ffprobe = Path(root) / "ffprobe.exe"
            ffprobe.write_bytes(b"")
            with patch("core.media_tools.shutil.which", return_value=None), \
                    patch("core.media_tools._candidate_paths", return_value=[ffprobe]):
                self.assertEqual(resolve_tool("ffprobe"), str(ffprobe.resolve()))


if __name__ == "__main__":
    unittest.main()