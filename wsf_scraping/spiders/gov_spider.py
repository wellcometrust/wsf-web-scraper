import scrapy
from urllib.parse import urlparse
from scrapy.http import Request
from collections import defaultdict
from wsf_scraping.items import WHOArticle
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError


class GovSpider(scrapy.Spider):
    name = 'gov_uk'

    custom_settings = {
        'JOBDIR': 'crawls/gov_uk'
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

        for href in response.css('.artifact-title a::attr(href)').extract():
            full_records_link = ''.join([href, '?show=full'])
            yield Request(
                url=response.urljoin(full_records_link),
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

        data_dict = {
            'year': response.meta.get('year', {}),
        }
        data_dict['title'] = response.css(
            'h2.page-header::text'
        ).extract_first()

        details_dict = defaultdict(list)
        for line in response.css('.detailtable tr'):

            # Each tr should have 2 to 3 td: attribute, value and language.
            # We're only interested in the first and the second one.
            tds = line.css('td::text').extract()
            if len(tds) < 2:
                continue

            # Make attribute human readable
            # (first part is always 'dc', so skip it)
            attr_name = ' '.join(tds[0].split('.')[1:]).lower()
            details_dict[attr_name].append(f'{tds[1]}')

        # Scrap all the pdf on the page, passing scrapped metadata
        href = response.css(
            '.file-link a::attr("href")'
        ).extract_first()

        data_dict['subjects'] = details_dict.get('subject mesh', [])
        data_dict['types'] = details_dict.get('type', [])
        data_dict['authors'] = ', '.join(
            details_dict.get('contributor author', [])
        )
        if href:
            yield Request(
                url=response.urljoin(href),
                callback=self.save_pdf,
                errback=self.on_error,
                meta={'data_dict': data_dict}
            )
        else:
            err_link = href if href else ''.join([response.url, ' (referer)'])
            self.logger.debug(
                "Item is null - Canceling (%s)",
                err_link
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

        # Retrieve metadata
        data_dict = response.meta.get('data_dict', {})
        # Download PDF file to /tmp
        filename = urlparse(response.url).path.split('/')[-1]
        with open('/tmp/' + filename, 'wb') as f:
            f.write(response.body)

        # Populate a WHOArticle Item
        who_article = WHOArticle({
                'title': data_dict.get('title', ''),
                'uri': response.request.url,
                'year': data_dict.get('year', ''),
                'authors': data_dict.get('authors', ''),
                'types': data_dict.get('types'),
                'subjects': data_dict.get('subjects'),
                'pdf': filename,
                'sections': {},
                'keywords': {}
            }
        )

        yield who_article
