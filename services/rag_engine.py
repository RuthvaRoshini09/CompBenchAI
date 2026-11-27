import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import re
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Locate knowledge base directory
KNOWLEDGE_BASE_DIR = (
    Path(__file__).resolve().parents[1]
    / "knowledge_base"
)

EDUCATIONAL_DISCLAIMER = (
    "General educational reference material — not official OEM or Caresoft data."
)

_cached_documents = None
_cached_vectorizer = None
_cached_tfidf_matrix = None


def load_knowledge(force_reload: bool = False):
    """
    Load automotive engineering knowledge documents from knowledge_base/.
    Parses markdown files into structured sections and passages.
    """
    global _cached_documents, _cached_vectorizer, _cached_tfidf_matrix

    if _cached_documents is not None and not force_reload:
        return _cached_documents

    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            f"Knowledge base directory not found: {KNOWLEDGE_BASE_DIR}"
        )

    documents = []

    for file_path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Extract main document title from first # heading
        title_match = re.search(r"^#\s+(.+)$", raw_text, re.MULTILINE)
        doc_title = (
            title_match.group(1).strip()
            if title_match
            else file_path.stem.replace("_", " ").title()
        )

        # Split into sections based on ## headings
        sections = re.split(r"\n(?=##\s+)", raw_text)

        for sec in sections:
            sec_text = sec.strip()
            if not sec_text:
                continue

            sec_match = re.match(r"^##\s+(.+)$", sec_text, re.MULTILINE)
            if sec_match:
                section_title = sec_match.group(1).strip()
                content = sec_text[sec_match.end():].strip()
            else:
                section_title = "Overview"
                content = sec_text

            # Remove markdown notice blockquote and document title for clean text
            clean_content = re.sub(r">\s*\*+Educational Reference Notice\*+:.*?(?:\n|$)", "", content, flags=re.DOTALL)
            clean_content = re.sub(r"^#\s+.*?(?:\n|$)", "", clean_content).strip()

            # Skip passages that have no substantive content (e.g., pure header blocks)
            if not clean_content or len(clean_content) < 30:
                continue

            documents.append({
                "source_title": doc_title,
                "section": section_title,
                "content": clean_content,
                "source_file": file_path.name,
                "disclaimer": EDUCATIONAL_DISCLAIMER
            })

    _cached_documents = documents
    _cached_vectorizer = None
    _cached_tfidf_matrix = None

    return documents


def retrieve_knowledge(query: str, top_k: int = 3):
    """
    Retrieve the most relevant knowledge passages for a query using TF-IDF
    and cosine similarity.

    Args:
        query: User search query string.
        top_k: Number of relevant passages to return (default 3).

    Returns:
        List of dictionaries with source_title, section, content, source_file,
        similarity_score, and educational disclaimer.
    """
    global _cached_documents, _cached_vectorizer, _cached_tfidf_matrix

    docs = load_knowledge()
    if not docs or not query or not query.strip():
        return []

    # Initialize TF-IDF vectorizer and matrix if not cached
    if _cached_vectorizer is None or _cached_tfidf_matrix is None:
        corpus = [
            f"{d['source_title']} {d['section']} {d['content']}"
            for d in docs
        ]
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)
        _cached_vectorizer = vectorizer
        _cached_tfidf_matrix = tfidf_matrix
    else:
        vectorizer = _cached_vectorizer
        tfidf_matrix = _cached_tfidf_matrix

    query_vec = vectorizer.transform([query])
    similarity_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    ranked_indices = similarity_scores.argsort()[::-1]

    results = []
    for idx in ranked_indices[:top_k]:
        score = float(similarity_scores[idx])
        doc = docs[idx]
        results.append({
            "source_title": str(doc["source_title"]),
            "section": str(doc["section"]),
            "content": str(doc["content"]),
            "source_file": str(doc["source_file"]),
            "similarity_score": round(score, 4),
            "disclaimer": doc["disclaimer"]
        })

    return results
