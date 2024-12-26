from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

import os
from dotenv import load_dotenv
load_dotenv()
llm = ChatOpenAI(api_key=os.getenv('OPEN_API_KEY'))
from langchain.schema.output_parser import StrOutputParser
from langchain.prompts import ChatPromptTemplate
import json
output_parser = StrOutputParser()
from langchain_core.output_parsers import JsonOutputParser

json_parser = JsonOutputParser()
from datetime import datetime,timezone
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())





import os
import json
import base64
import asyncio
import argparse
import time
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
import websockets
from dotenv import load_dotenv
import uvicorn
import re
from langchain_openai import OpenAIEmbeddings
load_dotenv()

from langchain.schema.runnable import RunnableMap
from langchain_core.output_parsers import StrOutputParser
string_parser= StrOutputParser()
import os
api_key = os.getenv('OPEN_API_KEY')
from langchain_openai import ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate
embeddings=OpenAIEmbeddings(api_key=api_key)

llm = ChatOpenAI(api_key=os.getenv('OPEN_API_KEY'))




today_date = datetime.now()
day_of_week = today_date.strftime("%A")
date = today_date.strftime("Year: %Y, Month: %m, Day: %d, %H:%M %p")