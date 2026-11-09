
import re
from difflib import SequenceMatcher

import pandas as pd


INTEREST_RULES = {
    "Nature": {
        "waterfall": 10, "forest": 9, "lake": 8,
        "wildlife": 10, "sanctuary": 9, "garden": 6,
        "national park": 10, "cave": 7, "beach": 5,
        "hill": 7, "mountain": 8, "nature": 7,
    },
    "Adventure": {
        "trek": 10, "hiking": 9, "camping": 9,
        "rafting": 10, "zipline": 10, "climbing": 9,
        "paragliding": 10, "safari": 8, "adventure": 10,
    },
    "Historical Places": {
        "archaeological": 12, "heritage": 10,
        "historic": 10, "historical": 10,
        "monument": 10, "fort": 10, "palace": 10,
        "ancient": 9, "ruins": 10, "temple": 8,
        "church": 7, "cathedral": 8, "mosque": 7,
        "museum": 5, "memorial": 7, "castle": 9,
        "royal enclosure": 11, "stone chariot": 12,
    },
    "Beaches": {
        "beach": 10, "coast": 8, "seaside": 9,
        "shore": 8, "island": 7,
    },
    "Shopping": {
        "market": 10, "shopping": 10, "bazaar": 10,
        "mall": 9, "handicraft": 9, "souvenir": 8,
    },
}

# Exclude activity listings and misleading historical matches.
ACTIVITY_TERMS = [
    "elephant bathing", "elephant bath",
    "walking tour", "guided tour", "boat ride",
    "camel ride",
]

HISTORICAL_EXCLUSIONS = [
    "termite castle",
    "wax world museum",
    "wax museum",
    "car museum",
    "automobile museum",
    "photo museum",
    "photography museum",
]

VIEWPOINT_TERMS = [
    "viewpoint", "view point", "panorama",
    "sunset point", "photo point",
]

# Museums with clear cultural, archaeological or heritage relevance.
CULTURAL_MUSEUMS = [
    "archaeological museum",
    "archeological museum",
    "museum of christian art",
    "goa chitra",
    "museum of goa",
    "moda goa museum",
]


def normalize_text(value):
    if value is None:
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def contains_term(text, term):
    text = normalize_text(text)
    term = normalize_text(term)

    return bool(
        text and term and
        re.search(
            r"(?<![a-z0-9])" + re.escape(term) +
            r"(?![a-z0-9])",
            text
        )
    )


def is_excluded(name, interest):
    name = normalize_text(name)

    if any(contains_term(name, term) for term in ACTIVITY_TERMS):
        return True

    if interest == "Historical Places":
        if name.startswith("near "):
            return True

        if any(
            contains_term(name, term)
            for term in HISTORICAL_EXCLUSIONS
        ):
            return True

    return False


def historical_score(name, category):
    name = normalize_text(name)
    category = normalize_text(category)

    score = 0
    matched = []

    for keyword, weight in INTEREST_RULES["Historical Places"].items():
        if contains_term(name, keyword):
            score += weight * 2
            matched.append(keyword)
        elif contains_term(category, keyword):
            score += weight
            matched.append(keyword)

    # A generic castle name alone is not enough evidence.
    if contains_term(name, "castle"):
        if not any(
            contains_term(category, term)
            for term in ["historic", "heritage", "fort", "castle"]
        ):
            score -= 12

    # Viewpoints are not equivalent to historical monuments.
    if any(contains_term(name, term) for term in VIEWPOINT_TERMS):
        score -= 18

    # Give recognised cultural and archaeological museums a boost.
    if any(contains_term(name, term) for term in CULTURAL_MUSEUMS):
        score += 10

    return max(0, score), matched


def general_score(name, category, interest):
    name = normalize_text(name)
    category = normalize_text(category)

    score = 0
    matched = []

    for keyword, weight in INTEREST_RULES.get(interest, {}).items():
        if contains_term(name, keyword):
            score += weight * 2
            matched.append(keyword)
        elif contains_term(category, keyword):
            score += weight
            matched.append(keyword)

    return score, matched


def are_duplicates(name1, name2):
    first = normalize_text(name1)
    second = normalize_text(name2)

    if first == second:
        return True

    # Compare names after removing generic museum wording.
    generic_words = {"the", "open", "air", "museum", "site"}

    first_core = " ".join(
        word for word in first.split() if word not in generic_words
    )
    second_core = " ".join(
        word for word in second.split() if word not in generic_words
    )

    if first_core and first_core == second_core:
        return True

    return (
        bool(first_core and second_core)
        and SequenceMatcher(None, first_core, second_core).ratio() >= 0.92
    )


def remove_duplicates(dataframe):
    kept = []

    for _, row in dataframe.iterrows():
        name = row.get("name", "")

        if not normalize_text(name):
            continue

        if not any(
            are_duplicates(name, existing.get("name", ""))
            for existing in kept
        ):
            kept.append(row)

    return pd.DataFrame(kept)


def recommend_dynamic_places(
    places,
    interest,
    destination=None,
    limit=15
):
    if places is None or len(places) == 0:
        return pd.DataFrame()

    if isinstance(places, pd.DataFrame):
        dataframe = places.copy()
    else:
        dataframe = pd.DataFrame(places)

    if dataframe.empty:
        return dataframe

    for column in [
        "name", "category", "description",
        "lat", "lon", "place_id"
    ]:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe["name"] = dataframe["name"].fillna("").astype(str)
    dataframe["category"] = dataframe["category"].fillna("").astype(str)

    dataframe = dataframe[
        ~dataframe["name"].apply(
            lambda name: is_excluded(name, interest)
        )
    ].copy()

    if dataframe.empty:
        return dataframe

    dataframe = remove_duplicates(dataframe)

    scores = []
    matched_interests = []

    for _, row in dataframe.iterrows():
        name = row["name"]
        category = row["category"]

        if interest == "Historical Places":
            raw_score, matched = historical_score(name, category)

        elif interest == "Mixed":
            all_scores = []
            matched = []

            for selected_interest in INTEREST_RULES:
                if selected_interest == "Historical Places":
                    current_score, current_matches = historical_score(
                        name, category
                    )
                else:
                    current_score, current_matches = general_score(
                        name, category, selected_interest
                    )

                all_scores.append(current_score)
                matched.extend(current_matches)

            raw_score = max(all_scores, default=0)

        else:
            raw_score, matched = general_score(
                name, category, interest
            )

        percentage = min(100, round(raw_score / 35 * 100, 1))

        scores.append(percentage)
        matched_interests.append(
            ", ".join(sorted(set(matched)))
        )

    dataframe["score"] = scores
    dataframe["matched_interests"] = matched_interests

    dataframe = dataframe[dataframe["score"] > 0]

    return (
        dataframe
        .sort_values("score", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
