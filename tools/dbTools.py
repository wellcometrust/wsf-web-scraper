import sqlite3
import logging


class SQLite3Connector:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection = sqlite3.connect('db.sqlite3')
        self.cursor = self.connection.cursor()
        self._check_db()

    def __del__(self):
        self.connection.commit()
        self.cursor.close()
        self.connection.close()

    def _execute(self, query, params=()):
        try:
            self.cursor.execute(query, params)
        except Exception as error:
            self.logger.error(
                'An exception had been encountered when executing {}'.format(
                    query,
                )
            )

    def _check_db(self):
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS article
            (
                id INTEGER PRIMARY KEY,
                title VARCHAR(64),
                url VARCHAR(255),
                file_hash VARCHAR(32),
                scrap_again INTEGER(1) DEFAULT(0),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

    def is_scraped(self, file_hash):
        self._execute(
            "SELECT id FROM article WHERE file_hash = ?",
            (file_hash,)
        )
        result = self.cursor.fetchone()
        return result or None

    def insert_article(self, title, file_hash, url):
        self._execute(
            "INSERT INTO article (title, file_hash, url) VALUES (?, ?, ?)",
            (title, file_hash, url)
        )
