import unittest
from tools import DatabaseConnector


class TestDBTools(unittest.TestCase):

    def setUp(self):
        """Assuming the database is already set up."""
        self.database = DatabaseConnector(
            'localhost', 'test_user', '', 'scraper_test'
        )
        mock_publication = {
            'title': 'foo',
            'uri': 'http://foo.bar',
            'pdf': 'foobar',
            'hash': '0' * 32,
            'authors': 'John Doe, Jane Doe',
            'year': '1999',
            'text': 'Very long sentence' * 300,
        }
        sections = {'foo': 'bar' * 32}
        keywords = {'bar': 'foo' * 32}
        types = [
            'foo',
            'bar',
            'kix'
        ]
        subjects = [
            'lorem',
            'ipsum'
        ]
        id_provider = self.database.get_or_create_name('foo.org', 'provider')
        id_pub = self.database.insert_full_publication(mock_publication,
                                                       id_provider)
        self.database.insert_joints('type', types, id_pub)
        self.database.insert_joints('subject', subjects, id_pub)
        self.database.insert_joints_and_text('section', sections, id_pub)
        self.database.insert_joints_and_text('keyword', keywords, id_pub)

    def tearDown(self):
        self.database._execute('DELETE FROM publications_types')
        self.database._execute('DELETE FROM publications_subjects')
        self.database._execute('DELETE FROM publications_sections')
        self.database._execute('DELETE FROM publications_keywords')
        self.database._execute('DELETE FROM type')
        self.database._execute('DELETE FROM subject')
        self.database._execute('DELETE FROM section')
        self.database._execute('DELETE FROM keyword')
        self.database._execute('DELETE FROM publication')
        self.database._execute('DELETE FROM provider')

    def test_full_publication(self):
        self.assertTrue(self.database.get_scraping_info('0' * 32))

    def test_joints(self):
        self.database._execute('SELECT * FROM section')
        self.assertTrue(self.database.cursor.fetchone())
        self.database._execute('SELECT * FROM keyword')
        self.assertTrue(self.database.cursor.fetchone())
        self.database._execute('SELECT * FROM publications_sections')
        self.assertTrue(self.database.cursor.fetchone())
        self.database._execute('SELECT * FROM publications_keywords')
        self.assertTrue(self.database.cursor.fetchone())
        self.database._execute('SELECT * FROM type')
        self.assertTrue(self.database.cursor.fetchone())
        self.database._execute('SELECT * FROM publications_types')
        self.assertTrue(self.database.cursor.fetchone())
        self.database._execute('SELECT * FROM subject')
        self.assertTrue(self.database.cursor.fetchone())
        self.database._execute('SELECT * FROM publications_subjects')
        self.assertTrue(self.database.cursor.fetchone())
