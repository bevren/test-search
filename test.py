from dotenv import load_dotenv
load_dotenv()

import os
import concurrent.futures
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from duckduckgo_search import DDGS



API_KEY = os.environ.get("API_KEY_GEMINI")
genai.configure(api_key=API_KEY)

generation_config = {
    "temperature": 0,
    "max_output_tokens": 4096,
    "candidate_count": 1
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    },
]

model = genai.GenerativeModel('gemini-pro', generation_config=generation_config, safety_settings=safety_settings)

def fetch_and_clean(q, url):
    try:
        # Fetch HTML content from the URL
        response = requests.get(url['href'])
        response.raise_for_status()

        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        #text_content = ' '.join(soup.stripped_strings)
        # Extract text content
        text_content = ' '.join(soup.stripped_strings)
        #text_content = soup.article.get_text(' ', strip=True)

        try:
            summarize_prompt = f"""Extract the information from given context that answers the question. 

            - Your response must be in the same language as the original question and provided context.

            Here is the question:

            {q}

            Here is the context:

            {text_content}

            """

            summarize_prompt_2 = f""" Summarize the following article using only 200 words.

            - Your response must be in the same language as the provided article.

            Here is the article:

            {text_content}

            """
            response = model.generate_content(summarize_prompt_2)

            return response.text
        except Exception as d:
            print(d)
            return "Error"

    except Exception as e:
        # Handle exceptions if any
        return f"Error processing {url}: {str(e)}"


def summarize(q, text):
    try:

        summarize_prompt = f"""Extract the information from given context that answers the question. 

        - Your response must be in the same language as the original question and provided context.

        Here is the question:

        {q}

        Here is the context:

        {text}

        """
        
        response = model.generate_content(summarize_prompt)


        return response.text
    except Exception as e:
        # Handle exceptions if any
        return f"Error summarizing"


def parallel_fetch_and_clean(q, links):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Use the executor to map the function to the list of links
        results = executor.map(fetch_and_clean, q, links)

    return list(results)

def parallel_summarize(q, texts):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Use the executor to map the function to the list of links
        results = executor.map(summarize, texts)

    return list(results)


def search_result_ddgs(q, num_results=5):
    result = []
    with DDGS() as ddgs:
        result = [r for r in ddgs.text(q, max_results=num_results, region="tr-tr")]
    
    return result


def construct_search_ddgs(q, num_results=5):
    q = [q] * num_results

    links_to_process = search_result_ddgs(q[0], num_results)

    # Get the cleaned text content for each link in parallel
    results = parallel_fetch_and_clean(q, links_to_process)

    result = ""

    i = 0
    # Print the results
    for url, text_content in zip(links_to_process, results):
        result += f"RESULT {i+1}:\n"
        result += f"URL: {url}\nSUMMARY:{text_content}\n\n"
        i += 1

    return result, links_to_process
