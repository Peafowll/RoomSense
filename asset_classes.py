import streamlit as st
def custom_progress_bar(current, min_val, max_val, color="#4CAF50", height="30px"):
    """
    Renders a custom progress bar in Streamlit.
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