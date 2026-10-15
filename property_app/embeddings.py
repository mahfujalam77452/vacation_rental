from functools import lru_cache

MODEL_NAME = "all-MiniLM-L6-v2"

DIMENSIONS = 384

@lru_cache(maxsize=1)
def get_model():

    # import is here so that each manage.py doesn't become slow
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)

def embed_text(text):
    """ A text to 384 dimensions vector"""
    return get_model().encode(text.strip(),normalize_embeddings=True).tolist()

def embed_texts(texts):
    """ batch processing for multiple text """
    return get_model().encode(
        [t.strip() for t in texts], normalize_embeddings=True,batch_size=32
    ).tolist()
