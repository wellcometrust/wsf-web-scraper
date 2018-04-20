import boto3
import logging
from botocore.exceptions import ClientError


class DynamoDBConnector:
    """Connector to make the web scraper compatible with AWS Dynamodb. It relies
    on boto3 and uses the credentials stored in ~/.aws/credentials.
    """

    def __init__(self):
        """Initialise the connection, try to create the tables if they don't
        exist yet. Create a logger instance as well.
        """
        self.logger = logging.getLogger(__name__)
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name='eu-west-2',
            endpoint_url='http://localhost:8765'
        )
        try:
            if 'scraper_articles' not in self.dynamodb.list_tables():
                self.__create_articles_table()
        except ClientError as e:
            self.logger.error(
                'Error when initialising the connection [%s]', e
            )

    def __create_articles_table(self):
        """Create the table to store web crawler information about
        already scraped articles (file hash and url).
        """
        table = self.dynamodb.create_table(
            TableName='scraper_articles',
            KeySchema=[
                {'AttributeName': 'file_hash', 'KeyType': 'HASH'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'file_hash', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )
        return table

    def __create_catalog_table(self):
        """Create the table to store scraping results s3 path,
        timestamp and index.
        """
        table = self.dynamodb.create_table(
            TableName='scraper_catalog',
            KeySchema=[
                {'AttributeName': 'file_index', 'KeyType': 'HASH'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'file_index', 'AttributeType': 'S'},
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )
        return table

    def insert_article(self, file_hash, url):
        try:
            table = self.dynamodb.Table("scraper_articles")
            response = table.put_item(Item={
                'file_hash': file_hash,
                'url': url
            })
        except ClientError as e:
            self.logger.error('Couldn\'t insert article [%s]', e)
            return

        return response

    def insert_file_in_catalog(self, file_index, file_path):
        try:
            table = self.dynamodb.Table('scraper_catalog')
        except ClientError as e:
            self.logger.error('Couldn\'t insert file in the catalog [%s]', e)
            return
        return table

    def is_scraped(self, file_hash):
        try:
            self.logger.info('Fetch scraped items...')
            table = self.dynamodb.Table('scraper_articles')
            item = table.get_item(
                TableName='scraper_articles',
                Key={
                    'file_hash': file_hash,
                },
                ConsistentRead=True,
            )
            self.logger.info('Scraped item: [%s]', 'Item' in item.keys())
        except ClientError as e:
            self.logger.error('Couldn\'t fetch article [%s]', e)
            return False
        return 'Item' in item.keys()
