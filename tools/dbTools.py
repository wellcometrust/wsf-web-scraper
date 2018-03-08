import sqlite3
import logging


class SQLite3Connector:
    def __init__(self):
        """Initialise an instance of the SQLite3Connector class and create:
         - self.logger: a logger to log errors
         - self.connection: the connection to the sqlite3 database
         - self.cursor: the cursor to execute requests on the database
        It also run the check_db method, creating the database if it doesn't
        exists yet.
        """

        self.logger = logging.getLogger(__name__)
        self.connection = sqlite3.connect('db.sqlite3')
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self._check_db()

    def __del__(self):
        """Commit all changes and close the database connection on the deletion
        of this instance from memory.
        """
        self.connection.commit()
        self.cursor.close()
        self.connection.close()

    def _execute(self, query, params=()):
        """Try to execute the SQL query passed by the query parameter, with the
        arguments passed by the tuple argument params.
        """
        try:
            self.cursor.execute(query, params)
        except sqlite3.Error as error:
            self.logger.error(
                'An exception had been encountered when executing %s',
                query,
            )
            raise

    def _check_db(self):
        """Create the tables needed by the web scraper if they don't exists."""
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

    def reset_scraped(self):
        """Set all the articles `scrap_again` attribute to 1, forcing the web
        scraper to download and analyse them again.
        """
        self._execute(
            "UPDATE article SET scrap_again = ?",
            (1,)
        )

    def clear_db(self):
        """Remove all the articles from the database."""
        self._execute(
            "DELETE FROM article"
        )

    def close_connection(self):
        """Close the connection to the database and commit every changes."""

    def is_scraped(self, file_hash):
        """Check if an article had already been scraped by looking for its file
        hash into the database. Is the `scrap_again` attribute is true, return
        False anyway.
        """
        self._execute(
            "SELECT id FROM article WHERE file_hash = ? AND scrap_again = ?",
            (file_hash, 0)
        )
        result = self.cursor.fetchone()
        return result or None

    def get_articles(self, offset=0, limit=-1):
        """Return a list of articles. By default, returns every articles. This
        method accepts start and end arguments to paginate results.
        """
        if limit > 0:
            self._execute(
                "SELECT title, file_hash, url FROM article LIMIT ? OFFSET ?",
                (offset, limit,)
            )
        else:
            self._execute("SELECT title, file_hash, url FROM article")
        result = []
        for article in self.cursor.fetchall():
            result.append(article)
        return result

    def insert_article(self, title, file_hash, url):
        """Try to insert an article, composed by its title, file hash and url,
        into the database.
        """
        self._execute(
            "INSERT INTO article (title, file_hash, url) VALUES (?, ?, ?)",
            (title, file_hash, url)
        )
