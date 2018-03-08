# Use an official Ubuntu as a parent image
FROM python:3.6.4

RUN apt-get update -yqq \
  && apt-get install -yqq --no-install-recommends \
    python3 \
    python3-dev \
    gcc \
    python3-pip \
    libpoppler-cpp-dev \
    poppler-utils \
    build-essential \
    pkg-config \
    locales \
  && apt-get -q clean

# Build locales to avoid encoding issues with Scrapyd
RUN locale-gen en_GB.UTF-8

ENV LC_ALL=en_GB.UTF-8
ENV LANG=en_GB.UTF-8
ENV LANGUAGE=en_GB.UTF-8

# Set the working directory to /app
WORKDIR /wsf_scraper

# Copy the current directory contents into the container workdir
COPY ./wsf_scraping /wsf_scraper/wsf_scraping
COPY ./resources /wsf_scraper/resources
COPY ./pdf_parser /wsf_scraper/pdf_parser
COPY ./tools /wsf_scraper/tools

COPY ./api.py /wsf_scraper/api.py

COPY ./scrapy.cfg /wsf_scraper/scrapy.cfg
COPY ./requirements.txt /wsf_scraper/requirements.txt

RUN mkdir var
# Update pip
RUN pip3 install -qqq --upgrade pip
RUN rm -f /usr/bin/python && ln /usr/bin/python3 /usr/bin/python

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt
RUN pip install flask

# Run the flask file and expose the webservices
EXPOSE 8080

CMD ["python", "api.py"]
