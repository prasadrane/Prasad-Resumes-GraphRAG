"""Tests for ConversationStore — SQLite-based per-session conversation memory."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.query.conversation_store import (
    ConversationStore,
    get_conversation_store,
    reset_conversation_store,
)


class TestConversationStore(unittest.TestCase):

    def setUp(self):
        """Fresh tmp db for each test so sessions are isolated."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db_path = path
        self.store = ConversationStore(db_path=path)

    def tearDown(self):
        """Remove temp db after each test."""
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_add_and_get_messages(self):
        sid = "s-1"
        self.store.add_message(sid, "user", "Hello")
        self.store.add_message(sid, "assistant", "Hi there")
        history = self.store.get_history(sid, limit=10)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Hello")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "Hi there")

    def test_isolation_between_sessions(self):
        self.store.add_message("session-a", "user", "A-msg")
        self.store.add_message("session-b", "user", "B-msg")
        a_hist = self.store.get_history("session-a")
        b_hist = self.store.get_history("session-b")
        self.assertEqual(len(a_hist), 1)
        self.assertEqual(len(b_hist), 1)
        self.assertEqual(a_hist[0]["content"], "A-msg")
        self.assertEqual(b_hist[0]["content"], "B-msg")

    def test_limit_parameter(self):
        sid = "s-limit"
        for i in range(5):
            self.store.add_message(sid, "user", f"msg-{i}")
        history = self.store.get_history(sid, limit=3)
        self.assertEqual(len(history), 3)
        # Should be the last 3 messages (chronological): msg-2, msg-3, msg-4
        self.assertEqual(history[0]["content"], "msg-2")
        self.assertEqual(history[-1]["content"], "msg-4")

    def test_has_session_false_then_true(self):
        sid = "new-sess"
        self.assertFalse(self.store.has_session(sid))
        self.store.add_message(sid, "user", "hello")
        self.assertTrue(self.store.has_session(sid))

    def test_clear_session_removes_all(self):
        sid = "clear-me"
        self.store.add_message(sid, "user", "secret")
        self.store.add_message(sid, "assistant", "response")
        self.store.clear_session(sid)
        self.assertFalse(self.store.has_session(sid))
        self.assertEqual(self.store.get_history(sid), [])

    def test_empty_history_for_unknown_session(self):
        self.assertEqual(self.store.get_history("nonexistent"), [])

    def test_roles_enforced(self):
        """SQLite CHECK constraint should reject invalid roles."""
        conn = self.store._conn()
        with self.assertRaises(Exception):
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES "
                "(1, 'invalid', 'bad')"
            )
        conn.rollback()
        conn.close()


class TestGetConversationStoreSingleton(unittest.TestCase):

    def setUp(self):
        reset_conversation_store()

    def tearDown(self):
        reset_conversation_store()

    def test_returns_same_instance(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        s1 = get_conversation_store(db_path=path)
        s2 = get_conversation_store(db_path=path)
        self.assertIs(s1, s2)
        try:
            os.unlink(path)
        except OSError:
            pass

    def test_reset_clears_singleton(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        s1 = get_conversation_store(db_path=path)
        reset_conversation_store()
        s2 = get_conversation_store(db_path=path)
        self.assertIsNot(s1, s2)
    def test_default_db_path_honors_output_dir(self):
        """Test default db path uses OUTPUT_DIR_PATH from src.config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from unittest.mock import patch
            from pathlib import Path
            mock_output_path = Path(tmpdir) / "custom_output"
            with patch("src.query.conversation_store.OUTPUT_DIR_PATH", mock_output_path):
                store = ConversationStore()
                self.assertEqual(store.db_path, mock_output_path / "conversations.db")
                self.assertTrue(store.db_path.parent.exists())


if __name__ == "__main__":
    unittest.main()

