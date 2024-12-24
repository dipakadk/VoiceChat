from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


async def check_details(self):

    async def check_for_user_details(query:str):
        template = """
            You are provided with chat history between you and the user.
            ### chat history provided under double backticks: ``{chat_history}``
            ### metadata provided under triple backticks, which may also contain information of the user. ```{metadata}```
            Details to find: {booking_tour_fields} of the user.
            You are also provided with the Current user query provided by the user inside single backticks: `{query}`
            Your task is to analyze the chat history and also the metadata and check if the provided details are available in the conversation or metadata.'
            Check only 'Human: ' part of the conversation and also check the full metadata if not empty.
            If the metadata contains a non-empty 'name' key, extract the 'fullname' and separate it into 'firstname' and 'lastname'.
            your response must be in json format in the provided format below as:
            dict(
            "firstname": "first name of the user if available in chat history or metadata",
            "lastname" : "last name of the user if available in chat history or metadata",
            "email": "email address of the user if available in chat history or metadata",
            "phone number": "phone number of the user if available in chat history or metadata"
            )
            If some of the details are not available in the conversation or metadata, set the value of the correspoding key to "Not provided".
            Make sure your json response do not contain any additional texts, tags or backticks.
        """

        # print("History======================",self.history)
        print("Metadata during check details==============",self.metadata)
        print()
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | JsonOutputParser()
        args = {
            "chat_history": self.history,
            "metadata": self.metadata,
            "booking_tour_fields":self.booking_tour_fields,
            "query": self.query
        }

        return await chain.ainvoke(args)
    
    return check_for_user_details