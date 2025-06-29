import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import inspect
import inspect2
inspect.getargspec = inspect2.getargspec
import pymorphy2

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
morph = pymorphy2.MorphAnalyzer()

def normalize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r'[^а-яa-z\s]', '', text)
    words = text.split()
    lemmas = [morph.parse(word)[0].normal_form for word in words]
    return lemmas

def jaccard_similarity(str1: str, str2: str) -> float:
    set1 = set(normalize(str1))
    set2 = set(normalize(str2))
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union

def combined_similarity(query: str, article: dict) -> float:
    query_emb = model.encode(query)
    abstract_emb = model.encode(article["abstract"])
    cos_sim = cosine_similarity([query_emb], [abstract_emb])[0][0]
    jac_sim = jaccard_similarity(query, article["title"])
    return 0.7 * cos_sim + 0.3 * jac_sim