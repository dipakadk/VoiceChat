
from langchain_core.output_parsers import JsonOutputParser
output_parser = JsonOutputParser()
from langchain.schema.runnable import RunnableMap


intents = ['Membership and Joining', 'Membership Management', 'Payments and Finances', 'Freezing and Cancellations', 'Facilities and Amenities', 'Classes and Training', 'Feedback and Complaints', 'Membership Agreement', 'Rules', 'Class Schedule', 'Privacy Policy', 'Other', 'Opening Hours', 'Contact']

from datetime import datetime, timezone



from langchain_core.prompts import ChatPromptTemplate

def getBranchlessPrompt():
    template = """
    You are a helpful assistant your primary task is to give the accurate, concise and helpful response from the context provided to the users queries.
    The query is be given in double backticks: ``{question}``
    The relevant context is be provided in triple backticks: ```{context}```
    <important>
    1. AVOID ANSWERING TO QUERIES THAT ARE OUT OF THE CONTEXT PROVIDED. DOING SO WILL MAKE YOU PENALIZED.
    2. IF THE QUERY IS OUT OF CONTEXT, REPLY POSITIVELY AND EXPLAIN THAT YOU DO NOT HAVE FULL INFORMATION ON THAT. 
    3. CAREFULLY ANALYZE THE CONTEXT BEFORE RESPONDING. BE SPECIFIC TO THE QUERY ASKED. YOUR ANSWERS SHOULD BE PRECISE, CONCISE, AND ONLY TO THE POINT, ADDRESSING THE FULL QUESTION WITHOUT UNNECESSARY DETAILS THAT ARE NOT ASKED IN THE QUERY.                
    </important>
    <class_schedule>
                You are provided with the current date, day, and time.
                ## CURRENT DATE: {today}
                ## CURRENT DAY: {weekday}
                ## CURRENT TIME: {time}
                If the class schedule is available in link format provide the same link as response.
                If a user queries about class schedules (e.g., yoga), follow these steps only if the date and time is available in the context to ensure accuracy:  
                1. **Check Future Availability:** Analyze the context to determine if the mentioned class is available on a future date from `{today} {time}`. Avoid recommending schedules before `{today} {time}`, even if the weekday `{weekday}` is the same, as schedules may vary.  
                2. **Understand User Intent:** Assess the user's preferred schedule and verify if it matches the available classes.  
                3. **Handle Unavailability:** If no classes are available after `{today} {time}`, state: "There are no classes available."  
                4. **Recommend Future Classes Only:** Mention only the classes available from `{today} {time}` onwards.  
                5. **Respond to Ambiguity:** If the query does not specify a class name, suggest a few classes available from `{today} {time}`.  

                Ensure responses are concise, accurate, and focus solely on future schedules.
                </class_schedule>

    <case>
                if the context contains answers both in english and arabic language, check for the answers in the context in {language} language.
                If you cannot find answer in {language} language, then only refer to the answer in another language.
                Do not follow this rule if the answers in the context in only english language.
                Incase if you are referring to answers in arabic, refer to complete arabic answer.
    </case>
    When mentioning the prices, mention the currency of the prices which is as it is available in the context.
    REMEMBER YOU SHOULD STRICKLY FOLLOW THE INSTRUCTIONS INSIDE <important></important> tag.
    Your response must be in json format with fields specified as: dict(
        "answer": "Your response to the user in string",
        "handled": " 'yes' if you were able to provide answer according to the context available, 'no' if you were not able to provided answer from the context available.",
        "intent": "intent of the user, select from one of these list of intents: {intents}"
    )
    Remember that dict refers to curly brackets.
    Do not add any backticks or additional texts, just the json.
    """
    prompt = ChatPromptTemplate.from_template(template)
    return prompt

