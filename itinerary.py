
from math import ceil


def generate_itinerary(recommendations, days):

    itinerary = []

    if days <= 0:
        return []

    # Convert recommendations into a list
    if hasattr(recommendations, "to_dict"):
        places = recommendations.to_dict("records")
    else:
        places = list(recommendations or [])

    if not places:
        return []

    # Maximum four activities per day
    max_activities_per_day = 4
    total_limit = days * max_activities_per_day

    # Keep only the highest-ranked recommendations
    places = places[:total_limit]

    schedule = [
        "09:00 AM",
        "11:30 AM",
        "02:00 PM",
        "04:30 PM"
    ]

    # Distribute places evenly across the requested days
    places_per_day = ceil(len(places) / days)

    for day in range(days):

        start_index = day * places_per_day
        end_index = start_index + places_per_day

        daily_places = places[start_index:end_index]

        activities = []

        for index, place in enumerate(daily_places):

            activities.append({
                "time": schedule[index],
                "place": place.get("name", "Unknown Place"),
                "description": place.get(
                    "description",
                    "Explore this destination."
                ),
                "duration": "1–2 hours"
            })

        itinerary.append({
            "day": day + 1,
            "activities": activities
        })

    return itinerary
