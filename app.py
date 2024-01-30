from dotenv import load_dotenv
load_dotenv()
from flask import Flask, make_response, render_template, request, jsonify
import os
from supabase import create_client, Client
from search import do_search

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template('main.html')


@app.route("/generate", methods=['POST'])
def generate():
    result = do_search(request.json['question'])
    return result


@app.errorhandler(404)
def not_found(error):
    resp = make_response("<p>Not found.</p>", 404)
    resp.headers['X-Something'] = 'A value'
    return resp