import streamlit as st
import pandas as pd
import json
from asset_classes import *

with open("dummydata.json", "r") as file:
    data = json.load(file)

st.title("Apartment Overview")


st.write(data)

# Temperature Bar
current_temp = data["temp"]
temp_color = "#F7E06A"
st.write("Temperature : ")
custom_progress_bar(
    current = current_temp,
    color = temp_color,
    min_val = 10,
    max_val = 35,
    height = "25px"
)

# Air Quality Bar
current_air_qual = data["air"]
air_color = "#C8F7F3"
st.write("Air Quality : ")
custom_progress_bar(
    current = current_air_qual,
    color = air_color,
    min_val = 400,
    max_val = 2000,
    height = "25px"
)

# Light % Bar
current_light_percentage = data["light"]
light_color = "#CFCFCF"
st.write("Light : ")
custom_progress_bar(
    current = current_light_percentage,
    color = light_color,
    min_val = 0,
    max_val = 100,
    height = "25px"
)



