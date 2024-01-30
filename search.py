from dotenv import load_dotenv
load_dotenv()

import os
import requests
import google.generativeai as genai
import datetime
from duckduckgo_search import DDGS
import random
import re
from urllib.parse import urlparse

from test import construct_search_ddgs



API_KEY_SEARCH = os.environ.get("API_KEY_SEARCH_GOOGLE")
SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID")

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

def query_google(q, num=10, start=1, date_restrict="m1"):
    url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY_SEARCH}&cx={SEARCH_ENGINE_ID}&start={start}&num={num}&dateRestrict={date_restrict}&hl=tr&lr=lang_tr&q={q}"
    response = requests.get(url)

    print(response.status_code)
    if response.status_code != 200:
        raise Exception("request failed")

    return response.json()


def get_results_ddgs(q, num_results=10):
    result = []
    with DDGS() as ddgs:
        result = [r for r in ddgs.text(q, max_results=num_results, region="tr-tr")]
    
    return result

def get_results_google(q, num_results=10):
    reminder = num_results %  10
    pages = num_results // 10
    
    items = []
    if reminder > 0:
        pages += 1

    if pages*10 > 100:
        raise Exception("number of results cannot be higher than 100")
    

    for i in range(pages):
        if pages == i + 1 and reminder > 0:
            payload = query_google(q, start=(i+1)*10, num=reminder)
        else:
            payload = query_google(q, start=(i+1)*10)

        items.extend(payload['items'])


    return items


def construct_format_google(items):
    result = "SEARCH RESULTS: \n\n"

    for i, item in enumerate(items):
        result += f"{i + 1}. Title:{item['title']} Snippet:{item['snippet']} Link:{item['link']}\n"

    return result

def construct_format_ddgs(items):
    result = "WEB SEARCH RESULTS: \n\n"

    for i, item in enumerate(items):

        result += f"RESULT {i+1}:\n"
        result += f"TITLE:{item['title']}\n"
        result += f"SUMMARY:{item['body']}\n"
        result += f"URL:{item['href']}\n\n"

    return result


def do_search(q):
    #resp = get_results_ddgs(q, num_results=8)
    #constructed = construct_format_ddgs(resp)
    now = datetime.datetime.now()

    constructed, resp = construct_search_ddgs(q)

    system_prompt = f"""You are a helpful assistant. Generate a comprehensive and informative answer in Turkish language(not more than 100 words) for a given question solely based on the provided web search results(URL and summary) in Turkish language.You must only use information from the provided search results. This is the current date and time: {now.strftime("%Y-%m-%d %H:%M:%S")}. Convert search results together into a coherent answer. Never repeat text. Cite search results using [$(number)] notation.Only cite the most relevant results that answers the question accurately.If different results refers to different entities with same name, write seperate answers for each entity.Add cite results at the end of each sentence just like wikipedia."""

    history = []

    history.append({
        "parts": [system_prompt],
        "role": "user"
    })

    history.append({
        "parts": ["Anlaşıldı."],
        "role": "model"
    })

    history.append({
        "parts": [constructed],
        "role": "user"
    })

    all_prompt = f"""CURRENT DATE:{now.strftime("%Y-%m-%d %H:%M:%S")}

    CONTEXT:
    {constructed} 

    QUESTION: 
    {q}
    
    ```generated
    ANSWER:
    <insert comprehensive and informative, unique answer.cite search results using [$(number)] notation.Only cite the most relevant results that answers the question accurately.Add cite results at the end of each sentence.>
    <always give usage examples based on question and context if possible>

    FOLLOW-UP QUESTIONS:
    <insert three follow-up question not more than 15 words>
    ```
    """

    response = model.generate_content(all_prompt)

    text = response.text

    questions = []

    answer_text = re.search(r"ANSWER:(.*?)(FOLLOW-UP QUESTIONS:|$)", text, re.DOTALL | re.IGNORECASE)
    followup_questions = re.search(r"FOLLOW-UP QUESTIONS:(.*?)(END|$)", text, re.DOTALL | re.IGNORECASE)

    if answer_text: 
        text = answer_text.group(1).strip()
        print("Extracted Answer Text:\n", text)

    if followup_questions:
        followup_questions_extracted = followup_questions.group(1).strip()
        
        questions = re.findall(r'[\d-]+\.?\s*(.*\?)', followup_questions_extracted)
        # Remove leading and trailing whitespaces
        questions = [question.strip() for question in questions]


    history.append({
        "parts": [text],
        "role": "model"
    })

    related_question_prompt= f"""- Identify worthwhile topics that can be follow-ups and write a three questions. 

    - Your related questions must be in Turkish language.

    - Make sure that specifics, like events, names, locations, are included in follow up questions so they can be asked standalone. 

    - EXAMPLE: if the original question asks about "the Manhattan project", in the follow up question, do not just say "the project", but use the full name "the Manhattan project". 

    - Do NOT repeat original question.

    - Write questions no longer than 20 words each.

    - Ask follow-up questions that don't have answers already in provided context. 

    """

    

    # history.append({
    #     "parts": [related_question_prompt],
    #     "role": "user"
    # })

    # response = model.generate_content(history)

    # releated_questions = response.text

    # print(releated_questions)

    # #[\d-]+\.?\s*(.*\?)
    # #\d+\.\s(.*?\?)
    # questions = re.findall(r'[\d-]+\.?\s*(.*\?)', releated_questions)

    # # Remove leading and trailing whitespaces
    # questions = [question.strip() for question in questions]

    sources = []
    sources_text = ""

    for i, item in enumerate(resp):
        sources_text += "<div>"
        sources_text += f"<h2><a href='{item['href']}'>{item['title']}</a></h2>"
        sources_text += f"<p>{item['body']}...</p>"
        sources_text+= "</div>"
        parsed_url = urlparse(item['href'])

        sources.append({
            "title": item['title'],
            "link":item['href'],
            "link_base": parsed_url.netloc
        })


    pattern = r'\[(.*?)\]'


    def replace_with_indices(match):
        parts = match.group(1).split(',')
        current_match_indices = []
        result = ""

        if len(parts) > 0:
            for part in parts:
                stripped_part = part.strip()
                if stripped_part.isdigit():
                    current_match_indices.append(int(stripped_part))


            if(len(current_match_indices) > 0):
                for i in current_match_indices:
                    if resp[i-1]:
                        result += f"<a class='citation' target='_blank' rel='noopener noreferrer' href='{resp[i-1]['href']}'>{i}</a>"

        
        return result


    modified_text = re.sub(pattern, replace_with_indices, text)

    result = {
        "id": random.randint(0, 10000),
        "text": modified_text,
        "sources": sources_text,
        "sources_list": sources,
        "related_questions": questions
    }

    return result