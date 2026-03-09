"""
app.py — AuditAI Streamlit Web App (Real AI Engine)
Run with: streamlit run app.py
"""

import os
import time
from datetime import datetime

import streamlit as st
from audit_engine import VERSION

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title=f"AuditAI v{VERSION} — Marketing Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Version badge in sidebar ──────────────────────────────────
st.sidebar.markdown(f"**AuditAI** `v{VERSION}`")
st.sidebar.caption("Replace project folder to update")

# ── Custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&display=swap');

  html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
  .main { background: #f5f0e8; }
  .block-container { padding-top: 2rem; max-width: 920px; }

  h1, h2, h3 { font-family: 'DM Serif Display', serif !important; color: #0a0a0a !important; }

  .hero-title { font-family: 'DM Serif Display', serif; font-size: 3rem; line-height: 1.1; color: #0a0a0a; }
  .hero-title em { color: #c84b2f; font-style: italic; }
  .hero-sub { font-size: 1rem; color: #7a7060; line-height: 1.6; }
  .eyebrow { font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.18em; text-transform: uppercase; color: #c84b2f; }

  .stTextInput > div > div > input {
    font-family: 'DM Mono', monospace !important;
    border: 2px solid #d4cfc3 !important;
    border-radius: 4px !important;
    padding: 0.75rem 1rem !important;
    background: white !important;
  }
  .stTextInput > div > div > input:focus { border-color: #0a0a0a !important; box-shadow: none !important; }

  .stButton > button {
    background: #c84b2f !important; color: white !important; border: none !important;
    font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
    font-size: 0.9rem !important; letter-spacing: 0.06em !important;
    text-transform: uppercase !important; padding: 0.75rem 2rem !important;
    border-radius: 4px !important; width: 100%;
  }
  .stButton > button:hover { background: #e8623f !important; }

  .metric-card {
    background: #0a0a0a; color: #f5f0e8; padding: 1.5rem;
    border-radius: 6px; text-align: center; margin-bottom: 1rem;
  }
  .metric-label { font-family: 'DM Mono', monospace; font-size: 0.62rem; letter-spacing: 0.18em; text-transform: uppercase; color: #666; margin-bottom: 0.5rem; }
  .metric-grade { font-family: 'DM Serif Display', serif; font-size: 3rem; line-height: 1; }
  .metric-score { font-size: 0.82rem; color: #888; margin-top: 0.25rem; }

  .finding-critical { border-left: 4px solid #c84b2f; background: #fff5f3; padding: 1rem 1.2rem; margin: 0.5rem 0; border-radius: 0 4px 4px 0; }
  .finding-high     { border-left: 4px solid #e8623f; background: #fff8f5; padding: 1rem 1.2rem; margin: 0.5rem 0; border-radius: 0 4px 4px 0; }
  .finding-medium   { border-left: 4px solid #c9a227; background: #fffdf0; padding: 1rem 1.2rem; margin: 0.5rem 0; border-radius: 0 4px 4px 0; }
  .finding-low      { border-left: 4px solid #4a6741; background: #f5fff3; padding: 1rem 1.2rem; margin: 0.5rem 0; border-radius: 0 4px 4px 0; }
  .finding-title  { font-weight: 700; font-size: 0.95rem; color: #0a0a0a; margin-bottom: 0.25rem; }
  .finding-cat    { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: #7a7060; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
  .finding-desc   { font-size: 0.88rem; color: #333; line-height: 1.5; }
  .finding-impact { font-size: 0.82rem; color: #c84b2f; margin-top: 0.4rem; font-style: italic; }

  .task-row { display: flex; align-items: flex-start; gap: 0.75rem; padding: 0.75rem 0; border-bottom: 1px solid #d4cfc3; font-size: 0.88rem; }
  .task-check { color: #c84b2f; font-size: 1.1rem; flex-shrink: 0; }
  .task-text  { flex: 1; color: #0a0a0a; }
  .task-meta  { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: #7a7060; white-space: nowrap; }

  .agent-line { font-family: 'DM Mono', monospace; font-size: 0.82rem; padding: 0.3rem 0; }
  .agent-done    { color: #4a6741; }
  .agent-running { color: #c9a227; }
  .agent-waiting { color: #bbb; }

  .api-label { font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: #7a7060; margin-bottom: 0.3rem; }

  .stDownloadButton > button {
    background: #c84b2f !important; color: white !important; border: none !important;
    font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
    font-size: 1rem !important; padding: 0.9rem 2.5rem !important;
    border-radius: 4px !important; width: 100% !important;
  }

  #MainMenu { visibility: hidden; }
  footer    { visibility: hidden; }
  header    { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Imports ───────────────────────────────────────────────────
from audit_engine    import run_real_audit
from generate_report import generate_report

# ── Grade colors ──────────────────────────────────────────────
GRADE_HEX = {
    "A": "#4a6741", "B+": "#6a9a60", "B": "#7aa2f7", "B-": "#7aa2f7",
    "C+": "#c9a227", "C": "#c9a227", "C-": "#e8623f",
    "D+": "#c84b2f", "D": "#c84b2f", "F": "#8b0000",
}
def grade_color(g): return GRADE_HEX.get(g, "#c84b2f")
def sev_emoji(s):   return {"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢"}.get(s,"⚪")

# ── Session state ─────────────────────────────────────────────
defaults = {
    "audit_done": False, "audit_data": None,
    "pdf_bytes": None,   "pdf_filename": None,
    "api_key": "",       "error_msg": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════
st.markdown('<p class="eyebrow">AI Marketing Intelligence Platform</p>', unsafe_allow_html=True)
st.markdown('<h1 class="hero-title">Replace the <em>$10,000</em> Agency.</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-sub">Paste any URL. Five AI agents audit the site in real time — delivering competitive analysis, SEO teardowns, and a client-ready PDF report.</p>', unsafe_allow_html=True)
st.markdown("---")


# ════════════════════════════════════════════════════════════════
# INPUT FORM
# ════════════════════════════════════════════════════════════════
if not st.session_state.audit_done:

    st.markdown('<p class="api-label">Anthropic API Key</p>', unsafe_allow_html=True)
    api_key_input = st.text_input(
        "api_key_field",
        value=st.session_state.api_key,
        placeholder="sk-ant-api03-...",
        type="password",
        label_visibility="collapsed",
    )
    st.caption("Your key is never stored. Get one free at console.anthropic.com")

    st.markdown("<br/>", unsafe_allow_html=True)
    st.markdown('<p class="api-label">Website to Audit</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        domain_input = st.text_input(
            "domain_field",
            placeholder="yourclient.com",
            label_visibility="collapsed",
        )
    with col2:
        run_button = st.button("Run Audit →")

    st.caption("Works on any publicly accessible website")

    if st.session_state.error_msg:
        st.error(st.session_state.error_msg)
        st.session_state.error_msg = ""

    # ── Run ────────────────────────────────────────────────────
    if run_button:
        if not api_key_input.strip():
            st.warning("Please enter your Anthropic API key above.")
        elif not domain_input.strip():
            st.warning("Please enter a website URL.")
        else:
            st.session_state.api_key = api_key_input.strip()
            domain = domain_input.strip()

            st.markdown("---")
            st.markdown(f"### Auditing `{domain}`")

            progress_bar  = st.progress(0)
            agent_display = st.empty()
            status_text   = st.empty()

            agents = [
                ("market-content",  "Crawling brand voice & messaging"),
                ("market-convert",  "Scanning CTA placement & funnel"),
                ("market-compete",  "Mapping competitive landscape"),
                ("market-tech",     "Auditing technical SEO signals"),
                ("market-strategy", "Synthesizing findings via Claude API"),
            ]

            completed = []

            def render_agents():
                lines = ""
                for i, (agent, msg) in enumerate(agents):
                    if i < len(completed):
                        lines += f'<div class="agent-line agent-done">✓ [{agent}]&nbsp;&nbsp;{msg}</div>'
                    elif i == len(completed):
                        lines += f'<div class="agent-line agent-running">⟳ [{agent}]&nbsp;&nbsp;{msg}...</div>'
                    else:
                        lines += f'<div class="agent-line agent-waiting">&nbsp;&nbsp;[{agent}]&nbsp;&nbsp;waiting...</div>'
                agent_display.markdown(lines, unsafe_allow_html=True)

            render_agents()

            def progress_callback(msg):
                status_text.caption(msg)
                if len(completed) < len(agents):
                    completed.append(True)
                    progress_bar.progress(min(10 + len(completed) * 16, 88))
                    render_agents()

            try:
                audit_data = run_real_audit(domain, st.session_state.api_key, progress_callback)

                # Mark all done
                while len(completed) < len(agents):
                    completed.append(True)
                render_agents()
                progress_bar.progress(95)
                status_text.caption("Generating PDF report...")

                # PDF into memory (no temp files left behind)
                import tempfile
                with tempfile.TemporaryDirectory() as tmp:
                    pdf_path = generate_report(audit_data, tmp)
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()

                clean_domain = (
                    domain.replace("https://","").replace("http://","")
                          .replace("www.","").rstrip("/").replace(".","-")
                )
                date_str     = datetime.now().strftime("%Y%m%d")
                pdf_filename = f"{clean_domain}-audit-{date_str}.pdf"

                progress_bar.progress(100)
                status_text.caption("✓ Done!")

                st.session_state.audit_done   = True
                st.session_state.audit_data   = audit_data
                st.session_state.pdf_bytes    = pdf_bytes
                st.session_state.pdf_filename = pdf_filename
                st.rerun()

            except Exception as e:
                err = str(e)
                progress_bar.empty()
                agent_display.empty()
                status_text.empty()
                if "401" in err or "authentication" in err.lower():
                    st.session_state.error_msg = "❌ Invalid API key. Check your key at console.anthropic.com"
                elif "quota" in err.lower() or "credit" in err.lower():
                    st.session_state.error_msg = "❌ API key has no credits. Add credits at console.anthropic.com"
                elif "timeout" in err.lower() or "connection" in err.lower():
                    st.session_state.error_msg = f"❌ Could not reach {domain} — check the URL and try again."
                else:
                    st.session_state.error_msg = f"❌ Audit failed: {err[:300]}"
                st.rerun()


# ════════════════════════════════════════════════════════════════
# RESULTS
# ════════════════════════════════════════════════════════════════
if st.session_state.audit_done and st.session_state.audit_data:
    data = st.session_state.audit_data

    st.success(f"✓ Audit complete — **{data.get('business_name', data['domain'])}** · {data['audit_date']}")

    # ── Score cards ───────────────────────────────────────────
    st.markdown("### Performance Scores")
    score_cols = st.columns(5)
    score_cols[0].markdown(f"""
    <div class="metric-card">
      <div class="metric-label">Overall</div>
      <div class="metric-grade" style="color:{grade_color(data['overall_grade'])}">{data['overall_grade']}</div>
      <div class="metric-score">{data['overall_score']}/100</div>
    </div>""", unsafe_allow_html=True)

    for i, (label, vals) in enumerate(data["scores"].items()):
        score_cols[i+1].markdown(f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-grade" style="color:{grade_color(vals['grade'])}">{vals['grade']}</div>
          <div class="metric-score">{vals['score']}/100</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Findings + Action Plan ────────────────────────────────
    left, right = st.columns([1.1, 0.9])

    with left:
        st.markdown("### Critical Findings")
        for f in data["critical_findings"]:
            sev = f["severity"]
            st.markdown(f"""
            <div class="finding-{sev}">
              <div class="finding-cat">{sev_emoji(sev)} {sev.upper()} · {f['category']}</div>
              <div class="finding-title">{f['title']}</div>
              <div class="finding-desc">{f['description']}</div>
              <div class="finding-impact">→ {f['impact']}</div>
            </div>""", unsafe_allow_html=True)

    with right:
        st.markdown("### Action Plan")
        with st.expander("⚡ Quick Wins — Week 1–4", expanded=True):
            for t in data["action_plan"]["quick_wins"]:
                st.markdown(f"""
                <div class="task-row">
                  <span class="task-check">☐</span>
                  <span class="task-text">{t['task']}</span>
                  <span class="task-meta">{t['time']}</span>
                </div>""", unsafe_allow_html=True)

        with st.expander("📅 Medium Term — 1–3 Months"):
            for t in data["action_plan"]["medium_term"]:
                st.markdown(f"""
                <div class="task-row">
                  <span class="task-check">☐</span>
                  <span class="task-text">{t['task']}</span>
                  <span class="task-meta">{t['time']}</span>
                </div>""", unsafe_allow_html=True)

        with st.expander("🎯 Strategic — 3–6 Months"):
            for t in data["action_plan"]["strategic"]:
                st.markdown(f"""
                <div class="task-row">
                  <span class="task-check">☐</span>
                  <span class="task-text">{t['task']}</span>
                  <span class="task-meta">{t['time']}</span>
                </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Executive Summary ─────────────────────────────────────
    st.markdown("### Executive Summary")
    st.info(data["executive_summary"])

    st.markdown("---")

    # ── Competitors ───────────────────────────────────────────
    st.markdown("### Competitive Landscape")
    st.caption("✓ All competitor URLs verified as live websites")
    for col, h in zip(st.columns([1, 2, 2, 1, 1]), ["Tier", "Business", "Website", "Reviews", "Threat"]):
        col.markdown(f"**{h}**")
    threat_colors = {"HIGH":"#c84b2f","MED":"#c9a227","LOW":"#4a6741","N/A":"#7a7060"}
    for c in data["competitors"]:
        cols = st.columns([1, 2, 2, 1, 1])
        tier = c.get("tier", "Direct")
        tier_color = {"Direct":"#c84b2f","Indirect":"#c9a227","Aspirational":"#4a6741"}.get(tier, "#333")
        cols[0].markdown(f'<span style="color:{tier_color};font-weight:600;font-size:0.88rem">{tier}</span>', unsafe_allow_html=True)
        cols[1].markdown(f"**{c['name']}**")
        url = c.get("url", "")
        display_url = url.replace("https://","").replace("http://","").replace("www.","").rstrip("/")
        cols[2].markdown(f'<a href="{url}" target="_blank" style="color:#c84b2f;font-size:0.85rem">{display_url}</a>', unsafe_allow_html=True)
        cols[3].write(str(c.get("reviews","—")))
        tc = threat_colors.get(c.get("threat",""),"#333")
        cols[4].markdown(f'<span style="color:{tc};font-weight:700">{c.get("threat","—")}</span>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Download ──────────────────────────────────────────────
    st.markdown("### Download Client Report")
    st.download_button(
        label="⬇  Download PDF Report",
        data=st.session_state.pdf_bytes,
        file_name=st.session_state.pdf_filename,
        mime="application/pdf",
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    if st.button("← Audit Another Website"):
        for k in ["audit_done","audit_data","pdf_bytes","pdf_filename","error_msg"]:
            st.session_state[k] = None if k not in ("audit_done",) else False
        st.session_state.error_msg = ""
        st.rerun()
