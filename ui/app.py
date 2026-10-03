import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Black Box", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for aesthetics
st.markdown("""
<style>
    .reportview-container {
        background: #fafafa;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("⬛ Black Box")
st.sidebar.markdown("### Agent Flight Recorder")
page = st.sidebar.radio("Navigation", ["Dashboard", "Run Investigation", "Replay Lab", "Comparison", "Evaluation"])

def fetch_api(endpoint):
    try:
        res = requests.get(f"{API_URL}{endpoint}")
        if res.status_code == 200:
            return res.json()
        st.error(f"Error {res.status_code}: {res.text}")
    except Exception as e:
        st.warning(f"Failed to connect to API: {e} (Is the backend running?)")
    return None

if page == "Dashboard":
    st.title("Runs Dashboard")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Executions", "152", "+12 this hour")
    col2.metric("Success Rate", "87%", "-2%")
    col3.metric("Critical Failures", "20", "Requires Investigation")
    
    st.markdown("### Recent Runs")
    df = pd.DataFrame([
        {"Run ID": "run-123", "Scenario": "flight_basic", "Steps": 7, "Status": "FAILURE", "Time": "2026-10-03 16:30"},
        {"Run ID": "run-122", "Scenario": "flight_basic", "Steps": 7, "Status": "SUCCESS", "Time": "2026-10-03 16:25"},
        {"Run ID": "run-121", "Scenario": "hotel_booking", "Steps": 5, "Status": "SUCCESS", "Time": "2026-10-03 16:15"}
    ])
    st.dataframe(df, use_container_width=True)

elif page == "Run Investigation":
    st.title("Run Investigation")
    
    col_search, _ = st.columns([1, 2])
    with col_search:
        run_id = st.text_input("Run ID", value="run-123")
        load_btn = st.button("Load Trace", type="primary")
        
    if load_btn or run_id:
        run_data = fetch_api(f"/runs/{run_id}")
        diag_data = fetch_api(f"/runs/{run_id}/diagnosis")
        
        if run_data:
            if run_data['status'] == 'failure':
                st.error(f"Run {run_id} terminated with status: {run_data['status'].upper()}")
            else:
                st.success(f"Run {run_id} completed successfully.")
                
            tab1, tab2 = st.tabs(["Execution Timeline", "AI Diagnosis"])
            
            with tab1:
                for step in run_data.get("ordered_steps", []):
                    color = "🔴" if step.get("status") == "failure" else "🟢"
                    with st.expander(f"{color} Step {step['step_index']}: {step['tool'] or step['step_type']} ({step['step_id']})"):
                        cols = st.columns(2)
                        with cols[0]:
                            st.markdown("**Inputs:**")
                            st.json(step.get("input_summary", {}))
                            st.markdown("**State Before:**")
                            st.json(step.get("state_before", {}))
                        with cols[1]:
                            st.markdown("**Outputs:**")
                            st.json(step.get("output_summary", {}))
                            st.markdown("**State After:**")
                            st.json(step.get("state_after", {}))
                        if step.get("error_message"):
                            st.error(f"Error: {step['error_type']} - {step['error_message']}")

            with tab2:
                if diag_data:
                    st.markdown(f"**Model Version:** `{diag_data.get('model_version')}`")
                    for rank in diag_data.get("ranked_steps", []):
                        st.warning(f"**Suspicious Step Found:** `{rank['step_id']}` (Confidence Score: {rank['score']})")
                        st.markdown("### Ground-Truth Evidence")
                        for ev in rank.get("evidence", []):
                            st.markdown(f"- {ev}")
                else:
                    st.info("No diagnosis data available for this run.")

elif page == "Replay Lab":
    st.title("Replay Lab")
    st.markdown("Modify state from a known checkpoint and run counterfactuals.")
    
    with st.form("replay_form"):
        st.selectbox("Select Checkpoint", ["ckpt-5 (Step 5 - validate_availability)", "ckpt-4 (Step 4)"])
        st.selectbox("Modification Type", ["change_tool_result", "change_parameter", "change_branch"])
        st.text_area("Modification Payload (JSON)", value='{\n  "step_id": "step-5",\n  "value": {"available": true}\n}')
        
        if st.form_submit_button("Run Counterfactual", type="primary"):
            st.success("Counterfactual run started. Generated new Run ID: run-456")

elif page == "Comparison":
    st.title("Trace Comparison")
    st.markdown("Compare the original failure against the counterfactual replay.")
    
    cols = st.columns([1, 1, 1])
    orig_id = cols[0].text_input("Original Run", "run-123")
    alt_id = cols[1].text_input("Alternative Run", "run-456")
    # For spacing
    st.write("")
    if cols[2].button("Compare", type="primary", use_container_width=True):
        data = fetch_api(f"/runs/compare?original_id={orig_id}&alternative_id={alt_id}")
        if data:
            st.markdown("### Results")
            metric_cols = st.columns(4)
            metric_cols[0].metric("Common Prefix Steps", data.get("common_prefix_steps"))
            metric_cols[1].metric("Changed Steps", len(data.get("changed_steps", [])))
            metric_cols[2].metric("Rerun Steps", len(data.get("rerun_steps", [])))
            metric_cols[3].metric("Runtime Savings", f"{data.get('runtime_original_ms', 0) - data.get('runtime_alternative_ms', 0)}ms")
            
            st.markdown("### Outcome")
            st.write(f"Original Status: **{data.get('final_status_original', '').upper()}**")
            st.write(f"Counterfactual Status: **{data.get('final_status_alternative', '').upper()}**")

elif page == "Evaluation":
    st.title("Evaluation Metrics")
    data = fetch_api("/evaluation")
    if data:
        metrics = data.get("metrics", {})
        
        st.subheader("Localization Performance")
        loc_cols = st.columns(2)
        loc_cols[0].metric("Top-1 Localization", f"{metrics.get('top_1_localization', 0)*100}%")
        loc_cols[1].metric("Top-3 Localization", f"{metrics.get('top_3_localization', 0)*100}%")
        
        st.subheader("Diagnosis Accuracy")
        acc_cols = st.columns(3)
        acc_cols[0].metric("Precision", metrics.get("precision", 0))
        acc_cols[1].metric("Recall", metrics.get("recall", 0))
        acc_cols[2].metric("F1 Score", metrics.get("f1", 0))
        
        st.subheader("Replay Efficiency")
        st.metric("Recovery Rate", f"{metrics.get('recovery_rate', 0)*100}%")
