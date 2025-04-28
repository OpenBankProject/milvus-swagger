from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

import os

# Load environment variables from .env file
load_dotenv("../.env")

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY environment variable not set. Please set it in your environment variables or .env file.")

# Define an endpoint to summarize the descriptions
prompt = ChatPromptTemplate.from_template(
    "Summarise the following OpenAPI endpoint description (written in html) in plain text with less than 2000 characters:\n\n{raw_description}"
)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

endpoint_summary_chain = prompt | llm