import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from langchain.docstore.document import Document
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter

from firecrawl import FirecrawlApp
from dotenv import load_dotenv
load_dotenv()
import os

fire_crawl_api = os.getenv("FIRE_CRAWL_API_KEY")

social_media = [
    'https://www.puregym.com/blog/',
    'https://x.com/',
    'https://www.facebook.com/',
    'https://twitter.com/',
    'https://www.instagram.com/',
    'https://www.linkedin.com/',
    'https://www.youtube.com/',
    'https://play.google.com/',
    'https://apps.apple.com/',
    'https://linkedin.com/'
]
blog_keywords = ['blog', 'article', 'posts']


def get_all_bind_urls(url: str) -> List[str]:
    is_xml = url.endswith('.xml')
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml' if is_xml else 'html.parser')
        
        if is_xml:
            links = [loc.text for loc in soup.find_all('loc')]
        else:
            links = [a['href'] for a in soup.find_all('a', href=True)]
            links = [urljoin(url, link) for link in links]
        filtered_blog = [url for url in links if not any(keyword in url.lower() for keyword in blog_keywords)]

        filtered_links = [
            link for link in filtered_blog
            if urlparse(link).scheme in ['http', 'https'] and
               not any(link.startswith(keyword) for keyword in social_media)
        ]
        
        return filtered_links
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

import re

def clean_scraped_data(text):
    cleaned_text = re.sub(r'\[.*?\]\(.*?\)', '', text)
    
    cleaned_text = re.sub(r'[\[\]()]', '', cleaned_text)
    
    cleaned_text = re.sub(r'\n+', '\n', cleaned_text)
    
    cleaned_text = re.sub(r'[!\\]', '', cleaned_text)
    
    cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text)
    
    return cleaned_text.strip()

    
splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=100)

def web_extractor(url: str,intent:str=None, region_id:str=None, branch:str=None) -> List[str]:
        documents = []
        try:
            app = FirecrawlApp(api_key=fire_crawl_api)
            response = app.scrape_url(url=url, params={"formats": ["markdown"]})
            response = response.get("markdown")
            finalResponse = clean_scraped_data(response)
            chunks = splitter.split_text(finalResponse)
            for index,chunk in enumerate(chunks):
                documents.append(Document(page_content=chunk.strip(),
                                        metadata={
                                                "source":url,
                                                "type":'url',
                                                "filename":url,
                                                "intent":intent,
                                                "region_id": region_id or "Default",
                                                "branch": branch or "Default"
                        }))

        except Exception as e:
            print(f"An error occurred while processing URL {url}: {e}")

        return documents