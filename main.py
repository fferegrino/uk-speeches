import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Set
from slugify import slugify
import json

def find_links_in_index(index_url):
    page = requests.get(index_url)
    soup = BeautifulSoup(page.text, 'html.parser', preserve_whitespace_tags=["p"])

    entries = soup.find('div', class_='cm-entry-summary')
    links = entries.find_all('a')
    
    return [
        (link.text, link['href']) for link in links
    ]

def load_saved_index(letter) -> Set[str]:
    record = Path(f"record/{letter}.txt")
    if record.exists():
        with open(record) as f:
            return set(f.read().splitlines())
    return set()

def save_index(letter, links):
    record = Path(f"record/{letter}.txt")
    with open(record, 'w') as f:
        f.write('\n'.join(sorted(links)))
    

import requests
import html2text
from bs4 import BeautifulSoup

def remove_host_from_url(url):
    # Remove https://www.ukpol.co.uk/ from the url
    return url[23:]


html_converter = html2text.HTML2Text()
html_converter.body_width = 0

def turn_html_into_markdown(html):
    return html_converter.handle(str(html.prettify()))

def download_speech(speech_url):
    page = requests.get(speech_url)
    soup = BeautifulSoup(page.text, 'html.parser', preserve_whitespace_tags=["p"])
    article = soup.find('article')
    title = article.find('h1')
    post_categories = article.find('div', class_='cm-post-categories')
    categories = post_categories.find_all('a')
    metadata = article.find('div', class_='cm-below-entry-meta')
    post_date = metadata.find('span', class_='cm-post-date')
    author = metadata.find('span', class_='cm-author')
    tag_links = metadata.find('span', class_='cm-tag-links')
    tags = tag_links.find_all('a')

    metadata_dict = {
        "url": speech_url,
        "title": title.text.strip(),
        'post_date': post_date.text.strip(),
        'author': author.text.strip(),
        'tags': [{"text":tag.text, "url":remove_host_from_url(tag['href'])} for tag in tags],
        "categories": [{"text":category.text, "url":remove_host_from_url(category['href'])} for category in categories],
    }

    content = article.find('div', class_='cm-entry-summary')

    summary = None
    pharagraphs = []

    for child in content.find_all(recursive=False):
        if child.name == 'p':
            if summary is None and (em := child.find('em')):
                summary = child.text.strip()
            else:
                pharagraphs.append(
                    turn_html_into_markdown(child)
                    )
        elif child.name == 'ul' or child.name == 'ol':
            for li in child.find_all('li'):
                pharagraphs.append(
                    turn_html_into_markdown(li))
        elif len(child.name) == 2 and child.name[0] == 'h':
            pharagraphs.append(
                turn_html_into_markdown(child))
        else:
            print(f"Unknown tag: {child.name}")

    if summary is not None:
        metadata_dict['summary'] = summary

    metadata_dict['content'] = [p.strip() for p in pharagraphs if p.strip()]
    
    # print(metadata_dict)
    return metadata_dict

# download_speech("https://www.ukpol.co.uk/rishi-sunak-2015-article-on-farming/")

index = find_links_in_index("https://www.ukpol.co.uk/speeches/")


for letter, index_url in index:
    saved_links = load_saved_index(letter)
    index_data_path = Path(f"data/{letter}")
    index_data_path.mkdir(parents=True, exist_ok=True)
    downloaded_links = set()
    try:
        for title, speech_url in find_links_in_index(index_url):
            if speech_url in saved_links:
                continue

            print(f"Downloading {title}")

            try:
                speech = download_speech(speech_url)

                slugified_title = slugify(title)

                with open(index_data_path / f"{slugified_title}.json", 'w') as f:
                    json.dump(speech, f, indent=4)

                downloaded_links.add(speech_url)
            except Exception as e:
                print(f"Failed to download {speech_url}")
    except Exception as e:
        print(f"Failed to download {index_url}")
        break
    finally:
        save_index(letter, saved_links.union(downloaded_links))
    

        
