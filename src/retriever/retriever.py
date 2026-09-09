# def retrieve_chunks(query, collection, top_k=5):
#     print("=== NEW RETRIEVER CALLED ===")

#     results = collection.query(
#         query_texts=[query],
#         n_results=top_k,
#     )

#     print(results.keys())

#     return {
#         "documents": results["documents"][0],
#         "metadatas": results["metadatas"][0],
#     }
# =========================================================
# INTENT-AWARE RETRIEVER
# =========================================================

import re


# =========================================================
# DETECT QUERY INTENT
# =========================================================

def detect_query_intent(query: str):
    """
    Detect the user's query type.

    This is intentionally lightweight and rule-based so it
    does not require an additional LLM/API call.
    """

    query = query.lower().strip()

    # -----------------------------------------------------
    # SUMMARY / OVERVIEW
    # -----------------------------------------------------

    summary_patterns = [
        r"\bsummarize\b",
        r"\bsummary\b",
        r"\boverview\b",
        r"\bbrief\b",
        r"\bexplain the document\b",
        r"\bmain points\b",
        r"\bkey points\b",
    ]

    if any(
        re.search(pattern, query)
        for pattern in summary_patterns
    ):
        return "summary"

    # -----------------------------------------------------
    # COMPARISON
    # -----------------------------------------------------

    comparison_patterns = [
        r"\bcompare\b",
        r"\bcomparison\b",
        r"\bdifference between\b",
        r"\bsimilarities\b",
        r"\bversus\b",
        r"\bvs\b",
    ]

    if any(
        re.search(pattern, query)
        for pattern in comparison_patterns
    ):
        return "comparison"

    # -----------------------------------------------------
    # ANALYTICAL / EVALUATIVE
    # -----------------------------------------------------

    analytical_patterns = [
        r"\banalyze\b",
        r"\banalysis\b",
        r"\brate\b",
        r"\brating\b",
        r"\breview\b",
        r"\bevaluate\b",
        r"\bassessment\b",
        r"\bats\b",
        r"\bscore\b",
        r"\bstrength\b",
        r"\bweakness\b",
        r"\bpros and cons\b",
        r"\bquality\b",
        r"\bsuitability\b",
    ]

    if any(
        re.search(pattern, query)
        for pattern in analytical_patterns
    ):
        return "analytical"

    # -----------------------------------------------------
    # RECOMMENDATION / IMPROVEMENT
    # -----------------------------------------------------

    recommendation_patterns = [
        r"\bimprove\b",
        r"\bimprovement\b",
        r"\bsuggest\b",
        r"\brecommend\b",
        r"\bhow can i\b",
        r"\bwhat should i\b",
        r"\boptimize\b",
        r"\bbetter\b",
        r"\bfix\b",
    ]

    if any(
        re.search(pattern, query)
        for pattern in recommendation_patterns
    ):
        return "recommendation"

    # -----------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------

    return "factual"


# =========================================================
# GET DYNAMIC TOP-K
# =========================================================

def get_dynamic_top_k(intent: str):
    """
    Decide retrieval depth based on query intent.
    """

    top_k_map = {

        # Direct factual questions
        "factual": 5,

        # Document evaluation / analysis
        "analytical": 10,

        # Suggestions need broader context
        "recommendation": 10,

        # Summary needs maximum context
        "summary": 15,

        # Comparison needs broader retrieval
        "comparison": 12,
    }

    return top_k_map.get(
        intent,
        5,
    )


# =========================================================
# GET RELEVANCE THRESHOLD
# =========================================================

def get_relevance_threshold(intent: str):
    """
    Maximum acceptable Chroma distance.

    Lower distance = higher semantic relevance.

    Analytical queries get a slightly more relaxed threshold
    because useful evidence can be distributed across different
    sections of a document.
    """

    thresholds = {

        # Strict for direct factual lookup
        "factual": 1.35,

        # Broader context allowed
        "analytical": 1.55,

        "recommendation": 1.55,

        # Summary and comparison intentionally need
        # broader document coverage
        "summary": 1.70,

        "comparison": 1.65,
    }

    return thresholds.get(
        intent,
        1.35,
    )


# =========================================================
# RETRIEVE CHUNKS
# =========================================================

def retrieve_chunks(
    query,
    collection,
    top_k=None,
    apply_relevance_check=True,
):
    """
    Intent-aware document retrieval.

    Features:
    - Query intent detection
    - Dynamic Top-K
    - Chroma distance retrieval
    - Similarity/relevance filtering
    """

    print("\n========================================")
    print("INTENT-AWARE RETRIEVER CALLED")
    print("========================================")

    print("QUERY:", query)

    # -----------------------------------------------------
    # DETECT INTENT
    # -----------------------------------------------------

    intent = detect_query_intent(
        query
    )

    print("DETECTED INTENT:", intent)

    # -----------------------------------------------------
    # DYNAMIC TOP-K
    # -----------------------------------------------------

    if top_k is None:

        top_k = get_dynamic_top_k(
            intent
        )

    print("TOP-K:", top_k)

    # -----------------------------------------------------
    # COLLECTION COUNT
    # -----------------------------------------------------

    collection_count = collection.count()

    print(
        "COLLECTION COUNT:",
        collection_count
    )

    if collection_count == 0:

        return {
            "documents": [],
            "metadatas": [],
            "distances": [],
            "intent": intent,
            "top_k": top_k,
        }

    # Never request more chunks than exist
    top_k = min(
        top_k,
        collection_count,
    )

    # -----------------------------------------------------
    # CHROMA QUERY
    # -----------------------------------------------------

    results = collection.query(

        query_texts=[
            query
        ],

        n_results=top_k,

        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = (
        results.get(
            "documents",
            [[]]
        )[0]
        or []
    )

    metadatas = (
        results.get(
            "metadatas",
            [[]]
        )[0]
        or []
    )

    distances = (
        results.get(
            "distances",
            [[]]
        )[0]
        or []
    )

    print(
        "RAW RETRIEVED CHUNKS:",
        len(documents)
    )

    print(
        "DISTANCES:",
        distances
    )

    # -----------------------------------------------------
    # RELEVANCE CHECK
    # -----------------------------------------------------

    if not apply_relevance_check:

        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances,
            "intent": intent,
            "top_k": top_k,
        }

    threshold = get_relevance_threshold(
        intent
    )

    print(
        "RELEVANCE THRESHOLD:",
        threshold
    )

    filtered_documents = []
    filtered_metadatas = []
    filtered_distances = []

    # -----------------------------------------------------
    # FILTER BY DISTANCE
    # -----------------------------------------------------

    for index, document in enumerate(
        documents
    ):

        distance = (
            distances[index]
            if index < len(distances)
            else None
        )

        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        # Keep chunk if distance is acceptable
        if (
            distance is not None
            and distance <= threshold
        ):

            filtered_documents.append(
                document
            )

            filtered_metadatas.append(
                metadata
            )

            filtered_distances.append(
                distance
            )

    print(
        "RELEVANT CHUNKS:",
        len(filtered_documents)
    )

    print(
        "FILTERED DISTANCES:",
        filtered_distances
    )

    print(
        "========================================\n"
    )

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return {

        "documents":
            filtered_documents,

        "metadatas":
            filtered_metadatas,

        "distances":
            filtered_distances,

        "intent":
            intent,

        "top_k":
            top_k,

        "relevance_threshold":
            threshold,
    }