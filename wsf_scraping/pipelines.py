# -*- coding: utf-8 -*-
import os
import logging
from scrapy import spiderloader
from scrapy.utils.project import get_project_settings
from tools.dbTools import insert_article
from tools.cleaners import parse_keywords_files
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

        spider_loader = spiderloader.SpiderLoader.from_settings(self.settings)
        spiders = spider_loader.list()
        if not os.path.isdir('./results/pdfs'):
            os.makedirs('./results/pdfs')

        for spider_name in spiders:
            if not os.path.isdir('./results/pdfs/%s' % spider_name):
                os.makedirs('./results/pdfs/%s' % spider_name)

    def process_item(self, item, spider):
        """Process items sent by the spider."""

        keep_pdf = self.settings['KEEP_PDF']
        download_only = self.settings['DOWNLOAD_ONLY']
        feed = self.settings['FEED_CONFIG']
        pdf_path = ''.join(['./results/pdfs/', spider.name, '/'])

        # Convert PDF content to text format
        f = open('/tmp/' + item['pdf'], 'rb')

        if download_only:
            os.rename(
                ''.join(['/tmp/', item['pdf']]),
                ''.join([pdf_path, item['pdf']])
            )
            return item

        self.logger.info('Processing: %s (%s)' % (
            item['pdf'],
            self.settings['PARSING_METHOD'],
        ))

        # Parse using pdftotext only if specified. Leads to more false positive
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

        f.close()

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
        insert_article(item['title'], item['uri'])

        return item
