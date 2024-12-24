from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableMap
from urllib.parse import urlencode, urljoin
import os
from dotenv import load_dotenv, find_dotenv
from fastapi import HTTPException
import requests
from store.vectorestore_connection import VectorStore

from utils.get_prompts import get_prompts

intents = ['Membership and Joining', 'Membership Management', 'Payments and Finances', 'Freezing and Cancellations', 'Facilities and Amenities', 'Classes and Training', 'Feedback and Complaints', 'Membership Agreement', 'Rules', 'Class Schedule', 'Privacy Policy', 'Other', 'Opening Hours', 'Contact']


load_dotenv(find_dotenv())


keepme_url = os.getenv("KEEP_ME_URL")

def buildUrl(base_url, endpoint, queryParams):
    url = urljoin(base_url, endpoint)
    query = urlencode(queryParams, safe=":+")
    return f"{url}?{query}"


def getBranchesData(whatsapp_number:str=None, org_id:str=None, region_id:str=None):
    base_url = keepme_url
    endpoint = "/api/branches/branches-list"

    query_params = {}
    if whatsapp_number:
        query_params["whatsapp"] = whatsapp_number
    elif region_id:
        query_params["region"] = region_id
    elif org_id:
        query_params["client"] = org_id


    url = buildUrl(base_url, endpoint, query_params)
    headers = {
        "apikey": "12345",
        "Content-Type": "application/json"
    }
    response = requests.get(url=url, headers=headers)  
    response = response.json()    
    branches = []     
    if not response or "data" not in response:
        raise HTTPException(status_code=400, detail=f"No data found in the external API response. for {url}")
    else:
        branches = [{"ID": branch_info['branch']['_id'], "name": branch_info['branch']['name']}for branch_info in response.get("data")]
        return branches


def branchesOptionChain(query:str, data:list, llm):
    template = """
        Here is the user query provided inside double backticks: ``{query}``.
        Here is the list of available locations name inside triple backticks: ```{locations}```
        Your task is to create a human like friendly response by stating there are multiple locations, what location would they like to know ... about ? Also mention the location names.
        If only Single Location is available, state that there is only single location..., would they like to know....of it?
        Do not add any additional backticks or texts in your response.
    """
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"query": query, "locations": data})


def branchesMappingChain(query:str, locationname:str, data:list[dict], llm):
    template = """
        You only speak json.
        You are provided with the list of location names inside double backticks: ``{locations}``
        You are also provided with the name of the location name provided by the user inside triple bacticks: ```{location_name}```
        Here is also the user query for better reference, Query: {query}.
        Your task is to analyze the query and location name provided by the user and map with the similar name from the list of location names and fetch the ID from it.
        Your json output must be in format: 
        dict(
        "id":"Fetched corresponding ID from the chosen location"
        )
        If you cannot map or identify the location name from the list, keep it strictly as 'none'.
        Reminder that dict refers to curly brackets.
    """
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | JsonOutputParser()

    return chain.invoke({"query": query, "location_name":locationname, "locations":data})

def GetAnotherClub(self):
    def get_another_club_info(locationname: str, query:str):
        try:
            branches = getBranchesData(whatsapp_number=self.whatsapp_number, org_id=self.org_id, region_id=self.region_id)
            
            if len(branches) == 1 or locationname in ['', 'null', 'none', 'None', None]:
                return branchesOptionChain(query=query, data=[d.get("name") for d in branches],llm=self.llm)
            
            json_response = branchesMappingChain(query=query, locationname=locationname, data=branches, llm=self.llm)

            id = json_response.get("id")

            if id in ["none", "None", "'none'", None]:
                return branchesOptionChain(query=query, data=[d.get("name") for d in branches],llm=self.llm)

            collection_name=f'general_info_{str(id)}_{self.org_id}' 
            
            database = VectorStore.get_store(
                    self.embedings, 'milvus', collection_name, self.host, self.port
            )
            
            if not database:
                return f"No Details found for location {locationname}" 
            
            general_chain_prompts=get_prompts(None,'context_with_general_json',True,self.org_name,self.chatbot_name)
            
            chain = RunnableMap({
            "context":lambda x: [k.page_content for k in database.similarity_search(x['question'],k=6)],
            "question": lambda x: x["question"],
            "intents": lambda x: x["intents"]
            }) | general_chain_prompts | self.llm | JsonOutputParser()

            response = chain.invoke({"question": query, "intents": intents})
            
            if response.get("handled") in ["no", "'no'", "No"]:
                self.unhandled_arguments = False
            self.user_intent = response.get("intent")
            return response.get("answer")

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return get_another_club_info
