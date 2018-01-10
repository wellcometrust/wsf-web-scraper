import scrapy
import os
import json
import logging
from lxml import html
from scrapy.http import Request


class NiceSpider(scrapy.Spider):
    name = 'nice'

    def start_requests(self):
        urls = []
        # Initial URL (splited for PEP8 compliance). -1 length displays
        # the whole list.
        base_url = 'https://www.nice.org.uk/guidance/published/ajax'
        url = base_url + '?iDisplayLength=-1&type=apg,csg,cg,mpg,ph,sg,sc'

        # NICE website only answers to AJAX requests
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'referer': 'https://www.nice.org.uk/guidance/published'
        }
        urls.append(url)

        for url in urls:
            print(url)
            yield scrapy.Request(
                url=url,
                headers=headers,
                callback=self.parse,
            )

    def parse(self, response):
        """ Parse the articles listing page.

        @ajax
        @url https://www.nice.org.uk/guidance/published/ajax?iDisplayLength=10
        @returns items 0 0
        @returns requests 10 30
        """

        # Grab the link to the detailed article, its evidences and history
        try:
            articles = json.loads(response._body)
            doc_links = []
            evidence_links = []
            history_links = []

            for doc in articles['aaData']:
                doc_link = html.fromstring(doc['ProductTitle']).get('href')
                doc_links.append('https://www.nice.org.uk%s' % doc_link)
                evidence_links.append(
                    'https://www.nice.org.uk%s/evidence' % doc_link
                )
                history_links.append(
                    'https://www.nice.org.uk%s/history' % doc_link
                )

            for url in doc_links:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_article
                )

            for url in evidence_links:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_evidences
                )

            for url in history_links:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_histories
                )

        except json.decoder.JSONDecodeError:
            logging.info('Response was not json serialisable')

    def parse_evidences(self, response):
        """ Scrape the article metadata from the detailed article page. Then,
        redirect to the PDF page.

        @url https://www.nice.org.uk/guidance/ta494/evidence
        @returns requests 1 1
        @returns items 0 0
        """

        # Scrap all the pdf on the page, passing scrapped metadata
        for href in response.css('.track-link').extract():
            yield Request(
                url=response.urljoin(href),
                callback=self.save_pdf,
            )

    def parse_histories(self, response):
        """ Scrape the article metadata from the detailed article page. Then,
        redirect to the PDF page.

        @url https://www.nice.org.uk/guidance/ta494/history
        @returns requests 24 24
        @returns items 0 0
        """

        # Scrap all the pdf on the page, passing scrapped metadata
        for href in response.css('.track-link').extract():
            yield Request(
                url=response.urljoin(href),
                callback=self.save_pdf,
            )

    def parse_article(self, response):
        """ Scrape the article metadata from the detailed article page. Then,
        redirect to the PDF page.

        @url https://www.nice.org.uk/guidance/ta494
        @returns requests 1 1
        @returns items 0 0
        """
        href = response.xpath(
            './/a[contains(., "Save as PDF")]/@href'
        ).extract_first()
        if href:
            yield Request(
                url=response.urljoin(href),
                callback=self.save_pdf
            )
        else:
            logging.info('No link found to download the pdf version')

    def save_pdf(self, response):
        """ Retrieve the pdf file and scan it to scrape keywords and sections.

        @url http://apps.who.int/iris/bitstream/10665/123575/1/em_rc8_5_en.pdf
        @returns items 0
        @returns requests 0 0
        """

        # Download PDF file to /tmp
        is_pdf = response.headers.get('content-type', '') == 'application/pdf'
        if not is_pdf:
            return
        logging.info('Found a pdf')
        filename = response.url.split('/')[-1]
        with open('./pdf_result/' + filename, 'wb') as f:
            f.write(response.body)
