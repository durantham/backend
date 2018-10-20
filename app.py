from quart import Quart, websocket, jsonify
from psaw import PushshiftAPI
from bs4 import BeautifulSoup
import spacy
from langdetect import detect
from afinn import Afinn
from markdown import markdown
import time
import json
from datetime import datetime
import re

"""app = Quart(__name__)

@app.route('/')
async def hello():
    return 'hello'

@app.websocket('/ws')
async def ws():
    while True:
        await websocket.send('{ "msg": "x" }')
        time.sleep(1)

@app.websocket('/ws2')
async def ws2():
    while True:
        await websocket.send('{ "msg": "y" }')
        time.sleep(1)

app.run()"""

app = Quart(__name__)
api = PushshiftAPI()
nlp = spacy.load("en", disable=['parser', 'tagger', 'ner'])
stops = nlp.Defaults.stop_words
afinn = Afinn()

def sentiment(comment):
    n = len(comment.split(" "))
    s = afinn.score(comment)
    return (((s / n) / 5), s)

def normalize(comment, lowercase=True, remove_stopwords=True):
    if lowercase:
        comment = comment.lower()
    comment = nlp(comment)
    lemmatized = list()
    for word in comment:
        lemma = word.lemma_.strip()
        if lemma:
            if not remove_stopwords or (remove_stopwords and lemma not in stops):
                lemmatized.append(lemma)
    return " ".join(lemmatized)

def preprocess(comment):
    comment = markdown(comment)
    soup = BeautifulSoup(comment, "html5lib")
    text = soup.get_text(strip=True)
    text = text.lower()
    text = re.sub(r'^https?:\/\/.*[\r\n]*', ' ', text)
    text = re.sub(r'''(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))''', " ", text)
    text = normalize(text)
    text = re.sub(r'[^a-zA-Z0-9]+', ' ', text)
    text = text.strip()
    text = text.replace('PRON', '')
    return text

@app.websocket('/ws')
async def ws():
    data = await websocket.receive()
    data = json.loads(data)
    topic = data['topic']
    print(topic)
    gen = api.search_comments(q=topic)
    m = 10
    x = []
    print(datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    for c in gen:
        if not c.author.lower().endswith('bot'):
            x.append(c)
            t = preprocess(c.body)
            try:
                d = detect(t)
                print("++++", d,"++++")
                if d != 'en':
                    print("X")
                    continue
            except:
                continue
            y = {}
            y['body'] = t
            y['score'] = c.score
            y['sentiment'] = sentiment(t)[0]
            y['whole_sentiment'] = sentiment(t)[1]
            y['permalink'] = c.permalink
            z = json.dumps(y)
            print(z)
            print(datetime.utcfromtimestamp(c.created_utc).strftime('%Y-%m-%d %H:%M:%S'))
            await websocket.send(z)
            if len(x) > m:
                break

app.run()
