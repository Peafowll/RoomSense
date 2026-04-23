import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

def custom_progress_bar(current, min_val, max_val, color="#4CAF50", height="30px"):
    """
    Renders a custom progress bar in Streamlit.
    Params:
        current (int) : The current value to be displayed on the bar
        min_val (int) : The minimum value of the bar, that is also displayed on the left of it
        max_val (int) : The maximum value of the bar, that is also displayed on the right of it
        color (str) : The hexcode of the color of the bar (e.g., '#4CAF50')
        height (str) : The height of the bar, in pixels (e.g., '25px')
    """
    try:
        percentage = max(0, min(100, ((current - min_val) / (max_val - min_val)) * 100))
    except ZeroDivisionError:
        percentage = 0
        
    html_content = f"""
<div style="display: flex; align-items: center; width: 100%; font-family: sans-serif; margin-bottom: 1rem;">
    <div style="margin-right: 15px; font-weight: 600; color: #666; font-size: 14px;">
        {min_val}
    </div>
    <div style="flex-grow: 1; background-color: #e2e8f0; border-radius: 50px; height: {height}; overflow: hidden; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
        <div style="width: {percentage}%; background-color: {color}; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px; transition: width 0.4s ease; text-shadow: 0px 1px 2px rgba(0,0,0,0.3);">
            {current}
        </div>
    </div>
    <div style="margin-left: 15px; font-weight: 600; color: #666; font-size: 14px;">
        {max_val}
    </div>
</div>
"""
    
    st.markdown(html_content, unsafe_allow_html=True)


def display_historical_graph(df, date_column, metric_column, title, line_color="#3b82f6", fill_area=True):
    """
    Renders a detailed historical interactive graph in Streamlit using Plotly.
    
    Parameters:
    - df (pd.DataFrame): The dataframe containing the historical data.
    - date_column (str): The name of the column containing dates/timestamps.
    - metric_column (str): The name of the column containing the data to plot.
    - title (str): The title displayed above the chart.
    - line_color (str): Hex color code for the line. Default is blue.
    - fill_area (bool): If True, fills the area under the line. Default is True.
    """
    
    df[date_column] = pd.to_datetime(df[date_column])
    
    if fill_area:
        fig = px.area(df, x=date_column, y=metric_column, title=title)
    else:
        fig = px.line(df, x=date_column, y=metric_column, title=title)
        
    fig.update_traces(line_color=line_color)
    
    fig.update_layout(
        xaxis_title="", 
        yaxis_title=metric_column,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(200, 200, 200, 0.2)')

    st.plotly_chart(fig, use_container_width=True)

