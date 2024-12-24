import requests

import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


from datetime import datetime, timedelta
from datetime import datetime, timedelta, timezone
import pytz
from urllib.parse import urlencode, urljoin
KEEPME_URL=os.getenv("KEEP_ME_URL")

#http post services
def http_post(url='',headers={},data={}):
    try:   
        response=requests.post(
            url,
            json=data,
            headers=headers
        )
        responseData=response.json()
        print(responseData,url)
        return responseData
    except Exception as error:
          print("Something has been wrong api server hai   hh" + str(error))
          

#http get services         
def http_get(url='',headers={}):
    try:
        response=requests.get(
            url,
            headers=headers
        )
        responseData=response.json()
        # responseData={"status":404,"errorMessage":None,"userMessage":"Invalid key value 3","prompts":None,"messageNo":0,"result":
        #     {"company_id":"3","companyName":"Palmmind","chatbotName":"Palmmind","responseContentLine":70,"outOfContextResponse":"Sorry"}}
        return responseData
    except Exception as error:
        print("Something has been wrong in api server" + str(error))
        return None


def http_delete(url="", headers={}):
    try:
        response = requests.delete(
            url,headers=headers
        )
        if response.status_code == 200:
            print("Event successfully deleted.")
            return response
        else:
            print(f"Failed to delete event: {response.status_code} - {response.text}")
            return None
    except Exception as error:
        print("Something has been wrong in api server "+str(error))
        return None


async def calculate_time_seconds(start_time_str:str, tz_str:str):
    try:
        start_time = datetime.strptime(start_time_str[:16],"%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        local_tz = pytz.timezone(tz_str)
        now_time = datetime.now(local_tz)
        now_time_utc = now_time.astimezone(timezone.utc)
        time_difference = (start_time-now_time_utc).total_seconds()
        if time_difference < 0:
            return (8*60*60) #1 hour if past time
        return int(time_difference)
    except Exception as e:
        return (8*60*60)
    
def buildUrl(base_url, endpoint, queryParams):
    url = urljoin(base_url, endpoint)
    query = urlencode(queryParams, safe=":+")
    return f"{url}?{query}"



async def get_branch_details_from_orgid(org_id:str=None, branch_id:str=None, region_id:str=None):
    try:
        if org_id:
            base_url = KEEPME_URL
            endpoint = f"/api/bot/get-bot/{org_id}"
            query_params = {}
            if branch_id:
                query_params["branch"] = branch_id
            if region_id:
                query_params["region"] = region_id


            url = buildUrl(base_url, endpoint, query_params)
            headers = {
            "apikey": "12345",
                "Content-Type": "application/json"
            }
            print("url is==============",url)
            response = requests.get(url=url, headers=headers)  
            response = response.json()  
            if "data" in response:
                return response
            else:
                return None
    except Exception as e:
        print(f"Error ===== {e}")
        return None


async def process_search_response(search_response, sender, metadata):
    if not isinstance(search_response, dict):
        return {"result": search_response, "sender": sender}
    
    print("Search response is======================",search_response)

    org_key = "organization_id" 
    branch_key = "branch" 

    if org_key in search_response and branch_key in search_response:
        json_response = await get_branch_details_from_orgid(
            org_id=search_response[org_key],
            branch_id=search_response[branch_key]
        )

        json_response_data = json_response.get("data")

        # print("json_response_data===========================",json_response_data)

        to_update = {
            "org_id": search_response[org_key],
            "branch": search_response[branch_key],
        }

        if json_response_data:
            # metadata["gdprLlm"] = json_response_data.get("gdprLlm", None)
            metadata["type"] = json_response_data.get("branch", {}).get("type")
            to_update.update({
                "organization_name": json_response_data.get("client", {}).get("name", ""),
                "chatbot_name": json_response_data.get("name", ""),
                "welcome_message": json_response_data.get("welcomeMessage"),
                "details": {
                    "client": json_response_data.get("client", {}),
                    "branch": json_response_data.get("branch", {}),
                },
                "prompt": json_response_data.get("prompt", ""),
                "venue_id": json_response_data.get("branch", {}).get("venueId", ""),
                "region_id": json_response_data.get("branch", {}).get("region"),
                "useRegion": json_response_data.get("useRegion"),
                "metadata": metadata
            })



            if "oldQuery" in search_response:
                to_update["query"] = search_response.get("oldQuery")

            return to_update
        return to_update
