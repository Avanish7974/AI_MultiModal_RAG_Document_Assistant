def retrieve_chunks(query, collection, top_k=5):
    print("=== NEW RETRIEVER CALLED ===")

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    print(results.keys())

    return {
        "documents": results["documents"][0],
        "metadatas": results["metadatas"][0],
    }