# -*- coding: utf-8 -*-
import os
import logging
from tools.dbTools import insert_article
from scrapy.utils.project import get_project_settings
from pdf_parser.pdf_parse import (get_pdf_document, parse_pdf_document,
                                  grab_section)


class WsfScrapingPipeline(object):
    def process_item(self, item, spider):
        settings = get_project_settings()
        keep_pdf = settings['KEEP_PDF']
        download_only = settings['DOWNLOAD_ONLY']
        feed = settings['FEED_CONFIG']

        # Convert PDF content to text format
        f = open('/tmp/' + item['pdf'], 'rb')

        if download_only:
            os.rename(
                '/tmp/' + item['pdf'],
                './results/pdf/' + item['pdf']
            )
            return item

        logging.info('Processing: ' + item['pdf'])
        document = get_pdf_document(f)
        pdf_file = parse_pdf_document(document)

        for keyword in settings['SEARCH_FOR_LISTS']:
            # Fetch references or other keyworded list
            section = grab_section(pdf_file, keyword)

            # Add references and PDF name to JSON returned file
            # If no section matchs, leave the attribute undefined
            if section:
                item['sections'][keyword.title()] = section

        # Fetch references or other keyworded list
        keyword_dict = pdf_file.get_lines_by_keywords(
            settings['SEARCH_FOR_KEYWORDS'],
            settings['KEYWORDS_CONTEXT']
        )

        # Add references and PDF name to JSON returned file
        # If no section matchs, leave the attribute undefined
        if keyword_dict:
            item['keywords'] = keyword_dict

        # Remove the PDF file
        f.close()

        has_keywords = len(item['keywords'])

        if keep_pdf and has_keywords:
            if feed == 'S3':
                pass
            else:
                os.rename(
                    '/tmp/' + item['pdf'],
                    './results/pdf/' + item['pdf']
                )

        os.remove('/tmp/' + item['pdf'])

        insert_article(item['title'], item['uri'])

        return item
