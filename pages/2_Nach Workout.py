import streamlit as st
import pandas as pd
import altair as alt

st.title("Radar-Test")

# hard-coded example data
df = pd.DataFrame({
    "Makronährstoff": ["Fett","Protein","Kohlenhydrate","Zucker"],
    "Gramm": [10, 30, 60, 5]
})

st.write(df)

area = (
    alt.Chart(df)
       .mark_area(interpolate="linear", opacity=0.3)
       .encode(
           theta=alt.Theta("Makronährstoff:N", sort=["Fett","Protein","Kohlenhydrate","Zucker"]),
           radius=alt.Radius("Gramm:Q"),
           color=alt.Color("Makronährstoff:N", legend=None)
       )
)
line = (
    alt.Chart(df)
       .mark_line(point=True)
       .encode(
           theta=alt.Theta("Makronährstoff:N", sort=["Fett","Protein","Kohlenhydrate","Zucker"]),
           radius=alt.Radius("Gramm:Q"),
           color=alt.Color("Makronährstoff:N", legend=None),
           tooltip=["Makronährstoff","Gramm:Q"]
       )
       .interactive()
)
radar = (area + line).properties(width=300, height=300)
st.altair_chart(radar, use_container_width=True)
