import errno
import subprocess
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm
from PIL import Image

from core.chapters import probe_chapters, rewrite_chapters
from core.media_tools import resolve_tool
from core.metadata import _prepare_cover_bytes, populate_book_from_tags, write_cover, write_tags
from core.models import AudioBook
from core.renamer import execute_renames, execute_sort, preview_sort
from core import renamer


class CoreAuditSafetyTests(unittest.TestCase):
    def test_sort_rechecks_destination_created_after_preview(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source" / "book.m4b"
            source.parent.mkdir()
            source.write_bytes(b"source audio")
            book = AudioBook(str(source), str(source.parent), series="Series")
            previews = preview_sort([book], str(root / "destination"), {"Series": "Ongoing"})
            self.assertFalse(previews[0][3])
            destination = Path(previews[0][2])
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"existing destination audio")

            self.assertEqual(execute_sort(previews), (0, 1))

            self.assertEqual(source.read_bytes(), b"source audio")
            self.assertEqual(destination.read_bytes(), b"existing destination audio")
            self.assertEqual(book.file_path, str(source))

    def test_folder_rename_updates_every_book_in_shared_source_folder(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            folder = root / "Old folder"
            folder.mkdir()
            books = []
            for filename in ("first.m4b", "second.m4b"):
                audio = folder / filename
                audio.write_bytes(filename.encode())
                books.append(AudioBook(str(audio), str(folder), series="New series"))

            self.assertEqual(execute_renames(books, "{series}"), (1, 0))

            for book in books:
                self.assertEqual(Path(book.folder_path), root / "New series")
                self.assertTrue(Path(book.file_path).exists())

    def test_folder_rename_rejects_inconsistent_names_for_shared_folder(self):
        with TemporaryDirectory() as root:
            folder = Path(root) / "Shared folder"
            folder.mkdir()
            books = []
            for title in ("First title", "Second title"):
                audio = folder / f"{title}.m4b"
                audio.write_bytes(title.encode())
                books.append(AudioBook(str(audio), str(folder), title=title))

            self.assertTrue(all(preview[3] for preview in renamer.preview_renames(books, "{title}")))
            self.assertEqual(execute_renames(books, "{title}"), (0, 1))
            self.assertTrue(all(Path(book.file_path).exists() for book in books))
            self.assertTrue(folder.exists())

    def test_sort_cross_volume_preserves_audio_and_companion_cue(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source" / "book.m4b"
            source.parent.mkdir()
            source.write_bytes(b"source audio")
            cue = source.with_suffix(".cue")
            cue.write_bytes(b"source cue")
            book = AudioBook(str(source), str(source.parent), series="Series")
            previews = preview_sort([book], str(root / "destination"), {"Series": "Complete"})
            destination = Path(previews[0][2])
            with patch("core.renamer.os.link", side_effect=OSError(errno.EXDEV, "Cross-device link")):
                self.assertEqual(execute_sort(previews), (1, 0))

            self.assertFalse(source.exists())
            self.assertFalse(cue.exists())
            self.assertEqual(destination.read_bytes(), b"source audio")
            self.assertEqual(destination.with_suffix(".cue").read_bytes(), b"source cue")
            self.assertEqual(book.file_path, str(destination))

    def test_sort_cross_volume_collision_does_not_clobber_destination(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source" / "book.m4b"
            source.parent.mkdir()
            source.write_bytes(b"source audio")
            book = AudioBook(str(source), str(source.parent), series="Series")
            previews = preview_sort([book], str(root / "destination"), {"Series": "Ongoing"})
            destination = Path(previews[0][2])
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"existing destination audio")
            with patch("core.renamer.os.link", side_effect=OSError(errno.EXDEV, "Cross-device link")):
                self.assertEqual(execute_sort(previews), (0, 1))

            self.assertEqual(source.read_bytes(), b"source audio")
            self.assertEqual(destination.read_bytes(), b"existing destination audio")

    def test_sort_rolls_back_audio_when_cue_destination_appears_during_move(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source" / "book.m4b"
            source.parent.mkdir()
            source.write_bytes(b"source audio")
            cue = source.with_suffix(".cue")
            cue.write_bytes(b"source cue")
            book = AudioBook(str(source), str(source.parent), series="Series")
            previews = preview_sort([book], str(root / "destination"), {"Series": "Ongoing"})
            destination = Path(previews[0][2])
            move = renamer._move_no_overwrite

            def move_with_late_cue(source_path, destination_path):
                move(source_path, destination_path)
                if source_path == str(source):
                    destination.with_suffix(".cue").write_bytes(b"unrelated destination cue")

            with patch("core.renamer._move_no_overwrite", side_effect=move_with_late_cue):
                self.assertEqual(execute_sort(previews), (0, 1))

            self.assertEqual(source.read_bytes(), b"source audio")
            self.assertEqual(cue.read_bytes(), b"source cue")
            self.assertFalse(destination.exists())
            self.assertEqual(destination.with_suffix(".cue").read_bytes(), b"unrelated destination cue")
            self.assertEqual(book.file_path, str(source))

    def test_sort_incomplete_cross_volume_copy_preserves_source_and_cleans_output(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / "source" / "book.m4b"
            source.parent.mkdir()
            source.write_bytes(b"source audio")
            book = AudioBook(str(source), str(source.parent), series="Series")
            previews = preview_sort([book], str(root / "destination"), {"Series": "Ongoing"})
            destination = Path(previews[0][2])

            def failed_copy(_source, output):
                output.write(b"partial")
                raise OSError("synthetic disk full")

            with patch("core.renamer.os.link", side_effect=OSError(errno.EXDEV, "Cross-device link")), \
                    patch("core.renamer.shutil.copyfileobj", side_effect=failed_copy):
                self.assertEqual(execute_sort(previews), (0, 1))

            self.assertEqual(source.read_bytes(), b"source audio")
            self.assertFalse(destination.exists())
            self.assertEqual(book.file_path, str(source))

    def test_chapter_failure_preserves_preexisting_similar_temporary_file(self):
        with TemporaryDirectory() as root:
            source = Path(root) / "book.m4b"
            source.write_bytes(b"original audio")
            unrelated_temp = Path(str(source) + ".tmp.m4b")
            unrelated_temp.write_bytes(b"unrelated audio")
            with patch("core.chapters.media_tools_available", return_value=(True, "")), \
                    patch("core.chapters.MP4", return_value=Mock(tags={})), \
                    patch("core.chapters._probe_media", return_value={"streams": []}), \
                    patch("core.chapters.resolve_tool", return_value="ffmpeg"), \
                    patch("core.chapters.subprocess.run", return_value=Mock(returncode=1, stderr="synthetic failure")):
                with self.assertRaisesRegex(RuntimeError, "ffmpeg failed"):
                    rewrite_chapters(str(source), [{"start": 0, "end": 1000}], ["One"])

            self.assertEqual(source.read_bytes(), b"original audio")
            self.assertTrue(unrelated_temp.exists())
            self.assertEqual(unrelated_temp.read_bytes(), b"unrelated audio")
            self.assertEqual(set(Path(root).iterdir()), {source, unrelated_temp})

    def test_clearing_metadata_removes_aliases_that_would_reappear_on_read(self):
        fake = Mock()
        fake.tags = {
            "\xa9nam": ["Title"],
            "\xa9wrt": ["Old narrator"],
            "----:com.apple.iTunes:PUBLISHER": [b"Old publisher"],
            "----:com.apple.iTunes:SUBTITLE": [b"Old subtitle"],
            "----:com.apple.iTunes:LANGUAGE": [b"Old language"],
            "----:com.apple.iTunes:SERIES": [b"Old series"],
            "----:com.apple.iTunes:PART": [b"3"],
            "----:com.apple.iTunes:AUDIBLE_ASIN": [b"B012345678"],
            "unrelated": ["Keep me"],
        }
        book = AudioBook("synthetic.m4b", ".", title="Title")
        with patch("core.metadata.MP4", return_value=fake):
            self.assertTrue(write_tags(book))
            self.assertTrue(populate_book_from_tags(book))

        for field in ("narrator", "publisher", "subtitle", "language", "series", "series_number", "asin_tag"):
            with self.subTest(field=field):
                self.assertEqual(getattr(book, field), "")
        self.assertEqual(fake.tags["unrelated"], ["Keep me"])

    def test_cover_pixel_cap_is_checked_before_decoding(self):
        image = Mock(width=8000, height=8000)
        image_context = Mock()
        image_context.__enter__ = Mock(return_value=image)
        image_context.__exit__ = Mock(return_value=False)
        with patch("core.metadata.Image.open", return_value=image_context):
            with self.assertRaisesRegex(ValueError, "too many pixels"):
                _prepare_cover_bytes(b"synthetic image header", "jpeg")
        image.load.assert_not_called()

    def test_cover_rejects_pillow_decompression_bomb_without_opening_audio(self):
        book = AudioBook("synthetic.m4b", ".")
        with patch("core.metadata.Image.open", side_effect=Image.DecompressionBombError("oversized image")), \
                patch("core.metadata.MP4") as open_audio:
            self.assertFalse(write_cover(book, b"synthetic image header", "jpeg"))
        open_audio.assert_not_called()

    def test_real_chapter_rewrite_preserves_tags_cover_audio_and_timings(self):
        ffmpeg = resolve_tool("ffmpeg")
        ffprobe = resolve_tool("ffprobe")
        if not ffmpeg or not ffprobe:
            self.skipTest("Real chapter integration requires FFmpeg and FFprobe")

        with TemporaryDirectory() as root:
            root = Path(root)
            audio = root / "synthetic.m4b"
            metadata = root / "chapters.ffmetadata"
            metadata.write_text(
                ";FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=1000\ntitle=Old one\n"
                "[CHAPTER]\nTIMEBASE=1/1000\nSTART=1000\nEND=2000\ntitle=Old two\n",
                encoding="utf-8",
            )
            subprocess.run([
                ffmpeg, "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-i", str(metadata), "-t", "2", "-map", "0:a", "-map_metadata", "1",
                "-map_chapters", "1", "-c:a", "aac", "-b:a", "32k", str(audio),
            ], check=True, capture_output=True, timeout=15)
            original = MP4(audio)
            original.tags.update({
                "\xa9nam": ["Synthetic title"],
                "\xa9nrt": ["Synthetic narrator"],
                "\xa9pub": ["Synthetic publisher"],
                "asin": ["B012345678"],
                "CDEK": ["B012345678"],
                "----:com.pilabor.tone:SERIES": [MP4FreeForm(b"Synthetic series")],
            })
            cover = BytesIO()
            Image.new("RGB", (5, 5), "red").save(cover, format="PNG")
            original.tags["covr"] = [MP4Cover(cover.getvalue(), imageformat=MP4Cover.FORMAT_PNG)]
            original.save()
            before_tags = dict(MP4(audio).tags)
            before_chapters = probe_chapters(str(audio))

            def audio_packet_hash():
                return subprocess.run([
                    ffmpeg, "-v", "error", "-i", str(audio), "-map", "0:a:0", "-c:a", "copy",
                    "-f", "hash", "-hash", "sha256", "-",
                ], check=True, capture_output=True, text=True, timeout=15).stdout.strip()

            before_hash = audio_packet_hash()
            titles = ["New = one; #intro", "New two"]
            self.assertTrue(rewrite_chapters(str(audio), before_chapters, titles))

            after_tags = dict(MP4(audio).tags)
            self.assertEqual(after_tags, before_tags)
            self.assertEqual(after_tags["covr"][0].imageformat, before_tags["covr"][0].imageformat)
            self.assertEqual(audio_packet_hash(), before_hash)
            after_chapters = probe_chapters(str(audio))
            self.assertEqual([chapter["tags"]["title"] for chapter in after_chapters], titles)
            self.assertEqual(
                [(chapter["start_time"], chapter["end_time"]) for chapter in after_chapters],
                [(chapter["start_time"], chapter["end_time"]) for chapter in before_chapters],
            )


if __name__ == "__main__":
    unittest.main()
