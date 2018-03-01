# -*- coding: utf-8 -*-
import os
import logging
from scrapy import spiderloader
from tools import SQLite3Connector
from tools.cleaners import parse_keywords_files, get_file_hash
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import DropItem
from pdf_parser.pdf_parse import (parse_pdf_document, grab_section,
                                  parse_pdf_document_pdftxt)


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
        self.database = SQLite3Connector()

        spider_loader = spiderloader.SpiderLoader.from_settings(self.settings)
        spiders = spider_loader.list()

        for spider_name in spiders:
            os.makedirs('./results/pdfs/%s' % spider_name, exist_ok=True)

    def check_keywords(self, item, spider_name):
        keep_pdf = self.settings['KEEP_PDF']
        download_only = self.settings['DOWNLOAD_ONLY']
        feed = self.settings['FEED_CONFIG']
        pdf_path = ''.join(['./results/pdfs/', spider_name, '/'])

        # Convert PDF content to text format
        with open('/tmp/' + item['pdf'], 'rb') as f:
            if download_only:
                os.rename(
                    ''.join(['/tmp/', item['pdf']]),
                    ''.join([pdf_path, item['pdf']])
                )
                return item

            self.logger.info(
                'Processing: %s (%s)',
                item['pdf'],
                self.settings['PARSING_METHOD'],
            )

            if self.settings['PARSING_METHOD'] == 'pdftotext':
                pdf_file = parse_pdf_document_pdftxt(f)
            else:
                pdf_file = parse_pdf_document(f)

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
                    ''.join(['/tmp/', item['pdf']]),
                    ''.join([pdf_path, item['pdf']])
                )
        else:
            os.remove('/tmp/' + item['pdf'])
        return item

    def process_item(self, item, spider):
        """Process items sent by the spider."""

        file_hash = get_file_hash('/tmp/' + item['pdf'])
        if self.database.is_scraped(file_hash):
            # File is already scraped in the database
            raise DropItem(
                'Item footprint is already in the database'
            )
        full_item = self.check_keywords(item, spider.name)
        self.database.insert_article(item['title'], file_hash, item['uri'])

        return full_item
