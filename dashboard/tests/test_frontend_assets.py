from __future__ import annotations

import json
import unittest
from pathlib import Path

from dashboard.tools.build_dashboard import (
    BUNDLE_PATH,
    STYLE_PATH,
    build_bundle_text,
    build_style_text,
)

DASHBOARD_ROOT = Path(__file__).parents[1]


class DashboardAssetTests(unittest.TestCase):
    def test_manifest_uses_documented_local_dashboard_paths(self) -> None:
        manifest = json.loads((DASHBOARD_ROOT / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "hermes-affect")
        self.assertEqual(manifest["entry"], "dist/index.js")
        self.assertEqual(manifest["css"], "dist/style.css")
        self.assertEqual(manifest["api"], "plugin_api.py")
        self.assertEqual(
            set(manifest),
            {"name", "label", "description", "icon", "version", "tab", "entry", "css", "api"},
        )

    def test_generated_assets_match_layered_sources(self) -> None:
        self.assertEqual(BUNDLE_PATH.read_text(encoding="utf-8"), build_bundle_text())
        self.assertEqual(STYLE_PATH.read_text(encoding="utf-8"), build_style_text())

    def test_bundle_uses_sdk_and_avoids_unsafe_html(self) -> None:
        bundle = build_bundle_text()

        self.assertIn("window.__HERMES_PLUGIN_SDK__", bundle)
        self.assertIn('registry.register("hermes-affect"', bundle)
        self.assertNotIn("innerHTML", bundle)
        self.assertNotIn("dangerouslySetInnerHTML", bundle)
        self.assertNotIn("WebSocket", bundle)


if __name__ == "__main__":
    unittest.main()
