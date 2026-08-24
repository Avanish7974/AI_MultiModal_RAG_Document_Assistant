from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")


def create_embeddings(chunks):
    return model.encode(chunks)


def get_embedding_model():
    return model