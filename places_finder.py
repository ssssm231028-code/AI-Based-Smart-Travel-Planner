
import requests
import streamlit as st
import re


# ----------------------------------
# GEOAPIFY API CONFIGURATION
# ----------------------------------

GEOCODING_URL = "https://api.geoapify.com/v1/geocode/search"

PLACES_URL = "https://api.geoapify.com/v2/places"


# ----------------------------------
# DESTINATION GEOCODING
# ----------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def find_destination(destination):

    destination = destination.strip()

    if not destination:
        raise ValueError("Please enter a destination.")

    api_key = st.secrets["GEOAPIFY_API_KEY"]

    params = {
        "text": destination,
        "filter": "countrycode:in",
        "type": "locality",
        "format": "json",
        "limit": 5,
        "apiKey": api_key
    }

    response = requests.get(
        GEOCODING_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    results = response.json().get("results", [])

    if not results:

        raise ValueError(
            f"Destination '{destination}' was not found in India."
        )

    # Prefer exact name match

    selected = next(
        (
            item for item in results
            if item.get("name", "").strip().lower()
            == destination.lower()
        ),
        results[0]
    )

    place_id = selected.get("place_id")

    if not place_id:

        raise ValueError(
            "Geoapify did not return a boundary ID."
        )

    return {
        "name": selected.get("name", destination),
        "place_id": place_id,
        "lat": selected["lat"],
        "lon": selected["lon"],
        "result_type": selected.get(
            "result_type",
            "unknown"
        )
    }


# ----------------------------------
# TEXT NORMALIZATION
# ----------------------------------

def normalize_name(name):

    if not name:
        return ""

    name = str(name).lower()

    name = re.sub(
        r"[^a-z0-9]+",
        " ",
        name
    )

    return " ".join(name.split())


# ----------------------------------
# TOURIST PLACE DISCOVERY
# ----------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def find_tourist_places(destination):

    api_key = st.secrets["GEOAPIFY_API_KEY"]

    location = find_destination(destination)

    places = []

    seen_ids = set()

    # ----------------------------------
    # EXPANDED TOURIST CATEGORIES
    # ----------------------------------

    categories = (
        "tourism,"
        "heritage,"
        "building.historic,"
        "entertainment.museum,"
        "religion,"
        "memorial,"
        "leisure,"
        "natural,"
        "beach"
    )

    # ----------------------------------
    # PAGINATED DISCOVERY
    # ----------------------------------

    page_size = 100

    max_results = 500

    for offset in range(0, max_results, page_size):

        params = {
            "categories": categories,
            "filter": f"place:{location['place_id']}",
            "limit": page_size,
            "offset": offset,
            "lang": "en",
            "apiKey": api_key
        }

        response = requests.get(
            PLACES_URL,
            params=params,
            timeout=45
        )

        response.raise_for_status()

        data = response.json()

        features = data.get("features", [])

        if not features:
            break

        for feature in features:

            properties = feature.get(
                "properties",
                {}
            )

            name = properties.get("name")

            if not name:
                continue

            # ----------------------------------
            # DUPLICATE REMOVAL
            # ----------------------------------

            place_id = properties.get("place_id")

            clean_name = normalize_name(name)

            if place_id:

                unique_id = place_id

            else:

                unique_id = clean_name

            if unique_id in seen_ids:
                continue

            seen_ids.add(unique_id)

            # ----------------------------------
            # CATEGORY INFORMATION
            # ----------------------------------

            place_categories = properties.get(
                "categories",
                []
            )

            if isinstance(place_categories, str):

                place_categories = [
                    place_categories
                ]

            category_text = ", ".join(
                place_categories
            )

            # ----------------------------------
            # DESCRIPTION
            # ----------------------------------

            description = properties.get(
                "formatted"
            )

            if not description:

                description = (
                    properties.get("address_line1")
                    or "Tourist attraction"
                )

            # ----------------------------------
            # COORDINATES
            # ----------------------------------

            latitude = properties.get("lat")

            longitude = properties.get("lon")

            if latitude is None or longitude is None:

                coordinates = (
                    feature.get("geometry", {})
                    .get("coordinates", [])
                )

                if len(coordinates) >= 2:

                    longitude = coordinates[0]

                    latitude = coordinates[1]

            # ----------------------------------
            # FINAL PLACE DATA
            # ----------------------------------

            places.append({

                "name": name,

                "category": category_text,

                "description": description,

                "lat": latitude,

                "lon": longitude,

                "place_id": place_id

            })

        # Stop when the current page is incomplete

        if len(features) < page_size:
            break

    # ----------------------------------
    # FINAL VALIDATION
    # ----------------------------------

    if not places:

        raise ValueError(
            f"No tourist places found inside "
            f"{location['name']}."
        )

    return places
