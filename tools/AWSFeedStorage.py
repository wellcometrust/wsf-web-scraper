import boto3
import logging
from six.moves.urllib.parse import urlparse
from .dynamodbConnector import DynamoDBConnector
from scrapy.extensions.feedexport import BlockingFeedStorage
from botocore.exceptions import ClientError


class AWSFeedStorage(BlockingFeedStorage):
    """This feed storage will store the results in a json file, in a S3 bucket
    and will update the Dynamodb catalog table with the location, the timestamp
    and the name of the file.
    """

    def __init__(self, uri):
        """Initialise the Feed Storage, giving it AWS informations."""
        from scrapy.conf import settings

        self.logger = logging.getLogger(__name__)

        u = urlparse(uri)
        self.s3_file = u.path[1:]
        self.s3_bucket = settings['AWS_S3_BUCKET']
        self.s3 = boto3.client('s3')
        self.dynamodb = DynamoDBConnector()

    def _store_in_thread(self, data_file):
        """This method will try to upload the file to S3, then to insert the
        file's related information into DynamoDB.
        """
        data_file.seek(0)
        try:
            self.s3.put_object(
                Body=data_file,
                Bucket=self.s3_bucket,
                Key=self.s3_file
            )
        except ClientError as e:
            self.logger.error('Couldn\'t upload the json file to s3: %s', e)
        else:
            self.dynamodb.insert_file_in_catalog(
                self.s3_file,
                f'{self.s3_bucket}/{self.s3_file}',
            )
