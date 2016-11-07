#! /usr/bin/env python3

# System
import sys
import os
import errno
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
FH = logging.handlers.RotatingFileHandler("update.log", maxBytes=5 * 1000000, backupCount = 5)
SH.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(message)s"))
FH.setFormatter(logging.Formatter("%(asctime)s:%(lineno)s:%(funcName)s:%(levelname)s:%(message)s"))
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(SH)
LOGGER.addHandler(FH)
from pprint import pprint

# NLP
import re
from collections import defaultdict

DESCRIPTION = """Extracts transcriptions of Donald J. Trump's speeches from the 2016 United States Presidential Election race."""
def get_arg_parser():
    parser = ArgumentParser(prog=sys.argv[0], description=DESCRIPTION)
    parser.add_argument("-i", "--info",
            help = "set console logging output to INFO")
    parser.add_argument("-d", "--debug",
            help = "set console logging output to DEBUG")
    parser.set_defaults(
            list_start_url              = None,
            transcript_urls_filename    = None,
            raw_pages_filename          = None,
            keywords                    = None,
            texts_filename              = None
            )

    # Sub Parsers
    subparsers = parser.add_subparsers(help = "Actions")
    update_parser = subparsers.add_parser("update", 
            help="updates the list of URLs containing transcripts")
    retrieve_parser = subparsers.add_parser("retrieve",
            help = "retrieves the raw HTML from the list of URLs filtering by lower case keywords existing in the name of the article")
    extract_parser = subparsers.add_parser("extract",
            help = "extracts text from the raw HTML")
    # Update URL List
    update_parser.add_argument(
            metavar = "<http://starturl.com/>",
            default = None,
            dest = "list_start_url",
            help = "URL of webpage with list of transcript URLs ")
    update_parser.add_argument(
            metavar = "<transcriptUrls.json>",
            default = None,
            dest = "transcript_urls_filename",
            help = "path to JSON of transcript URLs and their titles")

    # Retrieving Raw HTML
    retrieve_parser.add_argument(
            metavar = "<transcriptUrls.json>",
            default = None,
            dest = "transcript_urls_filename",
            help = "path to JSON of transcript URLs and their titles")
    retrieve_parser.add_argument(
            metavar = "<keyword1,keyword2,...>",
            default = None,
            dest = "keywords",
            help = "comma separated list of all keywords that must appear in name of article to retrieve")
    retrieve_parser.add_argument(
            metavar = "<rawPagesFile.json>",
            default = None,
            dest = "raw_pages_filename",
            help = "path to JSON of transcript pages raw HTML")

    # Extracting Text
    extract_parser.add_argument(
            metavar = "<rawPagesFile.json>",
            default = None,
            dest = "raw_pages_filename",
            help = "path to JSON of transcript pages raw HTML")
    extract_parser.add_argument(
            metavar = "<textDocuments.json>",
            default = None,
            dest = "texts_filename",
            help = "path to JSON of extracted texts")
    return parser

def save_as_json(object, filename, check = False):
    LOGGER.debug("Saving dictionary as JSON to '%s'", filename)
    if check and os.path.isfile(filename):
        LOGGER.warning("File already exists!")
        return False
    with open(filename, 'w') as file:
        json.dump(object, file)
    return True

def open_json(filename, check = False):
    LOGGER.debug("Loading JSON as dictionary:'%s'", filename)
    if check and not os.path.isfile(filename):
        LOGGER.error("File doesn't exist!")
        return None
    with open(filename, 'r') as file:
        return json.load(file)

def get_page_text(url):
    htmlText = None
    LOGGER.debug("Opening:'%s'" % (url))
    try:
        with urlopen(url) as webpage:
            htmlText = webpage.read().decode()
    except Exception as e:
        LOGGER.error(e)
        return None
    return htmlText

def get_urls_from_page(result_page_url):
    url_names = []
    next_page_url = None

    LOGGER.debug("Retrieving transcript URLs from '%s'" % result_page_url)
    page_string = get_page_text(result_page_url)
    if not page_string:
        LOGGER.warning("Failed to retrieve html for %s" % result_page_url)
        return url_names, next_page_url

    LOGGER.debug("Parsing")
    bs = BeautifulSoup(page_string, "lxml")
    headlines = bs.find_all("h1", {"class" : "headline"})
    for h in headlines:
        name = h.text
        url = h.find("a")["href"]
        #LOGGER.debug("Found '%s':%s" % (name, url))
        url_names.append({"url" : url, "name" : name})

    LOGGER.debug("Finding next page URL")
    next_page_button = bs.find_all("a", {"class" : "next page-numbers"})
    if len(next_page_button) == 1:
        next_page_url = next_page_button[0]["href"]
    else:
        next_page_url = None
        if len(next_page_button):
            LOGGER.error("Encountered %d-many <a class='next page-number':"
                    % (len(next_page_button), next_page_button))
    LOGGER.debug("Next Page:'%s'" % next_page_url)
    return url_names, next_page_url

