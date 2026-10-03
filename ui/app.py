import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import numpy as np

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Black Box", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Glassmorphism & Neon aesthetics
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Neon Text & Glassmorphism cards */
    .metric-card-cyan {
        background: rgba(13, 25, 48, 0.6);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 255, 255, 0.2);
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    .metric-card-red {
        background: rgba(48, 13, 13, 0.6);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 0, 50, 0.2);
        box-shadow: 0 0 10px rgba(255, 0, 50, 0.1);
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    /* Hide default metric styles to use our custom cards */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        text-shadow: 0 0 5px rgba(255,255,255,0.3);
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("⬛ Black Box")
st.sidebar.markdown("### Agent Flight Recorder")
page = st.sidebar.radio("Navigation", [
    "🎛️ Dashboard", 
    "🔍 Run Investigation", 
    "🔬 Replay Lab", 
    "⚖️ Comparison", 
    "📊 Evaluation"
])

def fetch_api(endpoint):
    try:
        res = requests.get(f"{API_URL}{endpoint}")
        if res.status_code == 200:
            return res.json()
        st.error(f"Error {res.status_code}: {res.text}")
    except Exception as e:
        st.warning(f"Failed to connect to API: {e} (Is the backend running?)")
    return None

if page == "🎛️ Dashboard":
    st.title("🎛️ System Dashboard")
    
    # Custom Glass Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card-cyan">', unsafe_allow_html=True)
        st.metric("Total Executions", "152", "+12 this hour")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="metric-card-cyan">', unsafe_allow_html=True)
        st.metric("Success Rate", "87%", "-2%")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown('<div class="metric-card-red">', unsafe_allow_html=True)
        st.metric("Critical Failures", "20", "Requires Investigation", delta_color="inverse")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### ⚡ System Pulse")
    # Generate mock pulse data
    times = pd.date_range(end=pd.Timestamp.now(), periods=60, freq="1min")
    volumes = np.random.poisson(lam=5, size=60)
    pulse_df = pd.DataFrame({"Time": times, "Volume": volumes})
    
    fig = px.area(pulse_df, x="Time", y="Volume", 
                  color_discrete_sequence=["#00ffff"])
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("### 📋 Recent Runs")
    df = pd.DataFrame([
        {"Run ID": "run-123", "Scenario": "flight_basic", "Steps": 7, "Status": "FAILURE", "Time": "2026-10-03 16:30"},
        {"Run ID": "run-122", "Scenario": "flight_basic", "Steps": 7, "Status": "SUCCESS", "Time": "2026-10-03 16:25"},
        {"Run ID": "run-121", "Scenario": "hotel_booking", "Steps": 5, "Status": "SUCCESS", "Time": "2026-10-03 16:15"},
        {"Run ID": "run-120", "Scenario": "flight_basic", "Steps": 4, "Status": "FAILURE", "Time": "2026-10-03 16:10"},
    ])
    
    def highlight_status(val):
        color = '#00ffaa' if val == 'SUCCESS' else '#ff0032'
        return f'color: {color}; font-weight: bold; text-shadow: 0 0 5px {color};'
    
    styled_df = df.style.map(highlight_status, subset=['Status'])
    st.dataframe(styled_df, use_container_width=True)

elif page == "🔍 Run Investigation":
    st.title("🔍 Run Investigation")
    
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

elif page == "🔬 Replay Lab":
    st.title("🔬 Replay Lab")
    st.markdown("Modify state from a known checkpoint and run counterfactuals.")
    
    with st.form("replay_form"):
        st.selectbox("Select Checkpoint", ["ckpt-5 (Step 5 - validate_availability)", "ckpt-4 (Step 4)"])
        st.selectbox("Modification Type", ["change_tool_result", "change_parameter", "change_branch"])
        st.text_area("Modification Payload (JSON)", value='{\n  "step_id": "step-5",\n  "value": {"available": true}\n}')
        
        if st.form_submit_button("Run Counterfactual", type="primary"):
            st.success("Counterfactual run started. Generated new Run ID: run-456")

elif page == "⚖️ Comparison":
    st.title("⚖️ Trace Comparison")
    st.markdown("Compare the original failure against the counterfactual replay.")
    
    cols = st.columns([1, 1, 1])
    orig_id = cols[0].text_input("Original Run", "run-123")
    alt_id = cols[1].text_input("Alternative Run", "run-456")
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

elif page == "📊 Evaluation":
    st.title("📊 Evaluation Metrics")
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
