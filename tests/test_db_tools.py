import unittest
import sqlite3
from tools import SQLite3Connector


class TestDBTools(unittest.TestCase):

    def setUp(self):
        self.database = SQLite3Connector()

    def test_queries(self):
        self.database.insert_article(
            'Test',
            '0' * 32,
            'http://example.com/pdf.pdf'
        )
        self.assertTrue(self.database.is_scraped('0' * 32))
        self.database._execute(
            'UPDATE article SET scrap_again = 1 WHERE file_hash = ?',
            ('0' * 32,)
        )
        self.assertFalse(self.database.is_scraped('0' * 32))
        self.database._execute(
            'DELETE FROM article WHERE file_hash = ?',
            ('0' * 32,)
        )
        self.assertFalse(self.database.is_scraped('0' * 32))

    def test_exception(self):
            self.assertRaises(
                sqlite3.Error,
                self.database._execute,
                'SELECT 1 FROM sssss'
            )
