import fnmatch
import os
import threading
import time
from queue import Queue

import requests
from bs4 import BeautifulSoup
from goose3 import Goose

# Initialization
# Threads and Semaphores

semaphore = threading.Semaphore(5)
lock_doc_id = threading.Lock()
lock_all_queues = threading.Lock()

toCrawl = Queue().queue
crawled = Queue().queue

homeUrl = ''

directory = ''
doc_id = 1
DOCS_TO_SAVE = 1000
MIN_WORD_IN_DOC = 150


def create_doc(url, title, meta_keywords, date, content):
    global doc_id, directory
    lock_doc_id.acquire()
    this_doc_id = doc_id
    doc_id = doc_id + 1
    lock_doc_id.release()
    doc_name = directory + str(this_doc_id) + '.txt'
    doc = open(doc_name, 'w')
    doc.write("URL: " + url + '\n')
    doc.write("TITLE: " + title + '\n')
    doc.write("META-KEYWORDS: " + meta_keywords + '\n')
    doc.write("DATE: " + date + '\n')
    doc.write("DOC ID: " + str(this_doc_id) + '\n')
    doc.write("CONTENT: " + content + '\n')
    doc.close()
    print("Created Doc: " + doc_name + "\n")


def check_for_content(raw_html, soup):
    # Goose package used to extract Articles from News Websites only
    global homeUrl
    g = Goose()

    try:
        article = g.extract(raw_html=raw_html.content)
    except:
        return

    content = article.cleaned_text
    content = handle_encoding(content)
    if len(content.split()) < MIN_WORD_IN_DOC:
        return
    # todo might need to change the @attrs here depending on html tag of website crawled
    page_title = soup.title.string.replace("\n", "")
    page_title = handle_encoding(page_title)
    keywords = soup.findAll(attrs={"name": "news_keywords"})
    keywords = handle_encoding(keywords, True)
    date = soup.findAll(attrs={"name": "publish-date"})
    date = handle_encoding(date, True)
    create_doc(homeUrl, page_title, keywords, date, content)


def handle_encoding(input_string, with_find_all=False):
    if with_find_all:
        if len(input_string) == 0:
            return ""
        if isinstance(input_string[0]['content'], str):
            input_string = input_string[0]['content']
        elif isinstance(input_string[0]['content'], bytes):
            input_string = str(input_string[0]['content'].decode('utf-8'))
        return input_string
    elif input_string:
        if isinstance(input_string, bytes):
            input_string = str(input_string.decode('utf-8'))
        return input_string


def threads_work(link, thread_number):
    global homeUrl, DOCS_TO_SAVE, MIN_WORD_IN_DOC
    # print " Thread #" + str(thread_number) + " : Link : " + str(link)
    raw_html = requests.get(link)
    # Extract only html/text links
    if "text/html" not in raw_html.headers["content-type"]:
        semaphore.release()
        # print " Thread #" + str(thread_number) + " : REJECTED as Non-HTML Page"
        return
    time.sleep(0.5)
    soup = BeautifulSoup(raw_html.content, "html.parser")
    check_for_content(raw_html, soup)

    for a_set in soup.find_all('a'):
        try:
            next_link = str(a_set.get('href'))
        except:
            continue
        # Relative Link and External Link
        if homeUrl not in next_link:
            mod_link = homeUrl + next_link
            lock_all_queues.acquire()
            if mod_link not in crawled and mod_link not in toCrawl and not fnmatch.fnmatch(mod_link, '*http*http*'):
                toCrawl.append(mod_link)
            lock_all_queues.release()
        # Internal Link
        else:
            lock_all_queues.acquire()
            if next_link not in crawled and next_link not in toCrawl:
                toCrawl.append(next_link)
            lock_all_queues.release()
    # print " Thread #" + str(thread_number) + " : Finished"
    semaphore.release()


# Main function to start crawler
def begin_crawling(url_from_user, directory_from_user):
    global homeUrl, directory
    homeUrl = url_from_user
    directory = directory_from_user

    # Create Directory
    if not os.path.exists(directory):
        os.makedirs(directory)
    # all_files_in_dir = glob.glob(directory + '*')
    # for i in all_files_in_dir:
    #     os.remove(i)

    toCrawl.append(homeUrl)
    i = 0
    while 1:
        semaphore.acquire()

        # Check for Number of Docs created
        lock_doc_id.acquire()
        if doc_id > DOCS_TO_SAVE:
            print("%d Documents created and exiting.", DOCS_TO_SAVE)
            break
        lock_doc_id.release()

        lock_all_queues.acquire()
        if toCrawl:
            link = toCrawl.pop()
            crawled.append(link)
            lock_all_queues.release()
            i = i + 1
            t = threading.Thread(target=threads_work, args=(link, i))
            t.start()
            # print "Started Thread #" + str(i) + "\n"
        else:
            semaphore.release()
            lock_all_queues.release()
