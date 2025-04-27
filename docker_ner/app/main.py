import spacy
import json
import uvicorn
from fastapi import FastAPI, Body
from datetime import date
from pydantic import BaseModel
import geopy
from geopy.geocoders import Nominatim


class Text(BaseModel):
    text: str


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/v1.0/check-status")
async def root():
    return {"Alive": True}


@app.get("/api/ner_t")
def ner_t():
    d = [{'User': 'a', 'date': date.today(), 'count': 1},{'User': 'b', 'date':  date.today(), 'count': 2}]
    return d


@app.post("/api/ner")
def ner(text: Text):
    #text_dict = text.dict()
    nlp = spacy.load("ru_core_news_sm")
    doc = nlp(text.text)
    d = {}
    for ent in doc.ents:
        if ent.label_ == 'LOC':
            d.update({ent.text:ent.label_})
    #jsonStr = json.dumps(d, ensure_ascii=False)
    return d


@app.post("/api/geocode")
def geocode(text: Text):
    text_dict = text.dict()
    geolocator = Nominatim(timeout=10, user_agent = "docker_nlp")
    location = geolocator.geocode(text.text)
    d = {}
    if location is not None:
        d.update({"lat":location.latitude})
        d.update({"lon":location.longitude})
    return d


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, log_level="info")
