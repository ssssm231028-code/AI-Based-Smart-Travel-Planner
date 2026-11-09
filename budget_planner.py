
import math
import requests
import streamlit as st


ROUTING_URL = "https://api.geoapify.com/v1/routing"


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate straight-line distance in kilometres."""

    radius = 6371

    lat1, lon1, lat2, lon2 = map(
        math.radians, [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return radius * 2 * math.atan2(
        math.sqrt(a), math.sqrt(1 - a)
    )


def get_road_distance(start_coords, destination_coords):
    """Get road distance from Geoapify."""

    api_key = st.secrets["GEOAPIFY_API_KEY"]

    start_lat, start_lon = start_coords
    dest_lat, dest_lon = destination_coords

    params = {
        "waypoints": (
            f"{start_lat},{start_lon}|{dest_lat},{dest_lon}"
        ),
        "mode": "drive",
        "format": "json",
        "apiKey": api_key
    }

    response = requests.get(
        ROUTING_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()
    results = data.get("results", [])

    if not results:
        raise ValueError("No road route was returned.")

    distance_m = results[0].get("distance")

    if distance_m is None:
        raise ValueError("Route distance is missing.")

    return distance_m / 1000


def estimate_trip_budget(
    total_budget,
    travellers,
    days,
    transport_mode,
    start_coords,
    destination_coords
):
    """
    Estimate trip expenses automatically.

    Cost assumptions are illustrative Indian travel estimates,
    not live ticket or hotel quotations.
    """

    if travellers < 1 or days < 1:
        raise ValueError("Travellers and days must be at least 1.")

    road_km = get_road_distance(
        start_coords,
        destination_coords
    )

    # Round trip distance
    round_trip_km = road_km * 2

    # Straight-line distance is useful for flight estimates
    air_km = haversine_distance(
        start_coords[0],
        start_coords[1],
        destination_coords[0],
        destination_coords[1]
    )

    # --------------------------------
    # TRANSPORT ESTIMATION
    # --------------------------------

    mode = transport_mode.lower()

    if mode == "bus":
        transport = max(
            round_trip_km * 1.8 * travellers,
            300 * travellers
        )

    elif mode == "train":
        transport = max(
            round_trip_km * 1.1 * travellers,
            200 * travellers
        )

    elif mode == "flight":
        transport = max(
            (air_km * 5 + 1800) * 2 * travellers,
            3500 * travellers
        )

    elif mode == "car":
        transport = (
            round_trip_km / 15 * 105
            + round_trip_km * 1.5
        )

    elif mode == "bike":
        transport = (
            round_trip_km / 40 * 105
            + round_trip_km * 0.4
        )

    else:
        raise ValueError("Unsupported transportation method.")

    transport = round(transport)

    # --------------------------------
    # OTHER EXPENSE ESTIMATES
    # --------------------------------

    nights = max(days - 1, 1)

    rooms = math.ceil(travellers / 2)

    food = travellers * days * 350

    local_transport = travellers * days * 200

    sightseeing = travellers * days * 250

    basic_expenses = (
        transport
        + food
        + local_transport
        + sightseeing
    )

    # --------------------------------
    # AI ACCOMMODATION SELECTION
    # --------------------------------

    available_for_hotel = max(
        total_budget - basic_expenses,
        0
    )

    available_per_room_night = (
        available_for_hotel / (rooms * nights)
    )

    if available_per_room_night >= 3500:
        hotel_type = "Premium"
        hotel_rate = 3500

    elif available_per_room_night >= 1800:
        hotel_type = "Standard"
        hotel_rate = 1800

    else:
        hotel_type = "Budget"
        hotel_rate = 1000

    accommodation = (
        rooms * nights * hotel_rate
    )

    # --------------------------------
    # EMERGENCY RESERVE
    # --------------------------------

    subtotal = (
        basic_expenses + accommodation
    )

    emergency = round(subtotal * 0.08)

    estimated_total = subtotal + emergency

    remaining = total_budget - estimated_total

    expenses = {
        "Transportation": transport,
        "Accommodation": accommodation,
        "Food": food,
        "Local Transportation": local_transport,
        "Sightseeing": sightseeing,
        "Emergency Reserve": emergency
    }

    # --------------------------------
    # SUGGESTIONS
    # --------------------------------

    suggestions = []

    if remaining >= 0:

        suggestions.append(
            f"Approximately ₹{remaining:,.0f} remains "
            "after estimated expenses."
        )

        if hotel_type == "Budget" and remaining >= rooms * nights * 800:
            suggestions.append(
                "You may be able to upgrade to a standard hotel."
            )

        elif hotel_type == "Standard" and remaining >= rooms * nights * 1700:
            suggestions.append(
                "You may be able to upgrade to a premium hotel."
            )

        suggestions.append(
            "You can keep the remaining money as savings "
            "or spend it on additional activities."
        )

    else:

        suggestions.append(
            f"You need approximately ₹{abs(remaining):,.0f} "
            "more than your available budget."
        )

        suggestions.append(
            "Try cheaper transport, shared accommodation "
            "or fewer paid sightseeing activities."
        )

    return {
        "distance_km": round(road_km, 1),
        "round_trip_km": round(round_trip_km, 1),
        "transport_mode": transport_mode,
        "hotel_type": hotel_type,
        "details": expenses,
        "total": round(estimated_total),
        "budget": float(total_budget),
        "remaining": round(remaining),
        "per_person": round(estimated_total / travellers),
        "per_day": round(estimated_total / days),
        "suggestions": suggestions,
        "within_budget": remaining >= 0,
        "price_type": "Estimated, not live quotations"
    }
