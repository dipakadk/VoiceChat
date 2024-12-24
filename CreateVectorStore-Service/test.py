from bs4 import BeautifulSoup
from typing import List

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


# def get_all_bind_urls(url: str) -> List[str]:
#     is_xml = url.endswith('.xml')
    
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.content, 'xml' if is_xml else 'html.parser')
        
#         if is_xml:
#             links = [loc.text for loc in soup.find_all('loc')]
#         else:
#             links = [a['href'] for a in soup.find_all('a', href=True)]
#             links = [urljoin(url, link) for link in links]
#         filtered_blog = [url for url in links if not any(keyword in url.lower() for keyword in blog_keywords)]

#         filtered_links = [
#             link for link in filtered_blog
#             if urlparse(link).scheme in ['http', 'https'] and
#                not any(link.startswith(keyword) for keyword in social_media)
#         ]
        
#         return filtered_links
#     except requests.RequestException as e:
#         print(f"Request failed: {e}")
#         return []
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return []

def get_all_bind_urls(url: str):
    app = FirecrawlApp(api_key=fire_crawl_api)
    scrape_result = app.scrape_url(url=url,params={"formats": ["markdown"]})
    

if __name__ == "__main__":
    get_all_bind_urls("https://www.fitnessfirst.com/sg/en/")

