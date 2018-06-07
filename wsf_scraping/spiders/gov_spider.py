import scrapy
from urllib.parse import urlparse
from scrapy.http import Request
from .base_spider import BaseSpider
from wsf_scraping.items import UNICEFArticle


class GovSpider(BaseSpider):
    name = 'gov_uk'
    custom_settings = {
        'JOBDIR': 'crawls/gov_uk'
    }

    def start_requests(self):
        """ This sets up the urls to scrape for each years."""
        urls = [
            'https://www.gov.uk/government/policies',
        ]

        for url in urls:
            self.logger.info('Initial url: %s', url)
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.on_error,
                dont_filter=True,
            )

    def parse(self, response):
        """ Parse the articles listing page and go to the next one.

        @url https://www.gov.uk/government/policies
        @returns items 0 0
        @returns requests 1
        """

        file_links = response.css(
            '.attachment-details .title a::attr("href")'
        ).extract()
        other_document_links = response.css(
            'li.document a::attr("href")'
        ).extract()

        for href in other_document_links:
            yield Request(
                url=response.urljoin(href),
                callback=self.parse,
                errback=self.on_error,
            )

        for href in file_links:
            if response.headers.get(
                'content-type', ''
            ).split(b';')[0] != b'text/html':
                return Request(
                    url=response.urljoin(href),
                    callback=self.save_pdf,
                    errback=self.on_error
                )
            else:
                yield Request(
                    url=response.urljoin(href),
                    callback=self.parse,
                    errback=self.on_error,
                )

        next_page = response.css(
            '.pub-c-pagination__item--next a::attr("href")'
        ).extract_first()
        if next_page:
            yield Request(
                url=response.urljoin(next_page),
                callback=self.parse,
                errback=self.on_error,
            )

    def save_pdf(self, response):
        """ Retrieve the pdf file and scan it to scrape keywords and sections.

        @url http://apps.who.int/iris/bitstream/10665/123575/1/em_rc8_5_en.pdf
        @returns items 1 1
        @returns requests 0 0
        """

        self.logger.info("1")

        is_pdf = self._check_headers(response.headers)

        if not is_pdf:
            self.logger.info('Not a PDF, aborting (%s)', response.url)
            return

        self.logger.info("2")
        # Download PDF file to /tmp
        filename = urlparse(response.url).path.split('/')[-1]
        with open('/tmp/' + filename, 'wb') as f:
            f.write(response.body)
            self.logger.info('Writing file to the hard drive.')
        # Populate a WHOArticle Item
        who_article = UNICEFArticle({
                'title': '',
                'uri': response.request.url,
                'pdf': filename,
                'sections': {},
                'keywords': {}
            }
        )

        yield who_article
