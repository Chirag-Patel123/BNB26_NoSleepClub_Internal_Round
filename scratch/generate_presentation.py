import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def build_presentation(output_path="BlackBox_Agent_Observability.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9 widescreen
    prs.slide_height = Inches(7.5)

    # Color Palette
    BG_DARK = RGBColor(12, 14, 20)       # #0c0e14 Deep Navy / Dark
    CARD_BG = RGBColor(22, 27, 38)       # #161b26 Dark Slate Box
    CARD_BORDER = RGBColor(40, 48, 68)   # Subtle Border
    ACCENT_ORANGE = RGBColor(255, 87, 34) # #ff5722 Brand Accent
    ACCENT_GREEN = RGBColor(46, 213, 115) # #2ed573 Success / Status
    TEXT_LIGHT = RGBColor(248, 250, 252) # #f8fafc White/Silver
    TEXT_MUTED = RGBColor(156, 163, 175) # #9ca3af Cool Grey
    ACCENT_BLUE = RGBColor(56, 189, 248)  # #38bdf8 Cyan Blue

    blank_layout = prs.slide_layouts[6]

    def set_slide_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_DARK
        bg.line.fill.background()
        return bg

    def add_header(slide, title, category="BLACK BOX // AI AGENT OBSERVABILITY"):
        # Category tag
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11), Inches(0.4))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_ORANGE

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.5), Inches(0.8))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        p_title.text = title
        p_title.font.size = Pt(26)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_LIGHT

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)
        return card

    # =========================================================================
    # SLIDE 1: TITLE SLIDE
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1)

    # Accent decorative bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(1.8), Inches(0.12), Inches(3.8))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT_ORANGE
    bar.line.fill.background()

    tb1 = s1.shapes.add_textbox(Inches(1.5), Inches(1.8), Inches(10.5), Inches(3.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "BLACK BOX // AUTONOMOUS AI AGENT RECORDER"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_GREEN

    p1 = tf1.add_paragraph()
    p1.text = "See the Decision.\nUnderstand the Failure."
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_LIGHT

    p2 = tf1.add_paragraph()
    p2.text = "Trace-Grounded Causal Fault Localization & Checkpointed Counterfactual Replay"
    p2.font.size = Pt(18)
    p2.font.color.rgb = ACCENT_BLUE

    # Team Card at bottom
    add_card(s1, Inches(1.5), Inches(5.8), Inches(10.3), Inches(0.95))
    tb_team = s1.shapes.add_textbox(Inches(1.7), Inches(5.9), Inches(10), Inches(0.75))
    tf_team = tb_team.text_frame
    p_t1 = tf_team.paragraphs[0]
    p_t1.text = "Team: NoSleepClub  |  Chirag Patel  |  Production Deployment & Benchmark"
    p_t1.font.size = Pt(13)
    p_t1.font.bold = True
    p_t1.font.color.rgb = TEXT_LIGHT

    p_t2 = tf_team.add_paragraph()
    p_t2.text = "Tech Stack: Python FastAPI, Random Forest Causal Diagnosis, Directed Acyclic Graph (DAG), React + Vite"
    p_t2.font.size = Pt(11)
    p_t2.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 2: THE PROBLEM - SILENT AGENT FAILURES
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2)
    add_header(s2, "The Critical Problem: Silent Fault Propagation in AI Agents")

    cards_data_s2 = [
        ("1. Multi-Step Execution Blindspots", 
         "Autonomous LLM agents execute 5 to 15 sequential steps across LLM reasoning, schema extraction, tool calls, and API transactions.",
         "Where did the error actually happen?", ACCENT_ORANGE),
        ("2. Silent Fault Propagation", 
         "A subtle mistake at Step 3 (e.g., querying Bengaluru instead of Delhi, or a negative invoice fee) looks valid to downstream steps.",
         "Failure surfaces 5 steps later at Step 8.", ACCENT_BLUE),
        ("3. Expensive 'Re-run From Scratch'", 
         "Standard agent frameworks re-execute the entire pipeline from Step 1, wasting 60%+ tokens and latency on unchanged steps.",
         "Unnecessary compute waste & latency.", ACCENT_GREEN)
    ]

    for i, (title, desc, highlight, col) in enumerate(cards_data_s2):
        left = Inches(0.8 + i * 4.0)
        add_card(s2, left, Inches(1.8), Inches(3.7), Inches(4.8))
        tb = s2.shapes.add_textbox(left + Inches(0.2), Inches(2.0), Inches(3.3), Inches(4.3))
        tf = tb.text_frame
        tf.word_wrap = True

        pt = tf.paragraphs[0]
        pt.text = title
        pt.font.size = Pt(18)
        pt.font.bold = True
        pt.font.color.rgb = col

        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(14)
        pd.font.color.rgb = TEXT_LIGHT

        ph = tf.add_paragraph()
        ph.text = f"\nTakeaway:\n• {highlight}"
        ph.font.size = Pt(13)
        ph.font.bold = True
        ph.font.color.rgb = ACCENT_ORANGE

    # =========================================================================
    # SLIDE 3: THE ANALOGY - AIRPLANE FLIGHT RECORDER
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3)
    add_header(s3, "The Analogy: A Black Box Flight Recorder for AI Agents")

    add_card(s3, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))
    tb_left = s3.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.4))
    tf_l = tb_left.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "Aviation Flight Recorder"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = ACCENT_ORANGE

    points_l = [
        "Records every sensor reading, pilot command, and telemetry signal in real-time.",
        "When an incident happens, investigators don't guess what went wrong.",
        "They rewind the black box to discover the exact root event preceding the crash."
    ]
    for pt in points_l:
        p = tf_l.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(14)
        p.font.color.rgb = TEXT_LIGHT

    add_card(s3, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8))
    tb_right = s3.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.4))
    tf_r = tb_right.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "Black Box for Autonomous Agents"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    points_r = [
        "Records every prompt, tool input/output, latency, token count, and memory checkpoint.",
        "Learned ML model analyzes step mutations and ranks the true causal culprit step.",
        "Checkpointed replay allows human-in-the-loop branching with one counterfactual fix — saving 60% compute."
    ]
    for pt in points_r:
        p = tf_r.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(14)
        p.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 4: SYSTEM ARCHITECTURE & PIPELINE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4)
    add_header(s4, "System Architecture: End-to-End Diagnostic Pipeline")

    arch_steps = [
        ("Step 1: Instrument & Trace", "Captures prompts, tool calls, JSON payloads, and dependencies as a Directed Acyclic Graph (DAG)."),
        ("Step 2: State Checkpointing", "Snapshots immutable intermediate state before and after each tool call with zero overhead."),
        ("Step 3: ML Causal Diagnosis", "Random Forest ranking model evaluates input/output drift and ranks suspect steps with calibrated suspicion."),
        ("Step 4: Counterfactual Replay", "Branches execution from step k with modified parameter; reuses cached prefix 1..k-1 and diffs outcomes.")
    ]

    for i, (title, desc) in enumerate(arch_steps):
        top_pos = Inches(1.8 + i * 1.25)
        add_card(s4, Inches(0.8), top_pos, Inches(11.7), Inches(1.05))
        tb = s4.shapes.add_textbox(Inches(1.1), top_pos + Inches(0.12), Inches(11.1), Inches(0.8))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(16)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_ORANGE

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(13)
        p2.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 5: THE ML DIAGNOSIS ENGINE
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5)
    add_header(s5, "Causal Fault Localization: Learned ML Model vs Heuristics")

    # Left Card: ML Features
    add_card(s5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.8))
    tb_f = s5.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.4))
    tf_f = tb_f.text_frame
    tf_f.word_wrap = True
    p = tf_f.paragraphs[0]
    p.text = "Extracted Feature Representations"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_BLUE

    feats = [
        "Input / Output Invariant Verification: Checks parameter integrity (e.g. requested BOM->DEL vs searched BOM->BLR).",
        "Semantic & Schema Drift: Identifies when intermediate tool responses drift from user objective.",
        "Error Surface Distance: Calculates step distance between where the bug occurred and where failure was observed.",
        "Latency & Token Anomaly Detection: Flags suspicious spike in retries or latency."
    ]
    for f in feats:
        p = tf_f.add_paragraph()
        p.text = f"• {f}"
        p.font.size = Pt(13)
        p.font.color.rgb = TEXT_LIGHT

    # Right Card: Performance Metrics
    add_card(s5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8))
    tb_m = s5.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.4))
    tf_m = tb_m.text_frame
    tf_m.word_wrap = True
    p = tf_m.paragraphs[0]
    p.text = "Diagnostic Precision & Calibration"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    metrics = [
        "Top-1 Accuracy: 95.0% - 100% (Correct root culprit identified on rank 1).",
        "Top-3 Localization: 100.0% (True causal step guaranteed in top 3 suspects).",
        "Mean Reciprocal Rank (MRR): 0.985 (Near perfect ranking precision).",
        "Held-Out Generalization: 91.7%+ on unseen failure distributions never presented during training."
    ]
    for m in metrics:
        p = tf_m.add_paragraph()
        p.text = f"• {m}"
        p.font.size = Pt(13)
        p.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 6: CHECKPOINTED REPLAY & PREFIX CACHING
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6)
    add_header(s6, "Counterfactual Replay: Prefix Caching & Differential Verification")

    add_card(s6, Inches(0.8), Inches(1.8), Inches(11.7), Inches(2.1))
    tb_rep = s6.shapes.add_textbox(Inches(1.0), Inches(1.9), Inches(11.3), Inches(1.9))
    tf_rep = tb_rep.text_frame
    tf_rep.word_wrap = True

    p = tf_rep.paragraphs[0]
    p.text = "How Checkpointed Replay Works:"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = ACCENT_ORANGE

    p = tf_rep.add_paragraph()
    p.text = "Instead of re-executing steps 1 to 8, Black Box loads the exact snapshot from Checkpoint k (the culprit step). Steps 1..k-1 are marked as CACHED / REUSED. Only Step k and downstream steps re-compute with the patched value."
    p.font.size = Pt(13.5)
    p.font.color.rgb = TEXT_LIGHT

    # 3 Stat Cards
    stat_boxes = [
        ("62.5% Token Reduction", "Reuses pre-computed LLM prompt tokens and embeddings from earlier steps.", ACCENT_GREEN),
        ("58.0% Latency Economy", "Eliminates network latency of repeated search and tool calls.", ACCENT_BLUE),
        ("Side-by-Side Diff", "Compare view shows exact divergence point and validates recovery.", ACCENT_ORANGE),
    ]

    for i, (title, desc, col) in enumerate(stat_boxes):
        left = Inches(0.8 + i * 4.0)
        add_card(s6, left, Inches(4.2), Inches(3.7), Inches(2.5))
        tb = s6.shapes.add_textbox(left + Inches(0.2), Inches(4.4), Inches(3.3), Inches(2.1))
        tf = tb.text_frame
        tf.word_wrap = True

        pt = tf.paragraphs[0]
        pt.text = title
        pt.font.size = Pt(16)
        pt.font.bold = True
        pt.font.color.rgb = col

        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(13)
        pd.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 7: HETEROGENEOUS AGENT DOMAINS TESTED
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7)
    add_header(s7, "Multi-Domain Evaluation: Proving Generalization Across Industries")

    domains = [
        ("1. Flight Booking Agent", "Wrong Destination Hallucination", "Step 3 queried BLR instead of DEL. Replay patched search query."),
        ("2. Cloud DevOps Provisioning", "Target Region Mismatch", "Step 3 routed US-EAST to EU-CENTRAL. Blocked by pre-execution invariant."),
        ("3. FinTech Settlement", "Negative Fee Calculation Error", "Step 6 computed net_total -$1,240 due to inverted sign fee deduction."),
        ("4. Lakehouse ETL Pipeline", "Stale Search / Schema Drift", "Step 3 fetched stale v2.1 cached metadata, failing on missing live columns."),
        ("5. Customer Escrow Refund", "Policy Filter Relaxation", "Step 4 relaxed tier approval threshold ($500 vs $250 limit)."),
        ("6. Zero-Trust IAM Security", "Privilege Over-Granting", "Verified multi-factor hardware key and enforced least-privilege token duration.")
    ]

    for i, (dom, fail_type, res) in enumerate(domains):
        row = i // 3
        col = i % 3
        left = Inches(0.8 + col * 4.0)
        top = Inches(1.8 + row * 2.5)

        add_card(s7, left, top, Inches(3.7), Inches(2.2))
        tb = s7.shapes.add_textbox(left + Inches(0.15), top + Inches(0.15), Inches(3.4), Inches(1.9))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = dom
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_ORANGE

        p2 = tf.add_paragraph()
        p2.text = f"Failure: {fail_type}"
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = ACCENT_BLUE

        p3 = tf.add_paragraph()
        p3.text = res
        p3.font.size = Pt(11.5)
        p3.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 8: EMPIRICAL BENCHMARK & EVALUATION RESULTS
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8)
    add_header(s8, "Empirical Benchmark: Live Evaluation Dashboard")

    metrics_s8 = [
        ("0.9428", "F1 Score", "Step-level causal classification", ACCENT_GREEN),
        ("100.0%", "Top-1 Accuracy", "Root culprit ranked rank #1", ACCENT_ORANGE),
        ("100.0%", "Top-3 Coverage", "Culprit guaranteed in top 3", ACCENT_BLUE),
        ("0.985", "Mean Reciprocal Rank", "Strongest ranking certainty", ACCENT_GREEN),
        ("91.7%", "Held-Out Generalization", "Accuracy on unseen failure types", ACCENT_ORANGE),
        ("100.0%", "Replay Fix Rate", "Counterfactual recovery success", ACCENT_BLUE),
    ]

    for i, (val, title, note, col) in enumerate(metrics_s8):
        row = i // 3
        col_idx = i % 3
        left = Inches(0.8 + col_idx * 4.0)
        top = Inches(1.8 + row * 2.5)

        add_card(s8, left, top, Inches(3.7), Inches(2.2))
        tb = s8.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), Inches(3.3), Inches(1.8))
        tf = tb.text_frame
        tf.word_wrap = True

        pv = tf.paragraphs[0]
        pv.text = val
        pv.font.size = Pt(32)
        pv.font.bold = True
        pv.font.color.rgb = col

        pt = tf.add_paragraph()
        pt.text = title
        pt.font.size = Pt(16)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_LIGHT

        pn = tf.add_paragraph()
        pn.text = note
        pn.font.size = Pt(12)
        pn.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 9: PLATFORM CAPABILITIES & DEMO WALKTHROUGH
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s9)
    add_header(s9, "Interactive Platform: What You Can Do in Black Box")

    platform_features = [
        ("Overview & Live DAG", "Interactive directed graph visualization with real-time token/latency stats, active health indicators, and dynamic Top-1 failure ratios."),
        ("Investigate Tab", "Trace inspection with step-level input/output diffs, invariant guardrail violations, and calibrated suspicion ranking percentages."),
        ("Checkpointed Replay", "Pick any checkpoint, apply a counterfactual fix, and branch without re-running earlier cached steps."),
        ("Differential Compare", "Side-by-side execution diff highlights common prefix, divergence point, and validates recovery."),
        ("Arbitrary Trace Import", "Paste JSON traces from LangSmith, Langfuse, Arize Phoenix, or OpenTelemetry spans for instant causal diagnosis.")
    ]

    for i, (title, desc) in enumerate(platform_features):
        top_pos = Inches(1.8 + i * 1.0)
        add_card(s9, Inches(0.8), top_pos, Inches(11.7), Inches(0.85))
        tb = s9.shapes.add_textbox(Inches(1.0), top_pos + Inches(0.08), Inches(11.3), Inches(0.7))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = ACCENT_ORANGE

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(12)
        p2.font.color.rgb = TEXT_LIGHT

    # =========================================================================
    # SLIDE 10: CONCLUSION & IMPACT
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s10)
    add_header(s10, "Summary: Why Black Box Changes Autonomous AI Engineering")

    add_card(s10, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8))
    tb_c = s10.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(10.9), Inches(4.4))
    tf_c = tb_c.text_frame
    tf_c.word_wrap = True

    takeaways = [
        ("Root Cause Localization in Seconds", "Eliminates tedious manual log reading. The learned ML model flags the true originating culprit step with 95%+ precision."),
        ("Enterprise Safety Before Irreversible Actions", "Detects invariant violations before destructive API calls (money transfers, cloud deletions, ticket bookings)."),
        ("60%+ Cost & Latency Savings with Prefix Caching", "Counterfactual debugging only re-computes what changed, making agent development fast and affordable."),
        ("Universal Compatibility", "Works with LangChain, LangGraph, AutoGen, CrewAI, LangSmith, or raw custom agent loops via standard JSON trace ingestion."),
        ("Production-Ready", "Fully tested end-to-end (123 automated pytest suite passing, live responsive React web UI, deployed on Railway & Vercel).")
    ]

    for i, (h, desc) in enumerate(takeaways):
        p = tf_c.paragraphs[0] if i == 0 else tf_c.add_paragraph()
        p.text = f"✓ {h}"
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = ACCENT_GREEN

        p_desc = tf_c.add_paragraph()
        p_desc.text = f"   {desc}\n"
        p_desc.font.size = Pt(13)
        p_desc.font.color.rgb = TEXT_LIGHT

    prs.save(output_path)
    print(f"Presentation saved successfully to: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    build_presentation("BlackBox_AI_Agent_Observability_Presentation.pptx")
