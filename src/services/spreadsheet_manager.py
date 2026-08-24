import re
from typing import Any, Dict, List, Optional

import pandas as pd


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def _normalize(value: Any) -> str:
    """Normalize text for lightweight dataset relevance matching."""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _tokens(value: Any) -> set[str]:
    return {
        token
        for token in _normalize(value).split()
        if len(token) >= 2
    }


# =========================================================
# REGISTRATION
# =========================================================

def register_csv(
    registry: Dict[str, Dict[str, Any]],
    file_key: str,
    file_name: str,
    dataframe: pd.DataFrame,
) -> None:
    """Register one CSV DataFrame."""
    registry[f"{file_key}::CSV"] = {
        "file_name": file_name,
        "sheet_name": None,
        "dataframe": dataframe,
    }


def register_xlsx(
    registry: Dict[str, Dict[str, Any]],
    file_key: str,
    file_name: str,
    dataframes: Dict[str, pd.DataFrame],
) -> None:
    """Register every Excel sheet as an independent dataset."""
    for sheet_name, dataframe in dataframes.items():
        registry[f"{file_key}::{sheet_name}"] = {
            "file_name": file_name,
            "sheet_name": sheet_name,
            "dataframe": dataframe,
        }


# =========================================================
# DATASET DESCRIPTION
# =========================================================

def describe_dataset(item: Dict[str, Any]) -> Dict[str, Any]:
    """Return compact metadata used for routing and UI/debugging."""
    dataframe = item.get("dataframe")
    if not isinstance(dataframe, pd.DataFrame):
        return {}

    return {
        "file_name": item.get("file_name"),
        "sheet_name": item.get("sheet_name"),
        "rows": int(len(dataframe)),
        "columns": [str(column) for column in dataframe.columns],
    }


# =========================================================
# RELEVANCE SCORING
# =========================================================

def _score_dataset(item: Dict[str, Any], question: str) -> int:
    """Score how relevant a dataset is to a natural-language question."""
    dataframe = item.get("dataframe")
    if not isinstance(dataframe, pd.DataFrame):
        return -1

    question_tokens = _tokens(question)
    question_normalized = _normalize(question)

    file_name = str(item.get("file_name") or "")
    sheet_name = str(item.get("sheet_name") or "")

    score = 0

    # Explicit file/sheet mentions are the strongest signal.
    if file_name and _normalize(file_name) in question_normalized:
        score += 100

    if sheet_name and _normalize(sheet_name) in question_normalized:
        score += 90

    # Column names are strong evidence that this dataset is relevant.
    for column in dataframe.columns:
        column_tokens = _tokens(column)
        if not column_tokens:
            continue

        overlap = question_tokens.intersection(column_tokens)
        score += len(overlap) * 12

        normalized_column = _normalize(column)
        if normalized_column and normalized_column in question_normalized:
            score += 25

    # Categorical values provide useful evidence for questions such as
    # "How many employees are in Sales?" or "average tip on Sunday".
    for column in dataframe.select_dtypes(
        include=["object", "category", "bool"]
    ).columns:
        values = dataframe[column].dropna().astype(str).head(200)
        for value in values.unique():
            normalized_value = _normalize(value)
            if len(normalized_value) < 2:
                continue
            if normalized_value in question_normalized:
                score += 18
                break

    # A direct mention of a common business metric is useful when there
    # are several spreadsheets with different schemas.
    metric_aliases = {
        "salary": {"salary", "pay", "wage", "income"},
        "revenue": {"revenue", "sales", "turnover"},
        "tip": {"tip", "tips", "gratuity"},
        "age": {"age", "years"},
        "price": {"price", "cost", "amount"},
    }

    numeric_names = {
        token
        for column in dataframe.select_dtypes(include="number").columns
        for token in _tokens(column)
    }

    for aliases in metric_aliases.values():
        if question_tokens.intersection(aliases) and numeric_names.intersection(aliases):
            score += 20

    return score


# =========================================================
# DATASET SELECTION
# =========================================================

def rank_datasets(
    registry: Dict[str, Dict[str, Any]],
    question: str,
) -> List[Dict[str, Any]]:
    """Return datasets ordered from most to least relevant."""
    ranked = []

    for key, item in registry.items():
        score = _score_dataset(item, question)
        ranked.append({
            "key": key,
            "score": score,
            "item": item,
        })

    ranked.sort(key=lambda entry: entry["score"], reverse=True)
    return ranked


def select_dataset(
    registry: Dict[str, Dict[str, Any]],
    question: str,
) -> Optional[Dict[str, Any]]:
    """Select the best matching spreadsheet/sheet."""
    ranked = rank_datasets(registry, question)
    if not ranked:
        return None

    best = ranked[0]

    # If there is no meaningful relevance signal, let the analysis layer
    # try the datasets in their existing order rather than forcing a bad pick.
    if best["score"] <= 0:
        return None

    return best["item"]
