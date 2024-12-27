from fastapi import APIRouter,HTTPException,Query
from typing import List,Optional,Dict
from datetime import date, datetime,timedelta, timezone
from dotenv import load_dotenv
import csv
from fastapi.responses import StreamingResponse
from io import StringIO
from bson import ObjectId
import json
from fastapi.concurrency import run_in_threadpool
import pandas as pd
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

automation_url = os.getenv("AUTOMATION_URL")
authorization_id = os.getenv("CREATE_CONFIRMATION_AUTHORIZATION_TOKEN")

social_media = [
    'https://www.puregym.com/blog/',
    'https://x.com/',
    'https://www.facebook.com/',
    'https://twitter.com/',
    'https://www.instagram.com/',
    'https://www.linkedin.com/',
    'https://www.youtube.com/',
    'https://www.tiktok.com/'
]
blog_keywords = ['blog', 'article', 'posts']


load_dotenv()
router = APIRouter()

# Function to extract links using Selenium (Non-async function)
def extract_links_blocking(url: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)
    
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
    )
    
    page_source = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(page_source, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True)]
    links = [urljoin(url, link) for link in links]

    filtered_links = [
        link for link in links
        if urlparse(link).scheme in ['http', 'https'] and
           not any(sm in link for sm in social_media)
    ]
    
    return list(set(filtered_links))


#testing routes
@router.get('/test')
async def test_app():
    return {"message":"running"}

