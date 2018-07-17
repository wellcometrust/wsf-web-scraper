# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime
from scrapy import spiderloader
from tools import DatabaseConnector, DynamoDBConnector
from tools.utils import parse_keywords_files, get_file_hash
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import DropItem
from pdf_parser.pdf_parse import parse_pdf_document, grab_section


class WsfScrapingPipeline(object):
    def __init__(self):
        """Initialise the pipeline, giveng it the settings and keywords."""

        self.settings = get_project_settings()

        self.keywords = parse_keywords_files(
            self.settings['KEYWORDS_FILE']
        )

        self.section_keywords = parse_keywords_files(
            self.settings['SECTIONS_KEYWORDS_FILE']
        )

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.info(self.keywords)

        spider_loader = spiderloader.SpiderLoader.from_settings(self.settings)
        spiders = spider_loader.list()

        for spider_name in spiders:
            folder_path = os.path.join('results', 'pdfs', spider_name)
            os.makedirs(folder_path, exist_ok=True)

        if self.settings['DATABASE_ADAPTOR'] == 'dynamodb':
            self.database = DynamoDBConnector()
        else:
            self.database = DatabaseConnector()
        self.logger.info(
            'Using %s database backend. [%s]',
            self.settings.get('DATABASE_ADAPTOR'),
            self.settings.get('FEED_CONFIG'),
        )

    def check_keywords(self, item, spider_name, base_pdf_path):
        """Convert the pdf file to a python object and analyse it to find
        keywords and section based on the section/keywords files provided.
        """

        keep_pdf = self.settings['KEEP_PDF']
        download_only = self.settings['DOWNLOAD_ONLY']
        feed = self.settings['FEED_CONFIG']
        pdf_result_path = os.path.join(
            'results',
            'pdfs',
            spider_name,
            os.path.basename(item['pdf']),
        )

        # Convert PDF content to text format
        with open(item['pdf'], 'rb') as f:
            if download_only:
                os.rename(
                    item['pdf'],
                    pdf_result_path,
                )
                return item

            self.logger.info(
                'Processing: %s',
                item['pdf']
            )

            pdf_file, pdf_text = parse_pdf_document(f)

            if not pdf_file:
                return item

            item['text'] = pdf_text

            for keyword in self.section_keywords:
                # Fetch references or other keyworded list
                section = grab_section(pdf_file, keyword)

                # Add references and PDF name to JSON returned file
                # If no section matchs, leave the attribute undefined
                if section:
                    item['sections'][keyword.title()] = section

            # Fetch references or other keyworded list
            keyword_dict = pdf_file.get_lines_by_keywords(
                self.keywords,
                self.settings['KEYWORDS_CONTEXT']
            )

            # Add references and PDF name to JSON returned file
            # If no section matchs, leave the attribute undefined
            if keyword_dict:
                item['keywords'] = keyword_dict

        has_keywords = len(item['keywords'])

        # If we need to keep the pdf, move it, else delete it
        if keep_pdf or has_keywords:
            if feed == 'S3':
                pass
            else:
                os.rename(
                    item['pdf'],
                    pdf_result_path,
                )
        else:
            try:
                os.remove(item['pdf'])
            except FileNotFoundError:
                self.logger.warning(
                    "The file couldn't be found, and wasn't deleted."
                )
        return item

    def process_item(self, item, spider):
        """Process items sent by the spider."""

        if not item['pdf']:
            raise DropItem(
                'Empty filename, could not parse the pdf.'
            )
        file_hash = get_file_hash(item['pdf'])
        id_publication, scrape_again = self.database.is_scraped(file_hash)
        if id_publication and not scrape_again:
            # File is already scraped in the database
            raise DropItem(
                'Item footprint is already in the database'
            )
        full_item = self.check_keywords(item, spider.name, item['pdf'])

        # Remove the path from the value we are storing
        full_item['pdf'] = os.path.basename(item['pdf'])
        full_item['hash'] = file_hash
        full_item['provider'] = spider.name
        full_item['date_scraped'] = datetime.now().strftime('%Y%m%d')
        if scrape_again:
            full_item['id'] = id_publication
            self.database.update_full_article(full_item)
        else:
            id_provider = self.database.get_or_create_name(
                spider.name, 'provider'
            )
            id_publication = self.database.insert_full_article(
                full_item,
                id_provider
            )
            self.database.insert_joints_and_text(
                'section',
                full_item.get('sections'),
                id_publication
            )
            self.database.insert_joints_and_text(
                'keyword',
                full_item.get('keywords'),
                id_publication
            )
            self.database.insert_joints(
                'type',
                full_item.get('types'),
                id_publication
            )
            self.database.insert_joints(
                'subjects',
                full_item.get('types'),
                id_publication
            )

        self.database.insert_article(file_hash, item['uri'])

        return full_item
