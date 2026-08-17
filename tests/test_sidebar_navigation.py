"""
test_sidebar_navigation.py — Tests for Sidebar Rail Navigation Redesign.
Validates HTML structure, CSS rules/responsive tokens, and UI layout specifications.
"""

import unittest
from pathlib import Path
import re
from fastapi.testclient import TestClient

from src.web.app import app, ROOT_DIR


class TestSidebarNavigation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.html_path = ROOT_DIR / "src" / "web" / "static" / "index.html"
        cls.css_path = ROOT_DIR / "src" / "web" / "static" / "styles.css"
        cls.js_path = ROOT_DIR / "src" / "web" / "static" / "app.js"
        
        cls.html_content = cls.html_path.read_text(encoding="utf-8")
        cls.css_content = cls.css_path.read_text(encoding="utf-8")
        cls.js_content = cls.js_path.read_text(encoding="utf-8")

    def test_sidebar_rail_structure(self):
        """Verify sidebar rail element, sections, and nav buttons exist in index.html."""
        self.assertIn('class="sidebar-rail"', self.html_content)
        self.assertIn('id="sidebar-rail"', self.html_content)

        # Section Labels
        self.assertIn("BUILD", self.html_content)
        self.assertIn("PREPARE", self.html_content)
        self.assertIn("EXPLORE", self.html_content)

        # Action Buttons
        self.assertIn('id="nav-default-btn"', self.html_content)
        self.assertIn('id="nav-tailor-btn"', self.html_content)
        self.assertIn('id="nav-cover-btn"', self.html_content)
        self.assertIn('id="nav-prep-btn"', self.html_content)
        self.assertIn('id="nav-linkedin-btn"', self.html_content)
        self.assertIn('id="nav-chat-btn"', self.html_content)
        self.assertIn('id="open-diag-btn"', self.html_content)
        self.assertIn('id="nav-settings-btn"', self.html_content)

        # Material Symbols
        for symbol in ["article", "auto_awesome", "mail", "quiz", "share", "chat", "analytics", "settings"]:
            self.assertIn(symbol, self.html_content)

    def test_slim_header_and_search(self):
        """Verify slim header contains centered search and status badge."""
        self.assertIn('class="app-header"', self.html_content)
        self.assertIn('id="global-search-input"', self.html_content)
        self.assertIn('id="system-status"', self.html_content)
        self.assertIn('id="mobile-menu-btn"', self.html_content)

    def test_mobile_navigation_elements(self):
        """Verify mobile bottom navigation bar and scrim exist."""
        self.assertIn('id="mobile-bottom-nav"', self.html_content)
        self.assertIn('id="sidebar-scrim"', self.html_content)
        self.assertIn('id="mobile-more-sheet"', self.html_content)

    def test_css_grid_and_glassmorphism(self):
        """Verify CSS defines grid layout, glassmorphism, active accent, and transitions."""
        # Grid layout rules
        self.assertIn(".app-container", self.css_content)
        self.assertIn("56px 1fr", self.css_content)
        self.assertIn(".sidebar-rail", self.css_content)
        self.assertIn(".app-header", self.css_content)
        self.assertIn(".app-main", self.css_content)

        # Active state left border accent (3px)
        self.assertTrue(
            bool(re.search(r"border-left:\s*3px\s+solid", self.css_content)),
            "Expected 'border-left: 3px solid' active state styling in styles.css"
        )

        # Glassmorphism backdrop filter
        self.assertIn("backdrop-filter", self.css_content)
        self.assertIn("blur(", self.css_content)

        # Responsive media queries
        self.assertTrue(
            bool(re.search(r"@media\s*\([^\)]*max-width:\s*(?:1023px|1024px)", self.css_content)),
            "Expected tablet responsive breakpoint in styles.css"
        )
        self.assertTrue(
            bool(re.search(r"@media\s*\([^\)]*max-width:\s*(?:767px|768px)", self.css_content)),
            "Expected mobile responsive breakpoint in styles.css"
        )

    def test_view_transition_styles(self):
        """Verify view transition keyframes and classes exist in CSS."""
        self.assertIn("@keyframes viewIn", self.css_content)
        self.assertIn("@keyframes viewOut", self.css_content)

    def test_js_navigation_support(self):
        """Verify app.js handles sidebar, mobile navigation, and view switching."""
        self.assertIn("switchTab", self.js_content)
        self.assertIn("mobile-menu-btn", self.js_content)
        self.assertIn("sidebar-scrim", self.js_content)
        self.assertIn("mobile-bottom-nav", self.js_content)


if __name__ == "__main__":
    unittest.main()
