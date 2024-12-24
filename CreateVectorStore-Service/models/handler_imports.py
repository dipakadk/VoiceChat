import os
from queue import Queue
from models.new_handler import NewCallbackHandler
from langchain_openai import ChatOpenAI
tool_queue = Queue()
tool_handler = NewCallbackHandler(queue=tool_queue) 
api_key = os.getenv('OPEN_API_KEY_GPT_NEW')
def get_streaming_llm(model:str='gpt-3.5-turbo'):
    streaming_llm = ChatOpenAI(api_key=api_key, streaming=True, callbacks = [tool_handler])
    return streaming_llm
  