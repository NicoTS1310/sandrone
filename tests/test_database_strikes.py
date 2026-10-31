import os
import tempfile
import unittest
from unittest.mock import patch

from utils.database import (
    add_strike,
    get_connection,
    get_strike_count,
    get_strike_history,
    get_strike_overview,
    get_strike_total,
    get_strike_user_count,
    init_db,
    remove_latest_strike,
)


class StrikeDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, "test.db")
        self.database_path_patch = patch("utils.database.DB_PATH", database_path)
        self.database_path_patch.start()
        init_db()

    def tearDown(self):
        self.database_path_patch.stop()
        self.temp_dir.cleanup()

    def test_removed_strikes_keep_audit_history_but_leave_active_count(self):
        add_strike(1, 10, 100, "Manual warning", "manual")
        add_strike(1, 10, None, "Spam detected", "spam")

        self.assertEqual(get_strike_count(1, 10), 2)
        self.assertEqual(get_strike_history(1, 10, limit=1)[0][0], "Spam detected")
        self.assertTrue(remove_latest_strike(1, 10, 200))
        self.assertFalse(remove_latest_strike(1, 99, 200))
        self.assertEqual(get_strike_count(1, 10), 1)
        self.assertEqual(get_strike_history(1, 10), [("Manual warning", unittest.mock.ANY, "manual")])

        with get_connection() as connection:
            removed = connection.execute(
                "SELECT removed_by FROM strikes WHERE user_id = 10 AND reason = 'Spam detected'"
            ).fetchone()
        self.assertEqual(removed, (200,))

    def test_overview_is_guild_scoped_and_sorted_by_active_strikes(self):
        add_strike(1, 10, 100, "First", "manual")
        add_strike(1, 10, 100, "Second", "manual")
        add_strike(1, 20, 100, "Third", "manual")
        add_strike(2, 30, 100, "Other server", "manual")

        self.assertEqual(get_strike_user_count(1), 2)
        self.assertEqual(get_strike_total(1), 3)
        self.assertEqual(get_strike_overview(1, limit=1, offset=0), [(10, 2)])
        self.assertEqual(get_strike_overview(1, limit=1, offset=1), [(20, 1)])


if __name__ == "__main__":
    unittest.main()
