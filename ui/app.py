import streamlit as st
import requests
import json

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Black Box", layout="wide")
st.title("Black Box - Agent Flight Recorder")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Run Investigation", "Replay Lab", "Comparison", "Evaluation"])

# Utility to safely fetch from API
def fetch_api(endpoint):
    try:
        res = requests.get(f"{API_URL}{endpoint}")
        if res.status_code == 200:
            return res.json()
        st.error(f"Error {res.status_code}: {res.text}")
    except Exception as e:
        st.error(f"Failed to connect to API: {e}")
    return None

if page == "Dashboard":
    st.header("Runs Dashboard")
    st.write("Displaying sample run data.")
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total Runs", value=152)
    col2.metric(label="Success Rate", value="87%")
    col3.metric(label="Failed Runs", value=20)
    
    st.subheader("Recent Runs")
    # Mocking a list of runs
    st.table([
        {"Run ID": "run-123", "Scenario": "flight_basic", "Status": "failure", "Steps": 7},
        {"Run ID": "run-122", "Scenario": "flight_basic", "Status": "success", "Steps": 7},
    ])
    
elif page == "Run Investigation":
    st.header("Run Investigation")
    run_id = st.text_input("Enter Run ID:", value="run-123")
    
    if st.button("Load Run"):
        with st.spinner("Fetching trace..."):
            run_data = fetch_api(f"/runs/{run_id}")
            diag_data = fetch_api(f"/runs/{run_id}/diagnosis")
            
            if run_data:
                st.subheader(f"Status: {run_data['status'].upper()}")
                
                st.write("### Execution Timeline")
                for step in run_data.get("ordered_steps", []):
                    with st.expander(f"Step {step['step_index']}: {step['step_id']} - {step['status'].upper()}"):
                        st.json(step)
                        
            if diag_data:
                st.write("### AI Diagnosis")
                st.write(f"Model: {diag_data.get('model_version')}")
                for rank in diag_data.get("ranked_steps", []):
                    st.error(f"Suspicious Step: {rank['step_id']} (Score: {rank['score']})")
                    st.write("**Evidence:**")
                    for ev in rank.get("evidence", []):
                        st.write(f"- {ev}")
    
elif page == "Replay Lab":
    st.header("Replay Lab")
    st.write("Modify state and run counterfactuals here.")
    st.info("Select a checkpoint from the Investigation page to modify its outcome.")
    
elif page == "Comparison":
    st.header("Comparison")
    st.write("Compare original vs alternative runs.")
    if st.button("Compare run-123 vs run-456"):
        data = fetch_api("/runs/compare?original_id=run-123&alternative_id=run-456")
        if data:
            st.json(data)

elif page == "Evaluation":
    st.header("Evaluation")
    st.write("View ML model evaluation metrics.")
    data = fetch_api("/evaluation")
    if data:
        metrics = data.get("metrics", {})
        cols = st.columns(3)
        cols[0].metric("Precision", metrics.get("precision", 0))
        cols[1].metric("Recall", metrics.get("recall", 0))
        cols[2].metric("F1 Score", metrics.get("f1", 0))