def get_transcript_urls(start_page_url, already_seen_urls = set()):
    LOGGER.debug("Grabbing URLs and name of transcripts from search page")
    LOGGER.debug("Starting at %s" % start_page_url)
    next_page = start_page_url
    url_names = []
    result_urls = []
    while next_page:
        result_urls.append(next_page)
        new_urls, next_page = get_urls_from_page(next_page)
        for u in new_urls:
            if u["url"] not in already_seen_urls:
                LOGGER.debug("Adding:%s:%s" % (u["name"], u["url"]))
                url_names.append(u)
            else:
                LOGGER.warning("skipping:%s:%s" % (u["name"], u["url"]))
        if any(u["url"] in already_seen_urls for u in new_urls):
            LOGGER.debug("Exiting")
            break
        LOGGER.debug("Moving onto %s" % next_page)
    return url_names, result_urls

def get_transcript_html(url_names, keywords, already_downloaded_urls = set()):
    url_name_htmls = []
    [LOGGER.debug("Filtering name by: %s" % k.lower()) for k in keywords]
    to_download = [(un["url"], un["name"]) for un in url_names 
                if
                un["url"] not in already_downloaded_urls
                and
                all([x in un["name"].lower() for x in keywords])]
    speeches = {transcript_basename(name) for url, name in to_download}
    LOGGER.debug("Number of articles to retrieve: %d" % len(to_download))
    LOGGER.debug("Number of speeches to retrieve: %d" % len(speeches))
    for url, name in to_download:
        basename = transcript_basename(name)
        html = get_page_text(url)
        url_name_htmls.append({"url" : url, "name" : name, "html" : html})
    return url_name_htmls

def transcript_basename(name):
    basename = re.sub(" – Part [\d+]","", name).strip()
    if not (basename.endswith("2015") or basename.endswith("2016")):
        basename = re.sub("([\w])[\d+]$","\g<1>", basename)
    return basename

def strip_html(html):
    paras = []
    bs = BeautifulSoup(html, "lxml")
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
        if "Leave a Comment" == text:
            continue
        if not text:
            continue
        text = re.sub("…","...", text)
        paras.append(text if text[-1] == ' ' else text + ' ')
    return "\n".join(paras)

def extract_text(pages):
    transcripts = defaultdict(list)
    for p in pages["transcripts"]:
        LOGGER.debug("Stripping HTML from %s" % p["name"])
        transcripts[transcript_basename(p["name"])].append(strip_html(p["html"]))
    texts = []
    for name, parts in transcripts.items():
        texts.append({"name" : name, "text" : "\n".join(parts)})
    return texts

def main():
    # Parse Arguments
    parser = get_arg_parser()
    args = parser.parse_args()

    print(args)

    # Logging Information
    if args.info:
        SH.setLevel(logging.INFO)
    if args.debug:
        SH.setLevel(logging.DEBUG)

    start_page_url              = args.list_start_url
    transcript_urls_filename    = args.transcript_urls_filename
    raw_pages_filename          = args.raw_pages_filename
    keywords                    = [k for k in map(lambda x: x.lower(), args.keywords.split(","))] if args.keywords else None
    texts_filename              = args.texts_filename

    # Get Transcript URLs
    urls = None
    if transcript_urls_filename:
        urls = open_json(transcript_urls_filename, check = True)
        if start_page_url:
            if not urls:
                urls = {"transcripts" : [], "results" : []}
            new_urls, result_urls = get_transcript_urls(start_page_url, {u["url"] for u in urls["transcripts"]})
            LOGGER.info("Found %d new URLs" % len(new_urls))
            LOGGER.info("First result page looked at:'%s'" % (result_urls[0]))
            LOGGER.info("Last  result page looked at:'%s'" % (result_urls[-1]))
            urls["transcripts"].extend(new_urls)
            urls["results"] = sorted([r for r in set(urls["results"] + result_urls)])
            save_as_json(urls, transcript_urls_filename)
    if urls:
        LOGGER.info("Number of Transcript URLs  : %d" % len(urls["transcripts"]))
        LOGGER.info("Number of Result Pages Seen: %d" % len(urls["results"]))

    # Get Transcript HTML
    if raw_pages_filename:
        if not texts_filename and not urls:
            LOGGER.fatal("Transcript URLs file is required. Exiting.")
            return errno.ENOENT
        pages = open_json(raw_pages_filename, check = True)
        if not pages:
            pages = {"transcripts" : []}
        if not texts_filename:
            new_htmls = get_transcript_html(urls["transcripts"], keywords, {p["url"] for p in pages["transcripts"]})
            LOGGER.info("New Downloads: %d" % len(new_htmls))
            pages["transcripts"].extend(new_htmls)
            save_as_json(pages, raw_pages_filename)

    # Convert HTML to Text
    if texts_filename:
        if not pages:
            LOGGER.fatal("Transcript HTML file is required. Exiting.")
            return errno.ENOENT
        texts = extract_text(pages)
        LOGGER.info("Texts: %d" % len(texts))
        save_as_json(texts, texts_filename)
    return 0

if __name__ == '__main__':
    LOGGER.info("Beginning Session")
    rtn = main()
    LOGGER.info("Ending Session")
    sys.exit(rtn)
