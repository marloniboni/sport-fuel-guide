# … (imports and MealDB code stay the same) …

# ─── 3) Edamam Nutrition Analysis ────────────────────────────────────────────
@st.cache_data
def analyze_calories(ingredient_lines: list[str]) -> int | None:
    """
    Calls Edamam Nutrition Analysis endpoint with full ingredient lines.
    Returns calories or None on failure, but prints debug info.
    """
    url = "https://api.edamam.com/api/nutrition-details"
    params = {"app_id": EDAMAM_APP_ID, "app_key": EDAMAM_APP_KEY}
    body = {"title": "Meal", "ingr": ingredient_lines}

    try:
        r = requests.post(url, params=params, json=body, timeout=10)
    except Exception as e:
        st.error(f"Nutrition request exception: {e}")
        return None

    # Debug output
    st.write("Nutrition API status:", r.status_code)
    try:
        js = r.json()
        st.write("Nutrition raw JSON:", js)
    except ValueError:
        st.write("Nutrition raw text:", r.text)

    if r.status_code != 200:
        st.error(f"Nutrition API returned {r.status_code}")
        return None

    return js.get("calories", None)

# ─── 4) Streamlit App ────────────────────────────────────────────────────────
# … same setup as before …

for label, col in zip(labels, cols):
    with col:
        # … MealDB picking …

        for m in picks:
            d = get_meal_details(m["idMeal"])
            # build ingredient lines
            ingr_lines = [
                f"{d[f'strMeasure{i}'].strip()} {d[f'strIngredient{i}'].strip()}"
                for i in range(1,21)
                if d.get(f"strIngredient{i}") and d[f"strIngredient{i}"].strip()
            ]

            kcal = analyze_calories(ingr_lines)
            if kcal is None:
                st.warning("Kalorien konnten nicht berechnet werden.")
            else:
                st.markdown(f"**{d['strMeal']} — {kcal} kcal**")
            # … rest of display …
