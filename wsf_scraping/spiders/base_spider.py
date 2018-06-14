import scrapy
import os
import tempfile
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError
from urllib.parse import urlparse


class BaseSpider(scrapy.Spider):

    def __init__(self, *args, **kwargs):
        id = kwargs.get('uuid', '')
        self.uuid = id

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

    def _check_headers(self, response_headers,
                       desired_extension=b'application/pdf'):
        content_type = response_headers.get('content-type', '').split(b';')[0]
        return desired_extension == content_type

    def _save_file(self, url, response_body):
        filename = os.path.basename(urlparse(url).path).lower()
        if filename:
            if not filename.endswith('.pdf'):
                filename = filename + '.pdf'
            filepath = os.path.join(tempfile.gettempdir(), filename)
            with open(filepath, 'wb') as f:
                f.write(response_body)
            return filename
        else:
            self.logger.warning('Empty filename, could not save the file.')
            return ''