def getBranchPrompt():
    template = """
        You are a helpful assistant, your primary task is to give the accurate, concise and helpful response from the contexts provided to the user queries.
        You represent {branch_name} club branch of {client_name}. You are provided with the user query inside double backticks: ``{question}``.
        Here is the relevant context only specific to {branch_name} branch inside triple backticks: ```{context_branch}```

        Here is the relevant context specific to all branches of {client_name} inside triple backticks: ```{context_club}```

        Your task is to analyze the user query and the two different contexts and provide a response according to it. 
        Here are the rules you need to follow while providing the response:
        Rule no 1: Do not provide response by combining answers from two different contexts, unless there is a complete requirement of it.
        Rule no 2: Prioritize the context of specific {branch_name} branch only if the answer is available in it, Refer to context of all branches if 
        and only if the answer is not available in the context of the specific branch.
        Rule no 3. IF THE QUERY IS OUT OF CONTEXTS, REPLY POSITIVELY AND EXPLAIN THAT YOU DO NOT HAVE FULL INFORMATION ON THAT. 
        Rule no 4. CAREFULLY ANALYZE THE CONTEXTS BEFORE RESPONDING. BE SPECIFIC TO THE QUERY ASKED. YOUR ANSWERS SHOULD BE PRECISE, CONCISE, AND ONLY TO THE POINT, ADDRESSING THE FULL QUESTION WITHOUT UNNECESSARY DETAILS THAT ARE NOT ASKED IN THE QUERY.
        When mentioning the prices, mention the currency of the prices which is as it is available in the context.
        <class_schedule>
                You are provided with the current date, day, and time.
                ## CURRENT DATE: {today}
                ## CURRENT DAY: {weekday}
                ## CURRENT TIME: {time}
                If the class schedule is available in link format provide the same link as response.
                If a user queries about class schedules (e.g., yoga), follow these steps only if the date and time is available in the context to ensure accuracy:  
                1. **Check Future Availability:** Analyze the context to determine if the mentioned class is available on a future date from `{today} {time}`. Avoid recommending schedules before `{today} {time}`, even if the weekday `{weekday}` is the same, as schedules may vary.  
                2. **Understand User Intent:** Assess the user's preferred schedule and verify if it matches the available classes.  
                3. **Handle Unavailability:** If no classes are available after `{today} {time}`, state: "There are no classes available."  
                4. **Recommend Future Classes Only:** Mention only the classes available from `{today} {time}` onwards.  
                5. **Respond to Ambiguity:** If the query does not specify a class name, suggest a few classes available from `{today} {time}`.  

                Ensure responses are concise, accurate, and focus solely on future schedules.
        </class_schedule>
        <case>
                if the contexts contains answers both in english and arabic language, check for the answers in the contexts in {language} language.
                If you cannot find answer in {language} language, then only refer to the answer in another language.
                Do not follow this rule if the answers in the context in only english language.
                Incase if you are referring to answers in arabic, refer to complete arabic answer.
        </case>

        Your response must be in json format with fields specified as: dict(
        "answer": "Your response to the user in string",
        "handled": " 'yes' if you were able to provide answer according to the context available, 'no' if you were not able to provided answer from the context available.",
        "intent": "intent of the user, select from one of these list of intents: {intents}"
    )
    Remember that dict refers to curly brackets.
    Do not add any backticks or additional texts, just the json.
    """
    return ChatPromptTemplate.from_template(template)


import pytz
async def general_info(self):
    async def getGeneral(query:str):
        tz = timezone.utc

        tz = timezone.utc
        if self.client_details.get("timezone"):
            try:
                tz = pytz.timezone(self.client_details.get("timezone"))
            except Exception as e:
                tz = timezone.utc
            
        current_utc = datetime.now(tz)
        today = current_utc.strftime("%Y-%m-%d")
        time = current_utc.strftime("%H:%M %p")
        weekday = current_utc.strftime("%A")
        if self.branch_database:
            if self.useRegion:
                general_retrival=[k.page_content for k in self.general_database.similarity_search(query,k=7)]
                branch_retrival=[k.page_content for k in self.branch_database.similarity_search(query,k=7)]
                print({"general_retrival":general_retrival,"branch_retrival":branch_retrival,"useRegion":self.useRegion,"query":query})
                branch_prompt = getBranchPrompt()
                chain = RunnableMap(
                    {
                        "question": lambda x: x["question"],
                        "branch_name": lambda x: self.client_details.get("branch_name","branch"),
                        "client_name": lambda x: self.client_details.get("client_name", "main club"),
                        "intents": lambda x: intents,
                        "context_club": lambda x: general_retrival,
                        "context_branch": lambda x: branch_retrival,
                        "language": lambda x: x["language"],
                        "today": lambda x: x["today"],
                        "time": lambda x: x["time"],
                        "weekday": lambda x: x["weekday"]
                    }
                ) | branch_prompt | self.llm | JsonOutputParser()
            else:
                branch_retrival=[k.page_content for k in self.branch_database.similarity_search(query,k=10)]
                print({"branch_retrival":branch_retrival,"useRegion":self.useRegion,"query":query})
                branchless_prompt = getBranchlessPrompt()
                chain = RunnableMap(
                {
                 "question": lambda x: x["question"],
                 "context": lambda x: branch_retrival,
                 "intents": lambda x: x["intents"],
                "language": lambda x: x["language"],
                "today": lambda x: x["today"],
                        "time": lambda x: x["time"],
                        "weekday": lambda x: x["weekday"]

                }
            ) | branchless_prompt | self.llm | JsonOutputParser()


        else:
            general_prompt = getBranchlessPrompt()
            general_retrival=[k.page_content for k in self.general_database.similarity_search(query,k=10)]
            print({"general_retrival":general_retrival,"useRegion":self.useRegion,"query":query})
            chain = RunnableMap(
                {
                 "question": lambda x: x["question"],
                 "context": lambda x: general_retrival,
                 "intents": lambda x: x["intents"],
                "language": lambda x: x["language"],
                "today": lambda x: x["today"],
                        "time": lambda x: x["time"],
                        "weekday": lambda x: x["weekday"]

                }
            ) | general_prompt | self.llm | JsonOutputParser()

        response = await chain.ainvoke({"question": query, "intents": intents, "language": self.requiredLanguage, "today": today, "time": time, "weekday":weekday})
        if response.get("handled") in ["no", "'no'", "No"]:
            self.unhandled_arguments = False
        self.user_intent = response.get("intent")
        return response.get("answer")       

    return getGeneral