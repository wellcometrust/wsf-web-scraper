import scrapy
from scrapy.http import Request
from tools.cleaners import clean_html
from wsf_scraping.items import WHOArticle
from scrapy.utils.project import get_project_settings
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError


class WhoIrisSpider(scrapy.Spider):
    name = 'who_iris'
    # All these parameters are optionnal,
    # but it is good to set a result per page ubove 250, to limit query number
    data = {
        'location': '',
        'query': '',
        'sort_by': 'score',
        'filter_field_1': 'dateIssued',
        'filter_type_1': 'equals',
        'order': 'desc',
    }

    custom_settings = {
        'JOBDIR': 'crawls/who_iris'
    }

    def __init__(self, *args, **kwargs):
        settings = get_project_settings()
        years_list = kwargs.get('years_list', False)
        id = kwargs.get('uuid', '')

        self.uuid = id
        if years_list:
            self.years = years_list.split(',')
        else:
            self.years = settings['WHO_IRIS_YEARS']

    def on_error(self, failure):
        self.logger.error(repr(failure))

        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        elif failure.check(DNSLookupError):
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        elif failure.check(TimeoutError):
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)

    def start_requests(self):
        """ This sets up the urls to scrape for each years.
        """

        self.data['rpp'] = self.settings['WHO_IRIS_RPP']
        urls = []
        # Initial URL (splited for PEP8 compliance)
        base_url = 'http://apps.who.int/iris/discover'
        url = base_url + '?&rpp={rpp}&etal=0&group_by=none'
        url += '&filtertype_0=dateIssued&filtertype_1=iso'
        url += '&filter_relational_operator_0=contains'
        url += '&filter_relational_operator_1=contains'
        url += '&filter_1=en&filter_0={filter_0}'

        for year in self.years:
            self.data['filter_0'] = year
            # Format it with initial data and launch the process
            urls.append((url.format(**self.data), year))

        for url in urls:
            self.logger.info('Initial url: %s', url[0])
            yield scrapy.Request(
                url=url[0],
                callback=self.parse,
                errback=self.on_error,
                dont_filter=True,
                meta={'year': url[1]}
            )

    def parse(self, response):
        """ Parse the articles listing page and go to the next one.

        @url http://apps.who.int/iris/discover?rpp=3
        @returns items 0 0
        @returns requests 3 4
        """

        year = response.meta.get('year', {})
        for href in response.css('.artifact-title a::attr(href)').extract():
            yield Request(
                url=response.urljoin(href),
                callback=self.parse_article,
                errback=self.on_error,
                meta={'year': year}
            )

        if not self.settings['WHO_IRIS_LIMIT']:
            # Follow next link
            next_page = response.css(
                 'next-page-link::attr("href")'
            ).extract_first()

            yield Request(
                url=response.urljoin(next_page),
                callback=self.parse,
                errback=self.on_error,
                dont_filter=True,
                meta={'year': year}
            )

    def parse_article(self, response):
        """ Scrape the article metadata from the detailed article page. Then,
        redirect to the PDF page.

        @url http://apps.who.int/iris/handle/10665/123400
        @returns requests 1 1
        @returns items 0 0
        """

        year = response.meta.get('year', {})
        data_dict = {
            'Year': year,
        }
        for tr in response.css('table.itemDisplayTable tr'):
            label = tr.css('td.metadataFieldLabel::text').extract_first()
            label = label[:label.find(':')]
            # Remove HTML markdown for some metadata are in a <a>
            value = clean_html(tr.css('td.metadataFieldValue').extract_first())

            data_dict[label] = value

        # Scrap all the pdf on the page, passing scrapped metadata
        href = response.css(
            '.item-page-field-wrapper a:contains("pdf")::attr("href")'
        ).extract_first()
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

        is_pdf = b'application/pdf' in response.headers.get('content-type', '')

        if not is_pdf:
            self.logger.info('Not a PDF, aborting (%s)', response.url)
            return

        # Retrieve metadata
        data_dict = response.meta.get('data_dict', {})
        # Download PDF file to /tmp
        filename = response.url.split('/')[-1].replace(
            '?sequence=1&isAllowed=y', ''
        )
        with open('/tmp/' + filename, 'wb') as f:
            f.write(response.body)

        # Populate a WHOArticle Item
        who_article = WHOArticle({
                'title': data_dict.get('Title', ''),
                'uri': response.request.url,
                'year': data_dict.get('Year', ''),
                'authors': data_dict.get('Authors', ''),
                'pdf': filename,
                'sections': {},
                'keywords': {}
            }
        )

        yield who_article
