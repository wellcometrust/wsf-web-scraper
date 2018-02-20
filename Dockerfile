# Use an official Python runtime as a parent image
FROM ubuntu:16.04

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

RUN apt-get update -qq
RUN apt-get upgrade -qqy

# Install Scrapy and Textract dependencies
RUN apt-get install -qqqy \
    python3 \
    python3-dev \
    gcc \
    python3-pip \
    libpoppler-cpp-dev \
    poppler-utils \
    build-essential \
    pkg-config \
    locales

RUN locale-gen en_GB.UTF-8

ENV LC_ALL=en_GB.UTF-8
ENV LANG=en_GB.UTF-8
ENV LANGUAGE=en_GB.UTF-8

# Update pip
RUN pip3 install -qqq --upgrade pip
RUN rm -f /usr/bin/python && ln /usr/bin/python3 /usr/bin/python
# Install any needed packages specified in requirements.txt
RUN pip3 install -qqq -r requirements.txt
RUN pip3 install -qqq scrapyd scrapyd-client

COPY ./scrapyd.conf /etc/scrapyd/
VOLUME /etc/scrapyd/ /var/lib/scrapyd/
EXPOSE 6800

RUN scrapyd & PID=$! && \
   echo "Waiting for Scrapyd to start" && \
   sleep 2 && \
   scrapyd-deploy && \
   kill $PID

CMD ["scrapyd"]
