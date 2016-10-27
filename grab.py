#! /usr/bin/env python3

# System
import sys
import os
from argparse import ArgumentParser
import json

# Web
from urllib.request import urlopen
from bs4 import BeautifulSoup

# Logging
import logging
from logging import handlers
LOGGER = logging.getLogger(__name__)
SH = logging.StreamHandler()
FH = logging.handlers.RotatingFileHandler("grab.log", maxBytes=5 * 1000000, backupCount = 5)
SH.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
FH.setFormatter(logging.Formatter("%(asctime)s:%(lineno)s:%(funcName)s:%(levelname)s:%(message)s"))
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(SH)
LOGGER.addHandler(FH)
LOGGER.info("Beginning Session")
from pprint import pprint

DESCRIPTION = """Retrieves transcriptions of Donald J. Trump's speeches from the 2016 United States Presidential Election race."""
def getArgParser():
    parser = ArgumentParser(prog=sys.argv[0], description=DESCRIPTION)
    parser.add_argument('-r', '--retrieve-result-pages',
            metavar = "filename",
            dest="resultPagesFilename",
            nargs = 1,
            help="retrieves the result pages and saves it as filename")
    parser.add_argument('-a', '--article-list-filename',
            metavar = "filename",
            dest="articleListFilename",
            required = True,
            nargs = 1,
            help="file to save the list of transcript URLs to retrieve")
    parser.add_argument("-u","--url",
            metavar = "url",
            nargs = "?",
            dest="startUrl",
            help="url to start the traversal on")
    data = parser.add_mutually_exclusive_group()
    data.add_argument("-m", "--merge",
            action="store_true", default=False,
            help="merge from file")
    data.add_argument("-s", "--from-scratch",
            dest="fromScratch",
            action="store_true", default=False,
            help="do whatever we're doing from scratch")
    parser.add_argument("-l", "--limit",
            metavar="<num>",
            type=int, default=None,
            help="limit whatever we're doing to the given num")
    return parser

def saveDictionaryAsJSON(dictionary, filename, check = False):
    LOGGER.debug("Saving dictionary as JSON to '%s'", filename)
    if check and os.path.isfile(filename):
        LOGGER.warning("File already exists!")
        return False
    with open(filename, 'w') as file:
        json.dump(dictionary, file)
    return True

def openJSONAsDictionary(filename, check = False):
    LOGGER.debug("Loading JSON as dictionary:'%s'", filename)
    if check and not os.path.isfile(filename):
        LOGGER.error("File doesn't exist!")
        return None
    with open(filename, 'r') as file:
        return json.load(file)


def getPageText(url):
    htmlText = None
    LOGGER.debug("Opening:'%s'" % (url))
    with urlopen(url) as webpage:
        htmlText = webpage.read().decode('utf-8')
    return htmlText

def getTranscriptResultPages(startUrl, previousPages = {"pages" : [], "count" : 0}, limit = 5):

    # Retrieve Results Page
    LOGGER.debug("Retrieving results pages...")
    LOGGER.debug("Starting from %s" % startUrl)
    LOGGER.debug("Limiting to %d pages." % limit) if limit else LOGGER.debug("No limit to pages")
    previouslySeen = {}
    for seen in previousPages["pages"]:
        previouslySeen[seen['url']] = seen
    resultPages = previousPages
    pageUrl = startUrl
    nextPageButton = []
    count = 0

    while pageUrl and (not limit or count < limit):
        # Save Page Text
        pageString = None
        if pageUrl not in previouslySeen:
            try:
                pageString = getPageText(pageUrl)
            except Exception as e:
                LOGGER.error("Received error at %s:%s" % (pageUrl, e))
                break
            resultPages["pages"].append(
                    {"url" : pageUrl, "html" : pageString})
            count += 1
        else:
            pageString = previouslySeen[pageUrl]['html']
            LOGGER.warning("Already seen. Skipping %s" % pageUrl)

        # Move to Next Page
        bs = BeautifulSoup(pageString, "lxml")
        nextPageButton = bs.find_all("a", {"class" : "next page-numbers"})
        if len(nextPageButton) == 1:
            pageUrl = nextPageButton[0]["href"]
        else:
            pageUrl = None
            if len(nextPageButton):
                LOGGER.error("Encountered %d-many <a class='next page-number'..."
                        % (len(nextPageButton),))
    LOGGER.debug('Retrieved %d pages' % count)
    resultPages['count'] += count
    return resultPages

def getTranscriptUrlsFromResultPage(htmlText):
    urls = []
    bs = BeautifulSoup(htmlText, 'lxml')
    headlines = bs.find_all("h1", {"class" : "headline"})
    for h in headlines:
        name = h.text
        url = h.find("a")["href"]
        LOGGER.debug("Found '%s':%s" % (name, url))
        urls.append({"name" : name, "url" : url})
    return urls

def getTranscriptUrlList(startUrl, resultPagesFilename, fromScratch, limit = 5, merge = False):
    # Retrieve Results Pages
    resultPagesDict = None
    if not fromScratch:
        # Open From File
        LOGGER.debug("Opening from file: %s" % resultPagesFilename)
        resultPagesDict = openJSONAsDictionary(resultPagesFilename, check = True)
    if not resultPagesDict or fromScratch:
        LOGGER.debug("Retrieving from internet...")
        # Retrieve From Internet
        resultPagesDict = getTranscriptResultPages(startUrl, limit = limit)
    elif merge:
        LOGGER.debug("Merging with %s" % resultPagesFilename)
        resultPagesDict = getTranscriptResultPages(startUrl, previousPages = resultPagesDict, limit = limit)
    # Save Results Pages to file
    saveDictionaryAsJSON(resultPagesDict, resultPagesFilename)
    transcriptUrlsDict = {"transcripts" : []}
    for page in resultPagesDict["pages"]:
        LOGGER.debug("Getting transcript URLs for %s" % page["url"])
        transcriptUrlsDict["transcripts"].extend(getTranscriptUrlsFromResultPage(page["html"]))
    return transcriptUrlsDict

def getTranscriptPages(transcriptList):
    return

def main():
    # Parse Arguments
    parser = getArgParser()
    args = parser.parse_args()
    if args.resultPagesFilename:
        urls = getTranscriptUrlList(args.startUrl, args.resultPagesFilename[0], args.fromScratch, args.articleListFilename[0], args.limit, args.merge)
        saveDictionaryAsJSON(transcriptUrlsDict, args.articleListFilename)
    openJSONAsDictionary(args.articleListFilename[0])
    return 0

if __name__ == "__main__":
    sys.exit(main())
