import json
from langchain.prompts import PromptTemplate,ChatPromptTemplate
from langchain_core.runnables import RunnableMap
from langchain_core.output_parsers import JsonOutputParser

#Query is list of strings, and intent is also list of intent
def cout_and_classify(query,llm,intent):
     count_prompt="""You are an AI assistant tasked with analyzing a list of user queries. You have two main tasks:

     Task1:For providing most frequently asked queries follow the following steps:
          - Analyze the meaning behind each query and group similar queries together if they have similar meanings.
          - Then, count the frequency of each unique query and return the top 10 most frequently asked queries in descending order of frequency.

     Task 2: Classify the Top 10 Most Frequent aims identifying the key words following the following steps:
     1. Analyze the meaning behind each query and group similar aims together if they have similar meanings.
     2. Count the frequency of each unique aim.
     3. Return the top 10 most frequent aims in descending order of frequency.
          For example, for the query: "What is the best time to work out at the gym?" the aim could be 'time'
               Also for the query: 'What is the price of a 25k LED TV?' the aim could be a 'price'

     The list of queries is provided between double backticks:
     ``{query}``
     The list of intents is provided in triple backticks:
     ```{intent}```
      If two or more queries have similar meanings, list only the most representative query. 
          
     The response should be in the following format:
         -dict(
               "top_10_question":[
                    dict(
                    "query":"query from the top 10 queries",
                    "intent":"Analyze and provide the appropriate intent for the top 10 query.",
                    )
                    ],
                    ,
               "aim":[
                    "Top 10 Most Frequent Intents only in json format ignore the {intent}.Merge the duplicate aims to one"
               ]
          )
     Remember that the dict in the response represent the curly braces.
     Do not add the frequency in the response and unwanted information like index and other unwanted stuffs.
     Always return the top 10 most frequently asked queries and the top 10 most frequent intents.
     Your response should be in clean json format without any additional tags,symbols,backticks  information.
     """
     
     if intent:
          count_prompt="""As an AI assistant, you have two main tasks:
          The list of queries is provided in double backticks:
          ``{query}``
          The list of classification is provided in triple backticks:
          ```{intent}```

          Task1: For providing the most frequently asked queries, follow these steps:
          - Analyze the meaning behind each query and group similar queries together if they have similar meanings.
          - Count the frequency of each unique query and return the top 10 most frequently asked queries in descending order of frequency.
          - Understand the queries from the 10 most frequently asked queries and you must map those queries with the intents provided in the list of intents.If the queries does not match with the intent then classified the intent as 'others'.

          Task2: Analyze  and return the top 10 Most Frequent aims from the provided list of queries {query} by following these steps.
          1. Analyze the meaning behind each query and group similar intents together if they have similar meanings.
          2. Count the frequency of each unique aims.
          3. Return the top 10 most frequent aims in descending order of frequency.
          For example, for the query: "What is the best time to work out at the gym?" the aims could be 'time'

          Your response should be in the following JSON format:
          If intent is available:
               dict("top_10_questions":[
               dict(
               "query":"query from the top 10 queries",
               "intent":"Provide only matched intent for the top 10 questions from the provided intent list {intent} only.Provide the intent as 'others' if the query does not matches with the intent."
               )
               ],

          "aim": [
          "Igore the {intent}  and provide the Top 10 Most Frequent aims from {query} only in json format.Merge the duplicate aims to one.""
          ]
          )
          Do not include frequency or any additional information such as indices.

               """
     
     prompt_temp=ChatPromptTemplate.from_template(template=count_prompt)
     chain=RunnableMap({
                "query":lambda x: x['query'],
                "intent":lambda x: x['intent']
                }
            )| prompt_temp | llm | JsonOutputParser()

     return chain.invoke({"query":query,"intent":intent})
     