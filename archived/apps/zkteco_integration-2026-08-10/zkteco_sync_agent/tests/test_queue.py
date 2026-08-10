# Copyright (c) 2026, Exacuer
"""Unit tests for local queue (no Frappe required)."""

import os
import tempfile
import unittest
from pathlib import Path

from queue_db import AttendanceQueue


class TestAttendanceQueue(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.db = AttendanceQueue(Path(self.tmp.name) / "q.db")

	def tearDown(self):
		self.db.close()
		self.tmp.cleanup()

	def test_duplicate_enqueue(self):
		ok1 = self.db.enqueue("DEV1", "1001", "2026-08-10 09:00:00", "IN")
		ok2 = self.db.enqueue("DEV1", "1001", "2026-08-10 09:00:00", "IN")
		self.assertTrue(ok1)
		self.assertFalse(ok2)

	def test_stamp(self):
		self.db.set_last_att_stamp("DEV1", "2026-08-10 10:00:00")
		self.assertEqual(self.db.get_last_att_stamp("DEV1"), "2026-08-10 10:00:00")


if __name__ == "__main__":
	unittest.main()
