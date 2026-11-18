"""Recherche des procédures pertinentes (TF-IDF + similarité cosinus).

Le corpus contient les procédures légitimes et, en mode attaque, des documents
piégés qui contiennent des instructions cachées (injection de prompt indirecte).
"""
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Document:
    doc_id: str
    text: str
    poisoned: bool


def load_corpus(include_poisoned: bool = True) -> list[Document]:
    docs = [Document(p.stem, p.read_text(encoding="utf-8"), False)
            for p in sorted((DATA_DIR / "procedures").glob("*.md"))]
    if include_poisoned:
        docs += [Document(p.stem, p.read_text(encoding="utf-8"), True)
                 for p in sorted((DATA_DIR / "poisoned").glob("*.md"))]
    return docs


class Retriever:
    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.vectorizer = TfidfVectorizer(lowercase=True, strip_accents="unicode")
        self.matrix = self.vectorizer.fit_transform([d.text for d in docs])

    def search(self, query: str, k: int = 3) -> list[Document]:
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        ranked = sorted(range(len(self.docs)), key=lambda i: scores[i], reverse=True)
        return [self.docs[i] for i in ranked[:k] if scores[i] > 0]
