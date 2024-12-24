from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate


async def get_intent(query, llm,history):
    template = """
        you only speak in json. 
        You are provided with the query of the user inside double backticks: ``{query}``
        Do not change the user query, Leave it unchanged and do not modify in any sort of way.

        <language requirement>
        Analyze the language of the user query, and classify the language of it to either (english or arabic).
        arabic: if the language of the user query is in arabic.
        english: if the language of the user query is in english or any other languages.
        <language requirement>

        <intent analysis requirement>
        Here is the conversation history between you and the user inside double backticks: ```{history}```
        You need to analyze the user query and history to know the intent of the current query.
        
        If the intent of the user query relates to general greetings, introductions, relates to user wanting to book a pass/trial/tour or cancellations or scheduling of it, providing date and time, name, email and phonenumber (Analyze the conversation history for better understanding).
        Your answer must be 'no'.

        If the intent of the user query relates to asking questions about gym club (Analyze the conversation history for better understanding).
        Your answer must be 'yes'.
        <intent analysis requirement>

        Your output format must be in the following json format.
        dict(
        "language":"Either english or arabic",
        "intent":"yes or no based on the intent analysis requirement"
        )
        Reminder that dict refers to curly brackets.
        Do not add any additional backticks or texts in your response.
    """

    prompt = ChatPromptTemplate.from_template(template)

    chain = prompt | llm | JsonOutputParser()

    return await chain.ainvoke({"query": query, "history":history})