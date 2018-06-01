import scrapy
from urllib.parse import urlparse
from scrapy.http import Request
from wsf_scraping.items import UNICEFArticle
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError


class UnicefSpider(scrapy.Spider):
    name = 'unicef'
    # All these parameters are optionnal,
    # but it is good to set a result per page ubove 250, to limit query number
    data = {}

    custom_settings = {
        'JOBDIR': 'crawls/unicef'
    }

    def on_error(self, failure):
        self.logger.error(repr(failure))

        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error(
                'HttpError on %s (%s)',
                response.url,
                response.status,
            )

        elif failure.check(DNSLookupError):
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        elif failure.check(TimeoutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)

    def start_requests(self):
        """ This sets up the urls to scrape for each years.
        """

        urls = [
            'https://data.unicef.org/resources/resource-type/publication/',
            'https://data.unicef.org/resources/resource-type/guidance/'
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

        @url http://apps.who.int/iris/discover?rpp=3
        @returns items 0 0
        @returns requests 3 4
        """

        for href in response.css('h2 a::attr(href)').extract():
            yield Request(
                url=response.urljoin(href),
                callback=self.parse_article,
                errback=self.on_error,
            )

    def parse_article(self, response):
        """ Scrape the article metadata from the detailed article page. Then,
        redirect to the PDF page.

        @url http://apps.who.int/iris/handle/10665/272346?show=full
        @returns requests 1 1
        @returns items 0 0
        """

        title = response.css('.entry-heading h1::text').extract_first()
        hrefs = response.css('a::attr("href")').extract()
        ls = list(filter(lambda x: x.endswith('pdf'), hrefs))
        for link in ls:
            yield Request(
                url=response.urljoin(link),
                callback=self.save_pdf,
                errback=self.on_error,
                meta={'title': title}
            )

    def save_pdf(self, response):
        """ Retrieve the pdf file and scan it to scrape keywords and sections.

        @url http://apps.who.int/iris/bitstream/10665/123575/1/em_rc8_5_en.pdf
        @returns items 1 1
        @returns requests 0 0
        """

        content_type = response.headers.get('content-type', '').split(b';')[0]
        is_pdf = b'application/pdf' == content_type

        if not is_pdf:
            self.logger.info('Not a PDF, aborting (%s)', response.url)
            return

        # Download PDF file to /tmp
        filename = urlparse(response.url).path.split('/')[-1]
        with open('/tmp/' + filename, 'wb') as f:
            f.write(response.body)

        # Populate a WHOArticle Item
        unicef_article = UNICEFArticle({
                'title': response.meta.get('title', ''),
                'uri': response.request.url,
                'pdf': filename,
                'sections': {},
                'keywords': {}
            }
        )

        yield unicef_article
