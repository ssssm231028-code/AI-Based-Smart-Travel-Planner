
import streamlit as st
import requests
import folium

from streamlit_folium import st_folium

from itinerary import generate_itinerary
from budget_planner import estimate_trip_budget
from places_finder import find_tourist_places, find_destination
from recommender import recommend_dynamic_places

def get_road_route(map_places):

    coordinates = []

    for _, place in map_places.iterrows():

        lat = float(place["lat"])
        lon = float(place["lon"])

        coordinates.append(f"{lon},{lat}")

    if len(coordinates) < 2:
        return None

    route_url = (
        "https://router.project-osrm.org/route/v1/driving/"
        + ";".join(coordinates)
    )

    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false"
    }

    try:
        response = requests.get(
            route_url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        if data.get("code") != "Ok":
            return None

        route = data["routes"][0]

        # GeoJSON coordinates are [longitude, latitude].
        route_coordinates = [
            [lat, lon]
            for lon, lat in route["geometry"]["coordinates"]
        ]

        return {
    "coordinates": route_coordinates,
    "distance_km": route["distance"] / 1000,
    "duration_minutes": route["duration"] / 60,
    "legs": [
        {
            "distance_km": leg["distance"] / 1000,
            "duration_minutes": leg["duration"] / 60
        }
        for leg in route.get("legs", [])
    ]
}

    except (requests.RequestException, KeyError, IndexError, TypeError):
        return None


# ----------------------------------
# PAGE CONFIGURATION
# ----------------------------------

st.set_page_config(
    page_title="AI Smart Travel Planner",
    page_icon="✈️",
    layout="wide"
)
@st.cache_data(ttl=86400, show_spinner=False)
def get_place_image(place_name, destination):

    url = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrlimit": 5,
        "gsrsearch": f"{place_name} {destination}",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 800
    }

    headers = {
        "User-Agent": "SmartTravelPlanner/1.0 (student project)"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        pages = response.json().get("query", {}).get("pages", {})

        for page in pages.values():

            image_info = page.get("imageinfo", [])

            if not image_info:
                continue

            info = image_info[0]

            image_url = info.get("thumburl") or info.get("url")

            if not image_url:
                continue

            metadata = info.get("extmetadata", {})

            license_name = metadata.get(
                "LicenseShortName", {}
            ).get("value", "See source page")

            return {
                "url": image_url,
                "license": license_name,
                "source": info.get("descriptionurl", "")
            }

    except requests.RequestException:
        return None

    return None


# ----------------------------------
# MAIN HEADING
# ----------------------------------

st.title("✈️ AI-Based Smart Travel Planner")

st.write(
    "Your intelligent assistant for planning smarter journeys."
)

st.divider()


# ----------------------------------
# TRAVEL DETAILS
# ----------------------------------

st.header("🌍 Plan Your Trip")

col1, col2 = st.columns(2)

with col1:

    starting_point = st.text_input(
        "Starting Location",
        placeholder="Example: Sullia"
    )

    destination = st.text_input(
        "Destination",
        placeholder="Example: Goa"
    )

    budget = st.number_input(
        "Total Budget (₹)",
        min_value=1000,
        value=5000,
        step=500
    )


with col2:

    people = st.number_input(
        "Number of Travellers",
        min_value=1,
        value=1,
        step=1
    )

    days = st.number_input(
        "Number of Days",
        min_value=1,
        value=2,
        step=1
    )

    interests = st.selectbox(
        "Travel Interests",
        [
            "Nature",
            "Adventure",
            "Historical Places",
            "Beaches",
            "Shopping",
            "Mixed"
        ]
    )

    transport_mode = st.selectbox(
        "Transportation Method",
        [
            "Bus",
            "Train",
            "Car",
            "Bike",
            "Flight"
        ]
    )


st.divider()


# ----------------------------------
# GENERATE TRAVEL PLAN
# ----------------------------------

if st.button(
    "Generate Travel Plan",
    type="primary"
):

    # ----------------------------------
    # INPUT VALIDATION
    # ----------------------------------

    if not starting_point.strip() or not destination.strip():

        st.warning(
            "Please enter your starting point and destination."
        )

        st.stop()

    if starting_point.strip().lower() == destination.strip().lower():

        st.warning(
            "Starting location and destination cannot be the same."
        )

        st.stop()


    st.success("Travel details collected successfully!")

    st.write("Starting Location:", starting_point)
    st.write("Destination:", destination)
    st.write("Budget:", f"₹{budget:,.0f}")
    st.write("Travellers:", people)
    st.write("Days:", days)
    st.write("Interests:", interests)
    st.write("Transportation:", transport_mode)

    st.divider()


    # ----------------------------------
    # TOURIST PLACE DISCOVERY
    # ----------------------------------

    try:

        with st.spinner("Discovering tourist places..."):

            discovered_places = find_tourist_places(
                destination
            )

            recommendations = recommend_dynamic_places(
                discovered_places,
                interests,
                destination
            )

    except requests.exceptions.RequestException as error:

        st.error("Unable to connect to the tourist place service.")
        st.caption(str(error))
        st.stop()

    except Exception as error:

        st.error("Unable to retrieve tourist places.")
        st.caption(str(error))
        st.stop()


    # ----------------------------------
    # AI RECOMMENDATIONS
    # ----------------------------------

    st.header("🤖 AI Recommended Tourist Places")

    if recommendations is None or recommendations.empty:

        st.warning(
            "No relevant tourist places found "
            "for your selected interest."
        )

        st.stop()


    for _, place in recommendations.iterrows():

        st.subheader(
            "📍 " + str(place["name"])
        )

        st.write(
            place["description"]
        )

        st.write(
            "AI Match Score:",
            f'{place["score"]:.1f}%'
        )

        st.divider()

    # ----------------------------------
    # INTERACTIVE TOURIST MAP
    # ----------------------------------

    st.header("🗺️ Interactive Tourist Map")

    map_places = recommendations.dropna(
        subset=["lat", "lon"]
    ).copy()

    map_places = map_places[
        map_places["lat"].between(-90, 90)
        & map_places["lon"].between(-180, 180)
    ]
    
    


    

  
    route_distance_lookup = {}

    if not map_places.empty:

        center_lat = map_places["lat"].astype(float).mean()
        center_lon = map_places["lon"].astype(float).mean()

        tourist_map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11
        )

        # Add attraction markers
        for _, place in map_places.iterrows():

            lat = float(place["lat"])
            lon = float(place["lon"])

            folium.Marker(
                location=[lat, lon],
                popup=str(place["name"]),
                tooltip=str(place["name"]),
                icon=folium.Icon(
                    color="red",
                    icon="info-sign"
                )
            ).add_to(tourist_map)

        # Get actual road route
        route_result = get_road_route(map_places)

        if route_result:

            # Store distance and time between consecutive attractions
            for index, leg in enumerate(route_result["legs"]):

                if index + 1 < len(map_places):

                    first_place = str(map_places.iloc[index]["name"])
                    second_place = str(map_places.iloc[index + 1]["name"])

                    route_distance_lookup[
                        (first_place, second_place)
                    ] = leg

            # Draw road route on map
            folium.PolyLine(
                route_result["coordinates"],
                color="blue",
                weight=5,
                opacity=0.8,
                tooltip="Driving road route"
            ).add_to(tourist_map)

            st.subheader("🚗 Road Route Information")

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Total Route Distance",
                    f"{route_result['distance_km']:.1f} km"
                )

            with col2:
                hours = int(route_result["duration_minutes"] // 60)
                minutes = int(route_result["duration_minutes"] % 60)

                st.metric(
                    "Estimated Driving Time",
                    f"{hours} hr {minutes} min"
                )

        else:
            st.warning(
                "Road route unavailable. Please check your internet connection."
            )

        # Display interactive map
        st_folium(
            tourist_map,
            width=None,
            height=550,
            returned_objects=[]
        )

    else:
        st.warning(
            "Location coordinates are unavailable for these attractions."
        )

    # ----------------------------------
    # ITINERARY GENERATION
    # ----------------------------------

    

    st.header("🗓️ Your AI Travel Itinerary")

    try:

        itinerary = generate_itinerary(
            recommendations,
            days
        )

        for day_plan in itinerary:

            st.subheader(
                f"📅 Day {day_plan['day']}"
            )

            if not day_plan["activities"]:

                st.info(
                    "No attractions available for this day."
                )

            else:

                for activity_index, activity in enumerate(
                    day_plan["activities"]
                ):

                    st.markdown(
                        f"**🕒 {activity['time']}**"
                    )

                    st.write(
                        "📍 " + activity["place"]
                    )

                    # Fetch tourist place photo
                    image_data = get_place_image(
                        activity["place"],
                        destination
                    )

                    if image_data:

                        st.image(
                            image_data["url"],
                            width="stretch"
                        )

                        st.caption(
                            f"Photo licence: {image_data['license']}"
                        )

                        if image_data["source"]:
                            st.markdown(
                                f"[View original photo]({image_data['source']})"
                            )

                    else:
                        st.info(
                            "Photo not available for this place."
                        )

                    st.write(
                        activity["description"]
                    )

                    st.caption(
                        "Estimated visit duration: "
                        + activity["duration"]
                    )

                    # Distance to the next attraction
                    if activity_index < len(day_plan["activities"]) - 1:

                        next_activity = day_plan["activities"][
                            activity_index + 1
                        ]

                        route_leg = route_distance_lookup.get(
                            (
                                activity["place"],
                                next_activity["place"]
                            )
                        )

                                            # Distance to the next attraction
                    if activity_index < len(day_plan["activities"]) - 1:

                        next_activity = day_plan["activities"][
                            activity_index + 1
                        ]

                        route_leg = route_distance_lookup.get(
                            (
                                activity["place"],
                                next_activity["place"]
                            )
                        )

                        if route_leg:

                            if route_leg["distance_km"] >= 0.1:

                                travel_minutes = round(
                                    route_leg["duration_minutes"]
                                )

                                st.info(
                                    f"🚗 Distance to next attraction: "
                                    f"{route_leg['distance_km']:.1f} km | "
                                    f"Estimated driving time: "
                                    f"{travel_minutes} min"
                                )

                            else:

                                st.info(
                                    "🚶 These attractions are very close together. "
                                    "Walking may be more practical than driving. "
                                    "Road distance is too small for a reliable estimate."
                                )

                    st.divider()


    except Exception as error:

        st.error("Unable to generate the itinerary.")
        st.caption(str(error))
        st.stop()

    # ----------------------------------
    # AUTOMATIC AI BUDGET PLANNER
    # ----------------------------------

    st.header("💰 AI-Based Automatic Budget Planner")

    try:

        with st.spinner(
            "AI is estimating your travel expenses..."
        ):

            # Find starting location coordinates
            start_location = find_destination(
                starting_point
            )

            # Find destination coordinates
            end_location = find_destination(
                destination
            )

            if not start_location:

                st.error(
                    f"Could not find starting location: {starting_point}"
                )

                st.stop()

            if not end_location:

                st.error(
                    f"Could not find destination: {destination}"
                )

                st.stop()

            # Automatically estimate expenses
            budget_plan = estimate_trip_budget(
                total_budget=budget,
                travellers=people,
                days=days,
                transport_mode=transport_mode,
                start_coords=(
                    start_location["lat"],
                    start_location["lon"]
                ),
                destination_coords=(
                    end_location["lat"],
                    end_location["lon"]
                )
            )

    except requests.exceptions.Timeout:

        st.error(
            "The travel estimation service timed out. "
            "Please try again."
        )

        st.stop()

    except requests.exceptions.RequestException as error:

        st.error(
            "Unable to connect to the travel estimation service."
        )

        st.caption(str(error))
        st.stop()

    except Exception as error:

        st.error(
            "Unable to generate the automatic budget estimate."
        )

        st.caption(str(error))
        st.stop()


    # ----------------------------------
    # TRAVEL DISTANCE
    # ----------------------------------

    st.subheader("📍 Travel Distance")

    distance_col1, distance_col2 = st.columns(2)

    with distance_col1:

        st.metric(
            "One-way Distance",
            f"{budget_plan['distance_km']:,.1f} km"
        )

    with distance_col2:

        st.metric(
            "Round-trip Distance",
            f"{budget_plan['round_trip_km']:,.1f} km"
        )


    # ----------------------------------
    # ESTIMATED TRIP COST
    # ----------------------------------

    st.subheader("💵 Estimated Trip Cost")

    cost_col1, cost_col2 = st.columns(2)

    with cost_col1:

        st.metric(
            "Total Estimated Cost",
            f"₹{budget_plan['total']:,.0f}"
        )

    with cost_col2:

        st.metric(
            "Cost Per Person",
            f"₹{budget_plan['per_person']:,.0f}"
        )

    st.metric(
        "Estimated Cost Per Day",
        f"₹{budget_plan['per_day']:,.0f}"
    )


    # ----------------------------------
    # AI ACCOMMODATION SELECTION
    # ----------------------------------

    st.subheader("🏨 AI-Selected Accommodation")

    hotel_type = budget_plan["hotel_type"]

    st.info(
        f"Recommended accommodation category: {hotel_type}"
    )

    st.write(
        "The accommodation category is automatically "
        "selected according to the available budget."
    )


    # ----------------------------------
    # EXPENSE BREAKDOWN
    # ----------------------------------

    st.subheader("📊 Expense Breakdown")

    for category, amount in budget_plan["details"].items():

        st.write(
            f"**{category}: ₹{amount:,.0f}**"
        )


    # ----------------------------------
    # BUDGET COMPARISON
    # ----------------------------------

    st.subheader("💰 Available Budget Comparison")

    st.write(
        f"Your Available Budget: ₹{budget:,.0f}"
    )

    st.write(
        f"Estimated Trip Cost: ₹{budget_plan['total']:,.0f}"
    )

    remaining = budget_plan["remaining"]

    if remaining >= 0:

        st.success(
            f"Your trip is within budget! "
            f"₹{remaining:,.0f} will remain."
        )

    else:

        st.error(
            f"Your budget is insufficient. "
            f"You need ₹{abs(remaining):,.0f} more."
        )


    # ----------------------------------
    # AI TRAVEL SUGGESTIONS
    # ----------------------------------

    st.subheader("🤖 AI Travel Suggestions")

    for suggestion in budget_plan["suggestions"]:

        st.write("• " + suggestion)


    # ----------------------------------
    # FINAL STATUS
    # ----------------------------------

    if budget_plan["within_budget"]:

        st.success(
            "Your estimated trip is within budget!"
        )

    else:

        st.warning(
            "Your estimated trip exceeds your budget. "
            "Consider cheaper alternatives."
        )


    # ----------------------------------
    # ESTIMATION DISCLAIMER
    # ----------------------------------

    st.caption(
        "Note: These are approximate model-based estimates. "
        "Actual bus, train, flight, hotel and sightseeing "
        "prices may vary."
    )
