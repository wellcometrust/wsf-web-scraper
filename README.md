# wsf-web-scraper

![genericSpider](https://user-images.githubusercontent.com/235073/38735019-72dbd1f6-3f1f-11e8-9cb4-fa6f3d270dda.png)

A web scraper tool to get data for evaluating Wellcome impact.

## Development

To bring up the development environment using docker:

1. Start a clean postgres DB:
   ```
   docker-compose up -d
   ```
2. Build the base image
   ```
   make base_image
   ```

Then, to run a scraper from your local repo, run:

```
./docker_run.sh ./entrypoint.sh SPIDER_TO_RUN
```

where `SPIDER_TO_RUN` is one of:
  * `who_iris`
  * `gov_uk`
  * `nice`
  * `unicef`
  * `msf`
  * `parliament`

If you need to run outside docker, Dockerfile.base and entrypoint.sh
should point you in the right direction.

## Testing

To run tests, first bring up the development environment as above.

Then, run:

```
./docker_run.sh python -m unittest discover -s /pwd/tests
```

## Usage

To deploy this scraper yourself, see the wiki:
https://github.com/wellcometrust/wsf-web-scraper/wiki

This scraper can also be deployed more easily using Docker.

## Output Formatting

The outputed file is meant to contain a number a different fields, which
can vary depending on the scraper provider.

It will always have the following attributes, though:

|Unique|Attribute|Description|
|------|---------|-----------|
|      |title    | a string containing the document title|
|*     |uri      | the url of the document|
|      |pdf      | the name of the file|
|      |sections | a json object of section names, containing the text extracted from matching sections|
|      |keywords | a json object of keywords, containing the text extracted from matching text|
|*     |hash     | a md5 digest of the file|
|      |provider | the provider from where the file has been downloaded|
|      |date_scraped | the date (YYYYMMDD) when the article has been scraped|

Some providers will have additional parameters:

### WHO

|Attribute|Description|
|---------|-----------|
|year     | the publication year of the document|
|types    | an array containing the WHO type associated with the document|
|subjects | an array containing the WHO subjects of the document|
|authors  | an array containing the authors (from WHO)|

### Nice

|Attribute|Description|
|---------|-----------|
|year     | the publication year of the document|

### Parliament

|Attribute|Description|
|---------|-----------|
|year     | the publication year of the document|
|types    | the type of the document |
