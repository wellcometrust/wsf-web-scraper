#!/bin/bash

set -o nounset
set -o errexit

if [ "$SPIDER_TO_RUN" == 'who_iris' ]
then
    scrapy crawl who_iris
elif [ "$SPIDER_TO_RUN" == 'nice' ]
then
    scrapy crawl nice
else
    exit 1
fi
exit 0
