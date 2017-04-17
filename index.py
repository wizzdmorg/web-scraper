from bs4 import BeautifulSoup
import requests
import sys
import os
import shutil
import argparse
from urllib.parse import urlparse, urljoin
from csv import DictWriter
from helpers import to_absolute

tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'li', 'span', 'a', 'img']

parser = argparse.ArgumentParser(description='Web scraper')
parser.add_argument('file', help='path to file containing target websites, one line for each')
parser.add_argument('--depth', type=int, help='how deep should the scraper follow links')
parser.add_argument('--no-image', help='do not download images', action='store_true')

args = parser.parse_args()

path = os.path.join(os.path.dirname(__file__), args.file)
with open(path) as f:
    sites = [a.replace('\n', '') for a in f.readlines()]

for host in sites:
    data = []
    visited = []
    queue = []

    main = urlparse(host.replace('\n', ''))
    base_dir = os.path.join('results', main.netloc)
    images_dir = os.path.join(base_dir, 'images')

    if not os.path.isdir(base_dir):
        os.mkdir(base_dir)
    if not os.path.isdir(images_dir):
        os.mkdir(images_dir)

    def scrape(url, depth=0):
        if args.depth is not None and depth > args.depth: return

        t = url.geturl()

        if t in visited: return

        html = requests.get(t).text
        visited.append(t)

        soup = BeautifulSoup(html, 'html.parser')
        elements = soup.find_all(tags)

        for el in elements:
            href = el.get('href')

            if not href and not el.string and not el.name == 'img': continue

            record = {
                'page': url.path,
                'tag': el.name,
                'text': el.string,
                'link': href,
                'image': el.src if el.name == 'img' else None
            }

            if not args.no_image and el.name == 'img' and el.get('src'):
                p = to_absolute(el.get('src'), host)
                filepath = os.path.join(images_dir, os.path.basename(p.path))

                if not os.path.exists(filepath):
                    response = requests.get(p.geturl(), stream=True)
                    with open(filepath, 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)
                    del response


            data.append(record)
            
            if href and href != '/':
                p = to_absolute(href, host)
                if p and p.netloc == main.netloc:
                    queue.insert(0, p)

        for link in queue:
            queue.remove(link)
            scrape(link, depth=depth + 1)
                        
    scrape(main)

    with open(os.path.join('results', main.netloc, 'texts.csv'), 'w') as f:
            w = DictWriter(f, fieldnames=['page', 'tag', 'text', 'link', 'image'])

            w.writeheader()
            w.writerows(data)
