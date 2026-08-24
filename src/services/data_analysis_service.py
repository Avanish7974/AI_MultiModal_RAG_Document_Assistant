import re
import math
import pandas as pd


# =========================================================
# NORMALIZATION / COLUMN HELPERS
# =========================================================

def _normalize_text(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _find_column(df, text):
    if not text:
        return None

    query = _normalize_text(text)
    columns = list(df.columns)

    for column in columns:
        normalized = _normalize_text(column)
        if normalized == query:
            return column

    for column in columns:
        normalized = _normalize_text(column)
        if normalized and normalized in query:
            return column

    for column in columns:
        normalized = _normalize_text(column)
        if query and query in normalized:
            return column

    return None


def _numeric_columns(df):
    return list(df.select_dtypes(include="number").columns)


def _find_numeric_column(df, question, preferred_words=None):
    numeric_columns = _numeric_columns(df)
    normalized_question = _normalize_text(question)

    if preferred_words:
        for word in preferred_words:
            column = _find_column(df, word)
            if column in numeric_columns:
                return column

    for column in numeric_columns:
        normalized_column = _normalize_text(column)
        if normalized_column and normalized_column in normalized_question:
            return column

    # Support common column-name fragments.
    for column in numeric_columns:
        tokens = _normalize_text(column).split()
        if tokens and all(token in normalized_question.split() for token in tokens):
            return column

    if len(numeric_columns) == 1:
        return numeric_columns[0]

    return None


def _find_categorical_column(df, question):
    normalized_question = _normalize_text(question)

    # Prefer object/category/bool columns.
    candidates = list(
        df.select_dtypes(include=["object", "category", "bool"]).columns
    )

    for column in candidates:
        normalized = _normalize_text(column)
        if normalized and normalized in normalized_question:
            return column

    for column in df.columns:
        normalized = _normalize_text(column)
        if normalized and normalized in normalized_question:
            return column

    return None


def _extract_n(question, default=5):
    match = re.search(r"\b(\d+)\b", question)
    return int(match.group(1)) if match else default


def _numeric_series(df, column):
    return pd.to_numeric(df[column], errors="coerce")


def _clean_scalar(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def _format_value(value):
    value = _clean_scalar(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            return str(value)
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return str(value)


def _records(df, limit=None):
    result = df if limit is None else df.head(limit)
    return [
        {
            str(key): _clean_scalar(value)
            for key, value in row.items()
        }
        for row in result.to_dict(orient="records")
    ]


# =========================================================
# FILTER HELPERS
# =========================================================

def _extract_category_filter(df, question):
    """Find simple categorical filters such as 'in Sales' or 'for Sunday'."""
    column_candidates = list(
        df.select_dtypes(include=["object", "category", "bool"]).columns
    )

    patterns = [
        r"\b(?:in|from|for|on|where)\s+([^,?.]+)",
        r"\b(?:department|category|day|region|gender|status)\s*(?:is|=)?\s+([^,?.]+)",
    ]

    question_lower = question.lower()

    normalized_question = _normalize_text(question)

    for column in column_candidates:
        normalized_column = _normalize_text(column)
        if normalized_column not in normalized_question:
            continue

        for pattern in patterns:
            match = re.search(pattern, question, flags=re.IGNORECASE)
            if not match:
                continue

            raw_value = match.group(1).strip()
            raw_value = re.sub(
                r"\b(?:employees?|people|records?|customers?|sales|revenue|salary|tip|tips)\s*$",
                "",
                raw_value,
                flags=re.IGNORECASE,
            ).strip()

            if not raw_value:
                continue

            values = df[column].dropna().astype(str).str.strip()
            exact = values[values.str.lower() == raw_value.lower()]
            if not exact.empty:
                return column, exact.iloc[0]

            # Unique prefix/contains match for values such as 'Sunday'.
            contains = values[values.str.lower().str.contains(re.escape(raw_value.lower()), na=False)]
            if len(contains) == 1:
                return column, contains.iloc[0]

    # Fallback: detect a unique categorical value even when the
    # column name is not explicitly mentioned. This supports questions
    # such as "How many employees are in Sales?" when the column is
    # named Department.
    for column in column_candidates:
        values = df[column].dropna().astype(str).str.strip()
        unique_values = values.drop_duplicates().tolist()

        for value in unique_values:
            if not value:
                continue

            normalized_value = _normalize_text(value)
            if len(normalized_value) < 2:
                continue

            if normalized_value in normalized_question:
                return column, value

    # Common boolean-style wording such as "percentage of smokers"
    # for a column named Smoker containing Yes/No.
    for column in column_candidates:
        normalized_column = _normalize_text(column)
        if normalized_column and normalized_column.rstrip("s") in normalized_question:
            values = df[column].dropna().astype(str).str.strip()
            lower_values = {str(v).lower() for v in values.unique()}
            if {"yes", "no"}.issubset(lower_values):
                if any(word in normalized_question for word in ["smoker", "smokers", "smoking"]):
                    return column, next(v for v in values.unique() if str(v).lower() == "yes")

    return None


def _extract_numeric_filter(df, question):
    """Find simple comparisons such as salary > 50000 or age above 30."""
    column = _find_numeric_column(df, question)
    if column is None:
        return None

    patterns = [
        (r"(?:greater than|more than|above|over)\s*([\d,.]+)", ">"),
        (r"(?:less than|below|under)\s*([\d,.]+)", "<"),
        (r"(?:at least|minimum of)\s*([\d,.]+)", ">="),
        (r"(?:at most|maximum of)\s*([\d,.]+)", "<="),
        (r"(?:>=|=>)\s*([\d,.]+)", ">="),
        (r"(?:<=|=<)\s*([\d,.]+)", "<="),
        (r"(?:>)\s*([\d,.]+)", ">"),
        (r"(?:<)\s*([\d,.]+)", "<"),
    ]

    for pattern, operator in patterns:
        match = re.search(pattern, question, flags=re.IGNORECASE)
        if match:
            value = float(match.group(1).replace(",", ""))
            return column, operator, value

    return None


def _apply_filters(df, question):
    filtered = df.copy()
    filters = []

    category_filter = _extract_category_filter(df, question)
    if category_filter:
        column, value = category_filter
        mask = (
            filtered[column].astype(str).str.strip().str.lower()
            == str(value).strip().lower()
        )
        filtered = filtered.loc[mask]
        filters.append(f"{column} = {value}")

    numeric_filter = _extract_numeric_filter(df, question)
    if numeric_filter:
        column, operator, value = numeric_filter
        series = _numeric_series(filtered, column)
        if operator == ">":
            mask = series > value
        elif operator == "<":
            mask = series < value
        elif operator == ">=":
            mask = series >= value
        else:
            mask = series <= value
        filtered = filtered.loc[mask]
        filters.append(f"{column} {operator} {value:g}")

    return filtered, filters


# =========================================================
# INDIVIDUAL ANALYSES
# =========================================================

def _count(df, question):
    filtered, filters = _apply_filters(df, question)
    result = int(len(filtered))
    description = f"Count: {result:,} records"
    if filters:
        description += " after filtering by " + ", ".join(filters)

    return {
        "operation": "count",
        "result": result,
        "description": description,
        "filters": filters,
    }


def _aggregate(df, question, operation):
    filtered, filters = _apply_filters(df, question)
    column = _find_numeric_column(df, question)
    if column is None:
        return None

    series = _numeric_series(filtered, column).dropna()
    if series.empty:
        return None

    if operation == "sum":
        result = series.sum()
        label = "Total"
    elif operation == "mean":
        result = series.mean()
        label = "Average"
    elif operation == "min":
        result = series.min()
        label = "Minimum"
    else:
        result = series.max()
        label = "Maximum"

    description = f"{label} {column}: {_format_value(result)}"
    if filters:
        description += " after filtering by " + ", ".join(filters)

    return {
        "operation": operation,
        "column": str(column),
        "result": _clean_scalar(result),
        "description": description,
        "filters": filters,
    }


def _top_bottom(df, question, ascending):
    n = _extract_n(question, 5)
    column = _find_numeric_column(df, question)

    filtered, filters = _apply_filters(df, question)

    # If no sort column is specified, "top N records" /
    # "bottom N records" means the first/last N rows.
    if column is None:
        result_df = (
            filtered.tail(n) if ascending else filtered.head(n)
        )
        direction = "bottom" if ascending else "top"
        return {
            "operation": f"{direction}_n",
            "column": None,
            "n": n,
            "result": _records(result_df),
            "description": f"{direction.title()} {n} records from the filtered dataset.",
            "filters": filters,
        }

    result_df = filtered.sort_values(
        by=column,
        ascending=ascending
    ).head(n)

    direction = "bottom" if ascending else "top"
    return {
        "operation": f"{direction}_n",
        "column": str(column),
        "n": n,
        "result": _records(result_df),
        "description": f"{direction.title()} {n} records by {column}.",
        "filters": filters,
    }


def _sort(df, question):
    column = _find_numeric_column(df, question) or _find_categorical_column(df, question)
    if column is None:
        return None

    descending = any(
        phrase in question.lower()
        for phrase in ["descending", "high to low", "highest to lowest", "largest to smallest", "greatest"]
    )

    result_df = df.sort_values(by=column, ascending=not descending)
    return {
        "operation": "sort",
        "column": str(column),
        "ascending": not descending,
        "result": _records(result_df, limit=20),
        "description": f"Records sorted by {column} {'ascending' if not descending else 'descending'}.",
    }


def _group_by(df, question):
    group_column = _find_categorical_column(df, question)
    numeric_column = _find_numeric_column(df, question)

    if group_column is None:
        return None
    if numeric_column is None:
        grouped = df.groupby(group_column).size().reset_index(name="count")
        aggregation = "count"
    elif any(word in question.lower() for word in ["average", "mean", "avg"]):
        grouped = df.groupby(group_column)[numeric_column].mean().reset_index(name=numeric_column)
        aggregation = "mean"
    elif any(word in question.lower() for word in ["count", "number", "how many"]):
        grouped = df.groupby(group_column).size().reset_index(name="count")
        aggregation = "count"
    else:
        grouped = df.groupby(group_column)[numeric_column].sum().reset_index(name=numeric_column)
        aggregation = "sum"

    grouped = grouped.sort_values(
        by=grouped.columns[-1],
        ascending=False,
    )

    return {
        "operation": "group_by",
        "group_column": str(group_column),
        "value_column": str(numeric_column) if numeric_column is not None else None,
        "aggregation": aggregation,
        "result": _records(grouped),
        "description": f"Grouped by {group_column} using {aggregation}.",
    }


def _highest_group(df, question, lowest=False):
    """Handle: 'which department has highest revenue?' / 'which product lowest sales?'"""
    group_column = _find_categorical_column(df, question)
    numeric_column = _find_numeric_column(df, question)
    if group_column is None or numeric_column is None:
        return None

    lower = question.lower()
    if any(word in lower for word in ["average", "mean", "avg"]):
        grouped = df.groupby(group_column)[numeric_column].mean()
        aggregation = "mean"
    elif any(word in lower for word in ["total", "sum", "revenue", "sales generated", "generated"]):
        grouped = df.groupby(group_column)[numeric_column].sum()
        aggregation = "sum"
    else:
        grouped = df.groupby(group_column)[numeric_column].max()
        aggregation = "max"

    target = grouped.idxmin() if lowest else grouped.idxmax()
    value = grouped.loc[target]

    return {
        "operation": "lowest_group" if lowest else "highest_group",
        "group_column": str(group_column),
        "value_column": str(numeric_column),
        "aggregation": aggregation,
        "result": {
            str(group_column): _clean_scalar(target),
            str(numeric_column): _clean_scalar(value),
        },
        "description": (
            f"{target} has the {'lowest' if lowest else 'highest'} "
            f"{aggregation} {numeric_column}: {_format_value(value)}."
        ),
    }


def _percentage(df, question):
    filtered, filters = _apply_filters(df, question)
    if len(df) == 0:
        return None

    # Dataset category percentage, e.g. 'percentage of smokers'.
    category_filter = _extract_category_filter(df, question)
    if category_filter:
        column, value = category_filter
        matching = len(filtered)
        percentage = matching / len(df) * 100
        return {
            "operation": "percentage",
            "column": str(column),
            "filter_value": str(value),
            "matching_count": matching,
            "total_count": int(len(df)),
            "result": percentage,
            "description": f"{matching:,} of {len(df):,} records ({percentage:.2f}%) match {column} = {value}.",
            "filters": filters,
        }

    # Numeric comparison: 'what percentage is X of Y' is not tied to a dataset.
    match = re.search(r"percentage.*?(\d+(?:\.\d+)?)\s+(?:of|out of)\s+(\d+(?:\.\d+)?)", question.lower())
    if match:
        numerator = float(match.group(1))
        denominator = float(match.group(2))
        if denominator == 0:
            return None
        result = numerator / denominator * 100
        return {
            "operation": "percentage_calculation",
            "result": result,
            "description": f"{_format_value(numerator)} is {result:.2f}% of {_format_value(denominator)}.",
        }

    return None


# =========================================================
# PUBLIC ANALYSIS API
# =========================================================

def analyze_dataframe(dataframe, question, file_name=None, sheet_name=None):
    """
    Perform controlled spreadsheet analysis using pandas.

    The function returns a structured result. It never asks Gemini
    to perform the underlying numerical calculation.
    """
    if not isinstance(dataframe, pd.DataFrame):
        return {
            "success": False,
            "error": "Invalid DataFrame",
            "description": "The supplied data is not a pandas DataFrame.",
        }

    if dataframe.empty:
        return {
            "success": False,
            "error": "Empty DataFrame",
            "description": "The spreadsheet contains no data rows.",
        }

    question = str(question).strip()
    if not question:
        return {
            "success": False,
            "error": "Empty question",
            "description": "No question was provided.",
        }

    q = question.lower()
    result = None

    # Most specific intents first.
    if any(p in q for p in ["what percentage", "what percent", "percentage of", "percent of"]):
        result = _percentage(dataframe, question)

    # 'which X has highest/lowest Y' should be handled before top-N.
    if result is None and re.search(r"\b(which|what)\b.*\b(has|with)\b.*\b(highest|lowest|largest|smallest|greatest|least)\b", q):
        result = _highest_group(
            dataframe,
            question,
            lowest=any(word in q for word in ["lowest", "smallest", "least"]),
        )

    if result is None and any(p in q for p in ["group by", "group sales", "group data", "group total", "by department", "by category", "by product", "by region"]):
        result = _group_by(dataframe, question)

    if result is None and any(p in q for p in ["top ", "top records", "highest ", "largest ", "greatest "]):
        result = _top_bottom(dataframe, question, ascending=False)

    if result is None and any(p in q for p in ["bottom ", "bottom records", "lowest ", "smallest ", "least "]):
        result = _top_bottom(dataframe, question, ascending=True)

    if result is None and any(p in q for p in ["sort", "sorted", "order by"]):
        result = _sort(dataframe, question)

    if result is None and any(p in q for p in ["how many", "number of", "count"]):
        result = _count(dataframe, question)

    if result is None and any(p in q for p in ["average", "mean", "avg"]):
        result = _aggregate(dataframe, question, "mean")

    if result is None and any(p in q for p in ["total", "sum"]):
        result = _aggregate(dataframe, question, "sum")

    if result is None and any(p in q for p in ["minimum value", "minimum", "lowest value", "min"]):
        result = _aggregate(dataframe, question, "min")

    if result is None and any(p in q for p in ["maximum value", "maximum", "highest value", "max"]):
        result = _aggregate(dataframe, question, "max")

    # A lone 'revenue' is normally a total/revenue question in a spreadsheet.
    if result is None and "revenue" in q:
        result = _aggregate(dataframe, question, "sum")

    if result is None:
        return {
            "success": False,
            "error": "Unsupported analysis question",
            "description": "The question could not be mapped to a supported pandas analysis operation.",
        }

    result.update(
        {
            "success": True,
            "file_name": file_name,
            "sheet_name": sheet_name,
            "row_count": int(len(dataframe)),
            "column_count": int(len(dataframe.columns)),
            "columns": [str(column) for column in dataframe.columns],
        }
    )
    return result


def build_analysis_context(analysis_result, question):
    """Build factual context for Gemini. Gemini explains; pandas calculates."""
    if not analysis_result.get("success"):
        return "No valid pandas analysis result was generated."

    source = analysis_result.get("file_name") or "Unknown spreadsheet"
    sheet_name = analysis_result.get("sheet_name")
    if sheet_name:
        source += f" — Sheet: {sheet_name}"

    return f"""
DATA ANALYSIS RESULT

Question:
{question}

Source:
{source}

Operation:
{analysis_result.get('operation')}

Calculated Result:
{analysis_result.get('result')}

Factual Summary:
{analysis_result.get('description', '')}

Rows in source DataFrame:
{analysis_result.get('row_count')}

Columns:
{', '.join(analysis_result.get('columns', []))}

IMPORTANT:
The result above was calculated directly from the pandas DataFrame.
Do not recalculate, alter, estimate, or contradict the numerical result.
Explain the supplied result naturally and concisely.
If the result is a list/table, summarize it clearly and preserve the values.
"""
