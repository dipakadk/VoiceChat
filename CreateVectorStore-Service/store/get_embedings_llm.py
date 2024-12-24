from langchain_openai import OpenAIEmbeddings,ChatOpenAI
# from langchain.embeddings import HuggingFaceEmbeddings
# from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import Optional


import os
from dotenv import load_dotenv
load_dotenv()

OPEN_API_KEY=os.getenv('OPEN_API_KEY')
OPEN_API_KEY_EMBEDING=os.getenv('OPEN_API_KEY_EMBEDING')
OPEN_API_KEY_GPT_NEW=os.getenv('OPEN_API_KEY_GPT_NEW')

class Embedings:
    
    def __init__(self, **kwargs):
        self.embedding_type:Optional[str] = kwargs.get('embedding_type',None)
        self.open_ai_embedings = OpenAIEmbeddings(openai_api_key=OPEN_API_KEY_EMBEDING)
        # self.huggingface_embedings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    
    def get_embedings(self):
        if not self.embedding_type:
          return None
        if self.embedding_type == "openai":
            return self.open_ai_embedings
        elif self.embedding_type == "huggingface":
            return self.huggingface_embedings
        else:
            return None
         
    def get_llm(self,temperature:int=0,modal:str='gpt-4o'):
        if self.embedding_type == "openai":
            OPEN_API_KEYs= OPEN_API_KEY if modal=='gpt' else OPEN_API_KEY_GPT_NEW
            print("==========",OPEN_API_KEYs,"heeelelelel",modal)
            return ChatOpenAI(openai_api_key=OPEN_API_KEYs, temperature=temperature or 0, model=modal)
        #do it for other embeding type
        return None
    
