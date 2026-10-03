import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Black Box", layout="wide")
st.title("Black Box - Agent Flight Recorder")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Run Investigation", "Replay Lab", "Comparison", "Evaluation"])

if page == "Dashboard":
    st.header("Runs Dashboard")
    st.write("Displaying sample run data (Mocked).")
    st.metric(label="Total Runs", value=1)
    st.metric(label="Success Rate", value="0%")
    
elif page == "Run Investigation":
    st.header("Run Investigation")
    st.write("Execution timeline and diagnosis will appear here.")
    
elif page == "Replay Lab":
    st.header("Replay Lab")
    st.write("Modify state and run counterfactuals here.")
    
elif page == "Comparison":
    st.header("Comparison")
    st.write("Compare original vs alternative runs.")

elif page == "Evaluation":
    st.header("Evaluation")
    st.write("View ML model evaluation metrics.")
