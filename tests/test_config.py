import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import core.config as config_module


class ConfigTests(unittest.TestCase):
    def test_partial_scraper_settings_are_merged_with_defaults(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "config.json"
            path.write_text(json.dumps({"scrapers_enabled": {"audible": False}}))
            with patch.object(config_module, "CONFIG_FILE", path):
                config = config_module.Config()

        enabled = config.get("scrapers_enabled")
        self.assertFalse(enabled["audible"])
        self.assertIn("audible_api", enabled)
        self.assertIn("goodreads", enabled)


if __name__ == "__main__":
    unittest.main()
