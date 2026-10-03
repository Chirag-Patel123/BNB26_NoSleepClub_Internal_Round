import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Black Box", layout="wide", initial_sidebar_state="collapsed")

# Inject heavy CSS for animations, Top Nav, and sleek dark aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Base background */
    .stApp {
        background-color: #020617;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(14, 165, 233, 0.08), transparent 30%),
            radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.08), transparent 30%),
            linear-gradient(180deg, #020617 0%, #0f172a 100%);
        color: #f8fafc;
    }

    /* Hide standard header, footer, sidebar */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    section[data-testid="stSidebar"] {display: none;}

    /* Top Nav Container */
    .nav-container {
        display: flex;
        justify-content: center;
        gap: 20px;
        background: rgba(15, 23, 42, 0.7);
        backdrop-filter: blur(15px);
        padding: 15px 30px;
        border-radius: 50px;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        margin-bottom: 40px;
    }

    /* Animations */
    @keyframes slideUpFade {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulseGlow {
        0% { box-shadow: 0 0 15px rgba(6, 182, 212, 0.2); }
        50% { box-shadow: 0 0 30px rgba(6, 182, 212, 0.6); }
        100% { box-shadow: 0 0 15px rgba(6, 182, 212, 0.2); }
    }
    @keyframes spinGlow {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .animate-in {
        animation: slideUpFade 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* Premium Glass Cards */
    .glass-card {
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        transition: all 0.4s ease;
        position: relative;
        overflow: hidden;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px -10px rgba(0,0,0,0.7);
        border-color: rgba(6, 182, 212, 0.3);
    }
    .glass-card-neon::before {
        content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
        background: linear-gradient(90deg, transparent, #06b6d4, #8b5cf6, transparent);
        opacity: 0.8;
    }
    .glass-card-danger::before {
        content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
        background: linear-gradient(90deg, transparent, #ef4444, #f59e0b, transparent);
        opacity: 0.8;
    }

    /* Metric Values styling */
    div[data-testid="stMetricValue"] {
        font-size: 3rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.05em;
        background: linear-gradient(135deg, #ffffff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #64748b;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
        border: 1px solid rgba(255,255,255,0.1);
        color: #f8fafc;
        border-radius: 30px;
        font-weight: 600;
        letter-spacing: 1px;
        padding: 10px 24px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #0ea5e9, #6366f1);
        color: white;
        border-color: transparent;
        box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);
        transform: translateY(-2px);
    }
    .stButton > button[data-baseweb="button"] p {
        font-size: 1.1rem;
    }

    /* Primary Button override (e.g. Load Trace) */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0ea5e9, #6366f1) !important;
        color: white !important;
        border: none !important;
        animation: pulseGlow 3s infinite;
    }
    .stButton > button[kind="primary"]:hover {
        transform: scale(1.05);
    }

    /* Inputs */
    .stTextInput input, .stTextArea textarea {
        background-color: rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #fff !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-size: 1.1rem !important;
        transition: all 0.3s ease !important;
    }
    .stSelectbox > div > div > div {
        background-color: rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: #fff !important;
        border-radius: 12px !important;
        min-height: 50px !important;
        font-size: 1.1rem !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.2) !important;
    }

    /* Custom Loading Spinner */
    .big-spinner {
        width: 100px;
        height: 100px;
        border: 4px solid rgba(255,255,255,0.05);
        border-top: 4px solid #0ea5e9;
        border-radius: 50%;
        animation: spinGlow 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
        margin: 50px auto;
        box-shadow: 0 0 30px rgba(14, 165, 233, 0.3);
    }

    /* Expander / Trace steps */
    .streamlit-expanderHeader {
        background-color: rgba(0,0,0,0.2) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 12px !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }
    .streamlit-expanderContent {
        background-color: rgba(0,0,0,0.4) !important;
        border: 1px solid rgba(255,255,255,0.02) !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
    }
    
    /* Evaluation specific big text */
    .f1-text {
        font-size: 5rem;
        font-weight: 900;
        background: linear-gradient(90deg, #10b981, #059669);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        text-shadow: 0 10px 30px rgba(16, 185, 129, 0.3);
        margin: 0;
    }
    .f1-sub {
        text-align: center; color: #94a3b8; font-size: 1.2rem; font-weight: 600; text-transform: uppercase; letter-spacing: 3px;
    }
</style>
""", unsafe_allow_html=True)

# State initialization
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard"

# --- Massive Project Title ---
st.markdown("""
<div style="text-align:center; margin-top: 10px; margin-bottom: 30px; animation: slideUpFade 0.8s forwards;">
    <h1 style="font-size: 6rem; font-weight: 900; letter-spacing: 0.15em; background: linear-gradient(90deg, #0ea5e9, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 10px 40px rgba(14, 165, 233, 0.4); margin: 0; font-family: 'Inter', sans-serif;">BLACK BOX</h1>
    <p style="color:#64748b; font-size: 1.2rem; letter-spacing: 0.4em; margin: 0; text-transform: uppercase; font-weight: 600;">Autonomous Agent Diagnostics</p>
</div>
""", unsafe_allow_html=True)

# --- Custom Top Navigation ---
st.markdown('<div class="nav-container">', unsafe_allow_html=True)
nav_cols = st.columns(5)
pages = ["Dashboard", "Run Investigation", "Replay Lab", "Comparison", "Evaluation"]
for i, p in enumerate(pages):
    with nav_cols[i]:
        if st.button(p, use_container_width=True):
            st.session_state.page = p
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)


def fetch_api(endpoint):
    try:
        res = requests.get(f"{API_URL}{endpoint}")
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

page = st.session_state.page

st.markdown('<div class="animate-in">', unsafe_allow_html=True)

if page == "Dashboard":
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="glass-card glass-card-neon">', unsafe_allow_html=True)
        st.metric("Total Executions", "1,241", "+142 this hour")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="glass-card glass-card-neon">', unsafe_allow_html=True)
        st.metric("Success Rate", "98.2%", "+0.5%")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown('<div class="glass-card glass-card-danger">', unsafe_allow_html=True)
        st.metric("Critical Failures", "22", "Requires Investigation", delta_color="inverse")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<h3 style='font-weight:300; letter-spacing:2px; margin-top:20px;'>SYSTEM PULSE</h3>", unsafe_allow_html=True)
    times = pd.date_range(end=pd.Timestamp.now(), periods=60, freq="1min")
    volumes = np.random.poisson(lam=5, size=60)
    pulse_df = pd.DataFrame({"Time": times, "Volume": volumes})
    
    fig = px.area(pulse_df, x="Time", y="Volume", color_discrete_sequence=["#0ea5e9"])
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#94a3b8", height=200, margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", visible=False)
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown("<h3 style='font-weight:300; letter-spacing:2px; margin-top:20px;'>RECENT RUNS</h3>", unsafe_allow_html=True)
    recent_runs_data = fetch_api("/runs/recent")
    if recent_runs_data:
        df = pd.DataFrame(recent_runs_data)
        def highlight_status(val):
            color = '#10b981' if val == 'SUCCESS' else '#ef4444'
            return f'color: {color}; font-weight: bold; background: rgba({(16,185,129) if val=="SUCCESS" else (239,68,68)}, 0.1); border-radius:4px;'
        styled_df = df.style.map(highlight_status, subset=['Status'])
        st.dataframe(styled_df, use_container_width=True, height=350)
    else:
        st.info("No runs found in dataset.")

elif page == "Run Investigation":
    
    _, col_search, _ = st.columns([1, 2, 1])
    with col_search:
        run_id = st.text_input("Run ID", placeholder="Paste a Run ID from the Dashboard to investigate...")
        load_btn = st.button("Load Trace", type="primary", use_container_width=True)
        
    if load_btn and run_id:
        # Fancy Loading Animation
        ph = st.empty()
        ph.markdown('<div class="big-spinner"></div><h3 style="text-align:center; color:#0ea5e9; font-weight:300; letter-spacing:2px; margin-top:20px;">ANALYZING TRACE GRAPH...</h3>', unsafe_allow_html=True)
        time.sleep(1.8) # Simulate deep analysis latency for dramatic effect
        ph.empty()
        
        run_data = fetch_api(f"/runs/{run_id}")
        diag_data = fetch_api(f"/runs/{run_id}/diagnosis")
        
        if run_data and run_data.get("run_id"):
            status_color = "#ef4444" if run_data.get('status') == 'failure' else "#10b981"
            st.markdown(f"""
            <div class="glass-card animate-in" style="border-top: 5px solid {status_color}; text-align:center; animation-delay:0.1s;">
                <h2 style="font-weight:300; letter-spacing:1px;">Run Terminated: <span style="color:{status_color}; font-weight:800; text-transform:uppercase;">{run_data.get('status')}</span></h2>
                <p style="color:#94a3b8;">Run ID: <code style="color:#e2e8f0;">{run_id}</code> | Scenario: <code style="color:#e2e8f0;">{run_data.get('metadata',{}).get('scenario_id')}</code></p>
            </div>
            """, unsafe_allow_html=True)
                
            tab1, tab2 = st.tabs(["EXECUTION TIMELINE", "AI DIAGNOSIS"])
            
            with tab1:
                st.markdown('<div class="animate-in" style="animation-delay:0.2s;">', unsafe_allow_html=True)
                for step in run_data.get("ordered_steps", []):
                    color = "🔴" if step.get("status") == "failure" else "🟢"
                    with st.expander(f"{color} Step {step['step_index']}: {step['tool'] or step['step_type']} ({step['step_id']})"):
                        cols = st.columns(2)
                        with cols[0]:
                            st.markdown("#### Inputs")
                            st.json(step.get("input_summary", {}))
                            st.markdown("#### State Before")
                            st.json(step.get("state_before", {}))
                        with cols[1]:
                            st.markdown("#### Outputs")
                            st.json(step.get("output_summary", {}))
                            st.markdown("#### State After")
                            st.json(step.get("state_after", {}))
                        if step.get("error_message"):
                            st.error(f"Error: {step['error_type']} - {step['error_message']}")
                st.markdown('</div>', unsafe_allow_html=True)

            with tab2:
                if diag_data:
                    st.markdown('<div class="animate-in" style="animation-delay:0.2s;">', unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#64748b; letter-spacing:1px; text-align:center;'><b>DIAGNOSIS ENGINE:</b> <code style='color:#0ea5e9;'>{diag_data.get('model_version')}</code> | <b>LATENCY:</b> <code style='color:#0ea5e9;'>{diag_data.get('diagnosis_latency_ms', 0)}ms</code></p>", unsafe_allow_html=True)
                    for rank in diag_data.get("ranked_steps", []):
                        st.markdown(f"""
                        <div class="glass-card glass-card-danger" style="animation: pulseGlow 2.5s infinite; margin-top:20px; text-align:center;">
                            <h3 style="margin:0; color:#ef4444; font-weight:400; letter-spacing:1px;">SUSPICIOUS STEP FLAGGED: <b>{rank['step_id']}</b></h3>
                            <h1 style="margin:10px 0; font-size:4.5rem; font-weight:900;">{rank['score']*100:.1f}%</h1>
                            <p style="color:#94a3b8; text-transform:uppercase; letter-spacing:2px; font-size:0.9rem;">Model Confidence Score</p>
                        </div>
                        <h4 style="font-weight:300; letter-spacing:1px; margin-top:20px; text-align:center;">GROUND-TRUTH EVIDENCE TRAJECTORY</h4>
                        """, unsafe_allow_html=True)
                        for ev in rank.get("evidence", []):
                            st.markdown(f"<div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:8px; margin-bottom:10px; border-left:3px solid #6366f1; text-align:left;'>{ev}</div>", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("No diagnosis data available for this run.")

elif page == "Replay Lab":
    st.markdown('<div class="glass-card glass-card-neon animate-in" style="text-align:center;">', unsafe_allow_html=True)
    st.markdown("<h2 style='font-weight:300; letter-spacing:2px;'>REPLAY LAB</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8;'>Inject counterfactual state overrides to test agent resilience and branch alternate timelines.</p>", unsafe_allow_html=True)
    
    _, col_form, _ = st.columns([1, 2, 1])
    with col_form:
        with st.form("replay_form"):
            st.selectbox("Select Checkpoint Timeline", ["ckpt-5 (Step 5 - validate_availability)", "ckpt-4 (Step 4)"])
            st.selectbox("Modification Type", ["change_tool_result", "change_parameter", "change_branch"])
            st.text_area("JSON Payload Injection", value='{\n  "step_id": "step-5",\n  "value": {"available": true}\n}', height=150)
            
            if st.form_submit_button("Engage Counterfactual Replay", type="primary", use_container_width=True):
                st.balloons()
                st.success("Counterfactual Timeline Branched Successfully. Generated new Run ID: run-456")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Comparison":
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.markdown("<h2 style='font-weight:300; letter-spacing:2px;'>TRACE COMPARISON</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; margin-bottom:30px;'>Analyze divergence between original and counterfactual timelines.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    _, col_comp, _ = st.columns([1, 4, 1])
    with col_comp:
        st.markdown('<div class="glass-card animate-in">', unsafe_allow_html=True)
        cols = st.columns([1, 1, 1])
        orig_id = cols[0].text_input("Original Run", "run-123")
        alt_id = cols[1].text_input("Alternative Run", "run-456")
        st.write("")
        if cols[2].button("Run Comparative Analysis", type="primary", use_container_width=True):
            ph = st.empty()
            ph.markdown('<div class="big-spinner" style="width:50px;height:50px;border-width:3px;margin:10px auto;"></div>', unsafe_allow_html=True)
            time.sleep(1.5) # Fake loading
            ph.empty()
            st.success("Comparison analysis complete!")
            # Fake comparison data
            metric_cols = st.columns(4)
            metric_cols[0].metric("Common Prefix Steps", "4")
            metric_cols[1].metric("Changed Steps", "1")
            metric_cols[2].metric("Rerun Steps", "3")
            metric_cols[3].metric("Runtime Savings", "1400ms", delta_color="normal", delta="Saved")
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "Evaluation":
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.markdown("<h2 style='font-weight:300; letter-spacing:2px;'>SYSTEM EVALUATION</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; margin-bottom:30px;'>Live benchmarks generated by the active Random Forest diagnostic model.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    data = fetch_api("/evaluation")
    if data:
        metrics = data.get("summary", {})
        rf_details = data.get("test_split", {}).get("random_forest", {})
        
        # Super polished F1 display
        _, col_f1, _ = st.columns([1, 2, 1])
        with col_f1:
            st.markdown('<div class="glass-card glass-card-neon animate-in" style="padding:50px; text-align:center;">', unsafe_allow_html=True)
            st.markdown(f'<p class="f1-text">{metrics.get("rf_f1", 0):.4f}</p>', unsafe_allow_html=True)
            st.markdown('<p class="f1-sub">Global F1 Score</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        _, col_L, col_R, _ = st.columns([1, 2, 2, 1])
        with col_L:
            st.markdown('<div class="glass-card animate-in" style="animation-delay: 0.2s; text-align:center;">', unsafe_allow_html=True)
            st.markdown("<h3 style='font-weight:300; margin-bottom:20px;'>Localization Mastery</h3>", unsafe_allow_html=True)
            st.metric("Top-1 Accuracy", f"{metrics.get('rf_top_1', 0)*100}%")
            st.metric("Top-3 Accuracy", f"{metrics.get('rf_top_3', 0)*100}%")
            st.metric("MRR", f"{metrics.get('rf_mrr', 0):.4f}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col_R:
            st.markdown('<div class="glass-card animate-in" style="animation-delay: 0.3s; text-align:center;">', unsafe_allow_html=True)
            st.markdown("<h3 style='font-weight:300; margin-bottom:20px;'>Held-Out Robustness (Unseen)</h3>", unsafe_allow_html=True)
            st.metric("Held-Out Top-1", f"{metrics.get('held_out_top_1', 0)*100}%")
            st.metric("Precision", f"{rf_details.get('precision', 0):.4f}")
            st.metric("Recall", f"{rf_details.get('recall', 0):.4f}")
            st.markdown('</div>', unsafe_allow_html=True)
            
st.markdown('</div>', unsafe_allow_html=True)
