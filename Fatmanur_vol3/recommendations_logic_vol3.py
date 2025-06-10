# recommendations_logic.py dosyasının TAM İÇERİĞİ

import requests
import itertools
import random  # Bu versiyonda deterministik olmadığı için random kalabilir

OPENLIB_BASE = "https://openlibrary.org"

TAG_MAPPING = {
    "dystopian": ["dystopian", "utopia", "apocalyptic", "dystopia-fiction", "dystopia-future"],
    "historical-fiction": ["historical-fiction", "history", "historical", "historical-novels"],
    "action-adventure": ["adventure", "action", "action-adventure", "action-novels"],
    "crime": ["crime", "mystery-crime", "detective", "thriller-crime", "suspense"],
    "thriller": ["thriller", "suspense", "psychological-thriller"],
    "horror": ["horror", "psychological-horror", "gothic-horror", "horror-fiction", "occult-&-supernatural-fiction"],
    "science-fiction": ["science-fiction", "sci-fi", "space-fiction", "robot"],
    "fantasy": ["fantasy", "fantasy-fiction", "mythological", "epic-fantasy", "high-fantasy"],
    "mythology": ["mythology", "mythical", "myths"],
    "young-adult": ["young-adult", "ya", "teen-fiction", "juvenile-fiction"],
    "classics": ["classics", "classic-fiction", "classic-literature"],
    "romance": ["romance", "romantic-fiction", "romantic-novels", "love", "vampires"],
    "mystery": ["mystery", "detective", "mystery-fiction"],
    "drama": ["drama", "fiction", "dramatic-fiction"],
    "short-story": ["short-story", "short-fiction", "short-stories"],
    "feel-good": ["feel-good", "uplifting", "positive-fiction"],
    "contemporary": ["contemporary", "modern-fiction", "realistic-fiction"],
    "political": ["political", "political-fiction", "politics"],
    "spiritual-religious": ["spiritual", "religion", "religious-fiction"],
    "philosophy": ["philosophy", "philosophical", "philosophical-fiction"],
    "history": ["history", "historical", "non-fiction-history"],
    "memoir-biography": ["memoir", "biography", "autobiography"],
    "true-crime": ["true-crime", "true-crime-fiction"],
    "business-finance": ["business", "finance", "financial-literature"],
    "arts": ["arts", "art-history", "art"],
    "sports-and-hobby": ["sports", "hobbies", "sports-fiction"],
    "personal-development": ["self-help", "personal-development"],
    "poetry": ["poetry", "poems", "poetic-fiction"],
    "science": ["science", "scientific", "science-literature"],
    "health-and-nutrition": ["health", "nutrition", "healthcare"],
    "gore-graphic": ["gore", "violence", "horror"],
    "erotica": ["erotica", "erotica-fiction"],
    "feminism": ["feminism", "gender-equality", "women-studies"],
    "gender": ["gender", "gender-studies"],
    "bestseller": ["bestseller", "best-selling"]
}


def expand_input_tag(tag):
    key = tag.strip().lower()
    return TAG_MAPPING.get(key, [key])


def fetch_books_for_triple(slug1, slug2, slug3, limit=25):
    params = {
        "subject": [slug1, slug2, slug3],
        "language": "eng",
        "limit": limit,
        "fields": "key,title,author_name,cover_i,first_publish_year,subject,publisher"
    }
    try:
        resp = requests.get(f"{OPENLIB_BASE}/search.json", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("docs", [])
    except requests.RequestException as e:
        print(f"API isteği sırasında hata: {e}")
        return []


def fetch_book_details(work_id):
    if not work_id or not work_id.startswith('/works/'):
        return "Açıklama mevcut değil."
    try:
        work_details_url = f"{OPENLIB_BASE}{work_id}.json"
        desc_response = requests.get(work_details_url, timeout=5)
        desc_response.raise_for_status()
        desc_data = desc_response.json()
        description_obj = desc_data.get('description')
        if isinstance(description_obj, dict):
            return description_obj.get('value', "Açıklama mevcut değil.")
        elif isinstance(description_obj, str) and description_obj.strip():
            return description_obj
    except requests.RequestException as e:
        print(f"'{work_id}' için açıklama alınırken hata: {e}")
    return "Açıklama mevcut değil."


def get_recommendations_with_weighted_scoring(input_tags, final_limit=12, excluded_tags=None, tag_weights=None):
    """
    *** OPEN LIBRARY İÇİN VERSİYON 3.0: AĞIRLIKLI POZİTİF PUANLAMA MANTIĞI ***
    """
    if tag_weights is None: tag_weights = {}
    if excluded_tags is None: excluded_tags = []

    all_excluded_slugs = set(itertools.chain.from_iterable(expand_input_tag(tag) for tag in excluded_tags))
    expanded_slugs = {tag: expand_input_tag(tag) for tag in input_tags}
    tag_combos = list(itertools.combinations(input_tags, 3))
    random.shuffle(tag_combos)  # Sonuçları çeşitlendirmek için

    pool = {}
    for tag1, tag2, tag3 in tag_combos:
        if len(pool) >= 60:
            break
        slug1 = random.choice(expanded_slugs[tag1])
        slug2 = random.choice(expanded_slugs[tag2])
        slug3 = random.choice(expanded_slugs[tag3])
        docs = fetch_books_for_triple(slug1, slug2, slug3, limit=30)
        for doc in docs:
            book_subjects = {s.lower() for s in doc.get("subject", [])}
            if not all_excluded_slugs.isdisjoint(book_subjects):
                continue
            key = doc.get("key")
            if key and key not in pool:
                pool[key] = doc

    if not pool: return []

    scored_works = []
    weighted_slugs = {tag: (set(expand_input_tag(tag)), weight) for tag, weight in tag_weights.items()}

    for work_key, work_doc in pool.items():
        book_subjects = {s.lower() for s in work_doc.get("subject", [])}
        score = 0
        for tag_name, (slugs_to_check, weight) in weighted_slugs.items():
            if not book_subjects.isdisjoint(slugs_to_check):
                score += weight
        if score > 0:
            scored_works.append({'score': score, 'doc': work_doc})

    sorted_works = sorted(scored_works, key=lambda x: x['score'], reverse=True)
    selected_works = [item['doc'] for item in sorted_works[:final_limit]]

    suggestions = []
    for doc in selected_works:
        key = doc.get("key")
        description = fetch_book_details(key)
        thumbnail_url = f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-M.jpg" if doc.get('cover_i') else None
        suggestions.append({
            "id": key, "title": doc.get("title", "Başlık Yok"),
            "author": ", ".join(doc.get("author_name", ["Bilinmeyen Yazar"])),
            "genres": doc.get("subject", []), "publisher": ", ".join(doc.get("publisher", ["Bilinmeyen Yayıncı"])),
            "published_date": str(doc.get("first_publish_year", "Bilinmiyor")),
            "description": description, "thumbnail": thumbnail_url
        })
    return suggestions