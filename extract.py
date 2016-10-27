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
FH = logging.handlers.RotatingFileHandler("extract.log", maxBytes=5 * 1000000, backupCount = 5)
SH.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
FH.setFormatter(logging.Formatter("%(asctime)s:%(lineno)s:%(funcName)s:%(levelname)s:%(message)s"))
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(SH)
LOGGER.addHandler(FH)
LOGGER.info("Beginning Session")
from pprint import pprint

# NLP
import re

DESCRIPTION = """Extracts transcriptions of Donald J. Trump's speeches from the 2016 United States Presidential Election race."""
def getArgParser():
    parser = ArgumentParser(prog=sys.argv[0], description=DESCRIPTION)
    parser.add_argument("articlesFilename",
            metavar="<articles.json>", 
            help="path (absolute or relative) to the transcript htmls")
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

def getEachText(transcriptDictionary, limit = None):
    eachText = {"texts" : []}
    LOGGER.debug("Parsing %d transcripts..." 
            % (limit if limit else len(transcriptDictionary["pages"]),))
    for t in transcriptDictionary["pages"]:
        if "transcript" not in t["name"].lower():
            LOGGER.warning("Not a transcript:%s" % t["name"])
            continue
        paras = []
        bs = BeautifulSoup(t["html"], "lxml")
        for p in bs.find_all("p"):
            text = p.text
            if "…" == text:
                continue
            if "###" == text:
                continue
            if "Partial transcript" in text:
                continue
            if "Excerpts from a" in text:
                continue
            if "Donald Trump:" in text:
                continue
            if "Transcript:" in text:
                continue
            if "Category:" in text:
                continue
            if "RSS Feed" in text:
                continue
            if "Posted by News Editor" in text:
                continue
            if "What The Folly?!" in text:
                continue
            if "Comments are closed." == text:
                continue
            if not text:
                continue
            paras.append(text if text[-1] == ' ' else text + ' ')
        eachText["texts"].append({"name" : t["name"], "text" : ''.join(paras)})
    eachText["count"] = len(eachText["texts"])
    LOGGER.debug("Parsed %d texts" % eachText["count"])
    return eachText

def main():
    # Parse Arguments
    parser = getArgParser()
    args = parser.parse_args()
    transcriptDictionary = openJSONAsDictionary(args.articlesFilename)
    texts = getEachText(transcriptDictionary)
    saveDictionaryAsJSON(texts, "trumpText.json")
    return 0

if __name__ == '__main__':
    rtn = main()
    sys.exit(rtn)
