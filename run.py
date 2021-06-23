#!/usr/bin/env python3

# stdlib imports
import logging
import pathlib
import re
import sys

# third-party impots
import bs4
from github import Github
import requests

URL = 'https://covid19.min-saude.pt/pedido-de-agendamento'
# URL = 'http://localhost:12345/test.html'

ACCESS_TOKEN_FILENAME = '.that-thingg.github_access_token'

def run():
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    access_token = read_access_token()
    github = Github(access_token)
    repo = github.get_user().get_repo('that-thing')
    previously_published_releases = published_releases(repo)

    raw_html_bytes = fetch_page()
    if raw_html_bytes is None:
        sys.exit(1)

    raw_html = raw_html_bytes.encode('UTF-8')
    minimum_age = parse_minimum_age(raw_html)
    if minimum_age is None:
        sys.exit(1)

    release_name = new_release_name(minimum_age)
    if release_name not in previously_published_releases:
        logging.info('New release! %s' % release_name)
        release_message = new_release_message(minimum_age)
        publish_release(repo, release_name, release_message)
    else:
        logging.info('No new release')

def read_access_token():
    filename = pathlib.Path.home() / ACCESS_TOKEN_FILENAME
    with open(filename, 'r') as f:
        return f.read().strip()

def fetch_page():
    request_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
    }

    return perform_http_request(URL, request_headers)

def perform_http_request(url, request_headers):
    full_request_headers = headers_to_make_us_look_like_a_browser()
    full_request_headers.update(request_headers)

    logging.info('Fetching "%s"...' % url)
    response = requests.get(url, headers=request_headers)
    if response.status_code == 200:
        return response.text
    else:
        logging.error('Failed to fetch: HTTP %d' % response.status_code)

def headers_to_make_us_look_like_a_browser():
    return {
        # use the most common user agent as available in:
        # * https://techblog.willshouse.com/2012/01/03/most-common-user-agents/
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'gzip',
        'Connection': 'keep-alive'
    }.copy()

def parse_minimum_age(raw_html):
    soup = bs4.BeautifulSoup(raw_html, features='html.parser')
    pedido_node = soup.find('div', {'id': 'pedido_content', 'class': 'single_content'})
    if pedido_node is None:
        logging.error('Could not find `pedido_node` in page')
        return

    sentence_node = pedido_node.find('h3', {'class': 'has-text-color'})
    if sentence_node is None:
        logging.error('Could not find `sentence_node` in page')
        return

    text = sentence_node.text
    #regex = r'Tem (?P<age>[0-9]{1,2}) ou mais anos e ainda nÃ£o foi vacinado(a)?'
    regex = r'Tem (?P<age>[0-9]{1,2}) ou mais anos e ainda não foi vacinado(a)?'
    match = re.match(regex, text)
    if match is None:
        logging.error('Regex failed to match age')
        return

    age_str = match.groupdict()['age']
    age = int(age_str)
    return age

def new_release_name(minimum_age):
    return 'vacina-para-%d-anos-ou-mais' % minimum_age

def new_release_message(minimum_age):
    return 'A vacina está agora disponível para quem tenha %d ou mais anos de idade.' % minimum_age

def published_releases(repo):
    releases = repo.get_releases()
    return [release.title for release in releases]

def publish_release(repo, name, message):
    repo.create_git_release(name, name, message)

if __name__ == '__main__':
    run()
