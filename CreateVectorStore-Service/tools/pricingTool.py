from langchain_core.output_parsers import JsonOutputParser
output_parser = JsonOutputParser()
from langchain.schema.runnable import RunnableMap

from utils.get_prompts import get_prompts

intents = ['Membership and Joining', 'Membership Management', 'Payments and Finances', 'Freezing and Cancellations', 'Facilities and Amenities', 'Classes and Training', 'Feedback and Complaints', 'Membership Agreement', 'Rules', 'Class Schedule', 'Privacy Policy', 'Other','Opening Hours', 'Contact']

def general_pricing(self):
    
    def general_pricing_tool(**data):  
        pricing_prompt=get_prompts(None,'context_with_pricing_json',True,self.org_name,self.chatbot_name)

        query = data.get("query")
        database = self.database

        chain = RunnableMap({
            "context":lambda x: [k.page_content for k in database.similarity_search(x['question'],k=6)],
            "question": lambda x: x['question'],
            "location": lambda x: x["location"],
            "intents": lambda x: intents
        }) | pricing_prompt | self.llm | output_parser

        
        args={
            'question':query,
            'organization_name':self.org_name,
            'sender':self.sender,
            "chatbot_name":self.chatbot_name,
            "location": "Nepal"
            }

        response =  chain.invoke(args)

        if response.get("handled") in ["no", "'no'"]:
            self.unhandled_arguments = True
        self.user_intent = response.get("intent")
        return response.get("answer")

    
    return general_pricing_tool