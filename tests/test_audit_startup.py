import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import core.config as config_module


class StartupAuditTests(unittest.TestCase):
    def test_config_save_preserves_an_existing_temporary_file(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "config.json"
            unrelated = Path(root) / "config.json.tmp"
            unrelated.write_bytes(b"existing pending settings")
            with patch.object(config_module, "CONFIG_FILE", path):
                config = config_module.Config()
                config.save()
            self.assertEqual(unrelated.read_bytes(), b"existing pending settings")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), config._data)

    def test_invalid_config_shapes_and_types_fall_back_to_defaults(self):
        invalid = [[], None, "invalid", 3,
            {"scraping_delay": 10 ** 400, "splitter_sizes": [2 ** 60, 100]},
            {"ffprobe_path": None,
            "scraping_delay": "fast", "last_root_folder": [],
            "window_geometry": "invalid", "splitter_sizes": ["bad"],
            "scrapers_enabled": {"audible": "yes"}}]
        with TemporaryDirectory() as root:
            config_path = Path(root) / "config.json"
            for saved in invalid:
                with self.subTest(saved=saved):
                    config_path.write_text(json.dumps(saved), encoding="utf-8")
                    with patch.object(config_module, "CONFIG_FILE", config_path):
                        config = config_module.Config()
                    for key in ("ffprobe_path", "scraping_delay", "last_root_folder",
                                "window_geometry", "splitter_sizes", "scrapers_enabled"):
                        self.assertEqual(config.get(key), config_module.DEFAULT_CONFIG[key])

    @unittest.skipUnless(os.name == "nt", "Windows portable build script")
    def test_portable_build_stops_when_dependency_install_fails(self):
        root = Path(__file__).resolve().parent.parent
        # where.exe exits nonzero on the Python arguments; it cannot install/build.
        with TemporaryDirectory() as temp:
            scratch = Path(temp)
            python_stub = scratch / ".venv" / "Scripts" / "python.exe"
            python_stub.parent.mkdir(parents=True)
            shutil.copy2(Path(os.environ["SystemRoot"]) / "System32" / "where.exe", python_stub)
            shutil.copy2(root / "build-portable.ps1", scratch)
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                 str(scratch / "build-portable.ps1")],
                capture_output=True, text=True, timeout=30,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Done. Portable build:", result.stdout)
        self.assertNotIn("Building portable app", result.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows portable build script")
    def test_portable_build_refuses_to_overwrite_saved_user_data(self):
        root = Path(__file__).resolve().parent.parent
        with TemporaryDirectory() as temp:
            scratch = Path(temp)
            python_stub = scratch / ".venv" / "Scripts" / "python.exe"
            python_stub.parent.mkdir(parents=True)
            shutil.copy2(Path(os.environ["SystemRoot"]) / "System32" / "where.exe", python_stub)
            shutil.copy2(root / "build-portable.ps1", scratch)
            data = scratch / "dist" / "AudioBook-Manager" / "data"
            data.mkdir(parents=True)
            settings = data / "config.json"
            settings.write_bytes(b"user settings")
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                 str(scratch / "build-portable.ps1")],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(settings.read_bytes(), b"user settings")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("saved data", result.stderr)
        self.assertNotIn("Installing build dependencies", result.stdout)


if __name__ == "__main__":
    unittest.main()
