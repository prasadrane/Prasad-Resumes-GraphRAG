"""
test_web_static_structure.py — TDD test suite validating the modular frontend structure.
Ensures all modular JS files, CSS partials, and index.html wiring meet production standards.
"""

import unittest
from pathlib import Path
from src.config import WEB_STATIC_DIR


class TestWebStaticStructure(unittest.TestCase):
    def setUp(self):
        self.static_dir = Path(WEB_STATIC_DIR)
        self.js_dir = self.static_dir / "js"
        self.css_dir = self.static_dir / "css"

    def test_core_js_modules_exist_and_export(self):
        """Verify all core JS infrastructure modules exist and export expected symbols."""
        core_files = {
            "logger.js": ["Logger", "export"],
            "bus.js": ["EventBus", "export"],
            "utils.js": ["Utils", "export"],
            "api.js": ["ApiClient", "export"],
            "devtools.js": ["DevTools", "export"],
        }
        core_dir = self.js_dir / "core"
        self.assertTrue(core_dir.is_dir(), f"Missing directory: {core_dir}")

        for filename, expected_tokens in core_files.items():
            filepath = core_dir / filename
            self.assertTrue(filepath.is_file(), f"Missing core module: {filepath}")
            content = filepath.read_text(encoding="utf-8")
            self.assertGreater(len(content.strip()), 50, f"Module {filename} is too short or empty")
            for token in expected_tokens:
                self.assertIn(token, content, f"Module {filename} missing token: {token}")

    def test_controller_js_modules_exist_and_export(self):
        """Verify all feature controllers exist and export expected symbols."""
        controllers = {
            "navigation.js": ["NavigationController", "export"],
            "default_resume.js": ["DefaultResumeController", "export"],
            "generator.js": ["GeneratorController", "export"],
            "pipeline.js": ["PipelineController", "export"],
            "preview.js": ["PreviewDrawerController", "export"],
            "cover_letter.js": ["CoverLetterController", "export"],
            "prep.js": ["InterviewPrepController", "export"],
            "graph_explorer.js": ["GraphExplorerController", "export"],
            "chatbot.js": ["ChatbotController", "export"],
            "search.js": ["FTS5SearchController", "export"],
            "diagnostics.js": ["DiagnosticsController", "export"],
        }
        ctrl_dir = self.js_dir / "controllers"
        self.assertTrue(ctrl_dir.is_dir(), f"Missing directory: {ctrl_dir}")

        for filename, expected_tokens in controllers.items():
            filepath = ctrl_dir / filename
            self.assertTrue(filepath.is_file(), f"Missing controller: {filepath}")
            content = filepath.read_text(encoding="utf-8")
            self.assertGreater(len(content.strip()), 50, f"Controller {filename} is too short or empty")
            for token in expected_tokens:
                self.assertIn(token, content, f"Controller {filename} missing token: {token}")

    def test_main_js_entry_point(self):
        """Verify main.js imports all controllers and bootstraps the application."""
        main_file = self.js_dir / "main.js"
        self.assertTrue(main_file.is_file(), f"Missing main entry point: {main_file}")
        content = main_file.read_text(encoding="utf-8")
        self.assertIn("DOMContentLoaded", content)
        self.assertIn("NavigationController", content)
        self.assertIn("PipelineController", content)
        self.assertIn("window.App", content)
        self.assertIn("window.dbg", content)

    def test_css_modular_partials_exist(self):
        """Verify CSS token, layout, component, and view partials exist."""
        expected_css = [
            "tokens.css",
            "layout.css",
            "components/buttons.css",
            "components/forms.css",
            "components/cards.css",
            "components/pipeline.css",
            "components/diff-viewer.css",
            "components/diagnostics.css",
            "views/default-resume.css",
            "views/tailor.css",
            "views/cover-letter.css",
            "views/interview-prep.css",
            "views/graph_explorer.css",
            "views/chat.css",
            "views/search.css",
        ]
        for rel_path in expected_css:
            filepath = self.css_dir / rel_path
            self.assertTrue(filepath.is_file(), f"Missing CSS file: {filepath}")
            content = filepath.read_text(encoding="utf-8")
            self.assertGreater(len(content.strip()), 20, f"CSS file {rel_path} is too short")

    def test_styles_css_imports_all_partials(self):
        """Verify root styles.css imports all modular CSS partials."""
        styles_file = self.static_dir / "styles.css"
        self.assertTrue(styles_file.is_file())
        content = styles_file.read_text(encoding="utf-8")
        self.assertIn('@import "./css/tokens.css"', content)
        self.assertIn('@import "./css/layout.css"', content)
        self.assertIn('@import "./css/components/pipeline.css"', content)

    def test_index_html_loads_module_script(self):
        """Verify index.html loads main.js as an ES6 module and contains interactive elements."""
        index_file = self.static_dir / "index.html"
        self.assertTrue(index_file.is_file())
        content = index_file.read_text(encoding="utf-8")
        self.assertIn('type="module"', content)
        self.assertIn('/static/js/main.js', content)
        self.assertIn('agent-thought-terminal', content)
        self.assertIn('pipeline-flowchart', content)
        self.assertIn('sound-toggle-btn', content)
        self.assertIn('graph-canvas', content)
        self.assertIn('graph-zoom-fit', content)
        self.assertIn('graph-tooltip', content)
        self.assertIn('graph-hint', content)


if __name__ == "__main__":
    unittest.main()
