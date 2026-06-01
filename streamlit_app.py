"""
HerSignal Streamlit shareable demo.

Uses the same logic modules as the Flask app (scoring, results, FAQ, charts).
Does not start or modify app.py. Run with:

    streamlit run streamlit_app.py
"""

from __future__ import annotations

import html
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

MAX_CHAT_MESSAGE_LENGTH = 500
CATEGORY_LABELS = {
    "hormonal": "Hormonal patterns",
    "metabolic": "Metabolic patterns",
    "inflammatory": "Inflammatory patterns",
}
NAV_PAGES = ["Home", "Symptom checker", "Results"]

JOURNEY_STEPS = [
    ("Home", "Chat", "Ask PCOS questions"),
    ("Symptom checker", "Checker", "Answer symptom prompts"),
    ("Results", "Results", "See your pattern summary"),
]

HEART_SVG = """
<svg class="hs-hero-logo" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="hsHeart" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#e895c0"/>
      <stop offset="50%" style="stop-color:#b94f87"/>
      <stop offset="100%" style="stop-color:#8a3d67"/>
    </linearGradient>
  </defs>
  <path fill="url(#hsHeart)" d="M60 98c-2-2-28-16-38-36-8-16-2-34 18-34 10 0 16 6 20 12 4-6 10-12 20-12 20 0 26 18 18 34-10 20-36 34-38 36z"/>
</svg>
"""


def load_theme_css():
    css_path = ROOT / "static" / "streamlit_custom.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def inject_theme():
    st.markdown(f"<style>{load_theme_css()}</style>", unsafe_allow_html=True)


def esc(text):
    return html.escape(str(text or ""))


def render_html(fragment: str) -> None:
    """
    Render HTML without Streamlit markdown splitting on blank lines inside tags.
    """
    compact = " ".join(fragment.split())
    if hasattr(st, "html"):
        st.html(compact)
    else:
        st.markdown(compact, unsafe_allow_html=True)


@contextmanager
def hs_section():
    """Card-like section; avoids raw </div> leaking into the page."""
    try:
        with st.container(border=True):
            yield
    except TypeError:
        with st.container():
            yield


def render_hero(title: str, subtitle: str):
    logo_path = ROOT / "static" / "images" / "heart_logo.png"
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if logo_path.exists():
            st.image(str(logo_path), width=110)
        else:
            st.markdown(
                f'<div style="text-align:center">{HEART_SVG}</div>',
                unsafe_allow_html=True,
            )
    render_html(
        f'<div class="hs-hero">'
        f'<p class="hs-brand-tag">HerSignal insight</p>'
        f"<h1>{esc(title)}</h1>"
        f'<p class="hs-hero-sub">{esc(subtitle)}</p>'
        f"</div>"
    )


def render_journey(active_page: str):
    steps_html = []
    for num, (page_name, label, desc) in enumerate(JOURNEY_STEPS, start=1):
        active = " hs-journey-step--active" if page_name == active_page else ""
        steps_html.append(
            f'<div class="hs-journey-step{active}">'
            f'<span class="hs-journey-num">{num}</span>'
            f'<span class="hs-journey-label">{esc(label)}</span>'
            f'<span class="hs-journey-desc">{esc(desc)}</span>'
            f"</div>"
        )
    render_html(f'<nav class="hs-journey" aria-label="Your path">{"".join(steps_html)}</nav>')


def render_feature_cards():
    cards = [
        (
            "Understand symptom patterns",
            "Map your answers into hormonal, metabolic, and inflammatory educational scores.",
        ),
        (
            "Ask PCOS questions",
            "Calm, structured responses from HerSignal's FAQ knowledge base.",
        ),
        (
            "Saved insights timeline",
            "Compare checks over time when you use the full HerSignal app with an account.",
        ),
    ]
    inner = "".join(
        f'<article class="hs-feature-card"><h3>{esc(t)}</h3><p>{esc(d)}</p></article>'
        for t, d in cards
    )
    render_html(f'<div class="hs-feature-grid">{inner}</div>')


def render_score_cards(scores: dict):
    if not scores:
        return
    top_key = max(scores, key=scores.get)
    parts = []
    labels = {"hormonal": "Hormonal", "metabolic": "Metabolic", "inflammatory": "Inflammatory"}
    for key in ("hormonal", "metabolic", "inflammatory"):
        top = " hs-score-card--top" if key == top_key and scores.get(key, 0) > 0 else ""
        parts.append(
            f'<div class="hs-score-card{top}">'
            f"<h4>{labels[key]}</h4>"
            f'<div class="hs-score-value">{scores.get(key, 0)}</div>'
            f"</div>"
        )
    render_html(f'<div class="hs-score-row">{"".join(parts)}</div>')


def render_meaning_block(result_data: dict):
    paragraphs = result_data.get("why_hersignal_paragraphs") or []
    if not paragraphs and result_data.get("why_hersignal_presented_response"):
        paragraphs = [result_data["why_hersignal_presented_response"]]
    paras = "".join(f"<p>{esc(p)}</p>" for p in paragraphs)
    foot = esc(result_data.get("general_disclaimer", ""))
    render_html(
        f'<section class="hs-meaning">'
        f'<p class="hs-brand-tag">HerSignal insight</p>'
        f"<h3>What this may mean</h3>"
        f"{paras}"
        f'<p class="hs-meaning-foot">{foot}</p>'
        f"</section>"
    )


def render_bot_answer(text: str):
    render_html(
        f'<p class="hs-chat-label">HerSignal says</p>'
        f'<div class="hs-bot-bubble">{esc(text)}</div>'
    )


def disclaimer():
    render_html(
        '<p class="hs-disclaimer" role="note">'
        "<strong>Educational only:</strong> HerSignal shares general PCOS education and is not medical advice, "
        "a diagnosis, or a substitute for care from a qualified clinician."
        "</p>"
    )


def init_session_state():
    defaults = {
        "user_name": "",
        "scores": None,
        "result_data": None,
        "chart_path": None,
        "faq_warmed": False,
        "last_faq_answer": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource(show_spinner=False)
def warmup_faq():
    from chatbot.matcher import warmup_faq_matcher

    warmup_faq_matcher()
    return True


def page_home():
    render_hero(
        "HerSignal",
        "Explore PCOS questions and symptom patterns with clear, structured educational support.",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Start symptom checker", type="primary", use_container_width=True):
            st.session_state.nav_page = "Symptom checker"
            st.rerun()
    with col_b:
        if st.button("View latest results", use_container_width=True):
            st.session_state.nav_page = "Results"
            st.rerun()

    with hs_section():
        st.markdown("### What HerSignal helps with")
        render_feature_cards()

    with hs_section():
        st.markdown("### Ask HerSignal")
        greeting = st.session_state.user_name or "there"
        st.caption(f"Hi {greeting}. Ask about PCOS symptoms, patterns, or everyday questions.")

        name = st.text_input(
            "Your name (optional)",
            value=st.session_state.user_name,
            placeholder="For a friendlier greeting",
            label_visibility="collapsed",
        )
        if name != st.session_state.user_name:
            st.session_state.user_name = name.strip()

        starter = st.selectbox(
            "Starter questions",
            [
                "",
                "What is PCOS?",
                "Why are my periods irregular?",
                "What helps with insulin resistance?",
                "What lifestyle changes support PCOS?",
            ],
            label_visibility="collapsed",
        )

        question = st.text_area(
            "Your question",
            value=starter or "",
            max_chars=MAX_CHAT_MESSAGE_LENGTH,
            height=120,
            placeholder="For example: Can PCOS affect fertility?",
            label_visibility="collapsed",
        )

        if st.button("Ask HerSignal", type="primary", use_container_width=True):
            q = (question or "").strip()
            if not q:
                st.warning("Please enter a question first.")
            elif len(q) > MAX_CHAT_MESSAGE_LENGTH:
                st.warning(f"Please keep your question under {MAX_CHAT_MESSAGE_LENGTH} characters.")
            else:
                with st.spinner("HerSignal is thinking…"):
                    if not st.session_state.faq_warmed:
                        warmup_faq()
                        st.session_state.faq_warmed = True
                    from chatbot.responses import get_faq_response

                    st.session_state.last_faq_answer = get_faq_response(q)

        if st.session_state.last_faq_answer:
            render_bot_answer(st.session_state.last_faq_answer)


def page_checker():
    from logic.scoring_engine import load_symptom_questions, normalise_response, calculate_category_scores
    from logic.result_generator import generate_result_data
    from dashboard.chart_builder import build_symptom_chart

    with hs_section():
        st.markdown("### Understand your pattern")
        st.caption("Answer with **yes**, **no**, or **maybe**. Questions are grouped by category.")

        questions = load_symptom_questions()
        if not questions:
            st.error("Symptom questions could not be loaded.")
            return

        responses = {}
        with st.form("symptom_form", clear_on_submit=False):
            idx = 0
            for category in ("hormonal", "metabolic", "inflammatory"):
                group = [q for q in questions if q.get("category") == category]
                if not group:
                    continue
                st.markdown(f"**{CATEGORY_LABELS.get(category, category.title())}**")
                for item in group:
                    idx += 1
                    key = item["id"]
                    prior = st.session_state.get(f"sym_{key}", "maybe")
                    responses[key] = st.radio(
                        f"{idx}. {item['question']}",
                        options=["yes", "no", "maybe"],
                        index=["yes", "no", "maybe"].index(prior)
                        if prior in ("yes", "no", "maybe")
                        else 2,
                        horizontal=True,
                        key=f"sym_{key}",
                    )
                st.divider()

            submitted = st.form_submit_button("See my results", type="primary", use_container_width=True)

    if submitted:
        normalised = {}
        for item in questions:
            sid = item["id"]
            raw = responses.get(sid) or st.session_state.get(f"sym_{sid}", "")
            norm = normalise_response(raw)
            if norm not in {"yes", "no", "maybe"}:
                st.error("Please answer every question with yes, no, or maybe.")
                return
            normalised[sid] = norm

        scores = calculate_category_scores(normalised)
        result_data = generate_result_data(scores, normalised)
        chart_path = None
        try:
            chart_path = build_symptom_chart(scores)
        except Exception:
            chart_path = None

        st.session_state.scores = scores
        st.session_state.result_data = result_data
        st.session_state.chart_path = chart_path
        st.session_state.nav_page = "Results"
        st.rerun()


def page_results():
    scores = st.session_state.scores
    result_data = st.session_state.result_data

    if not scores or not result_data:
        with hs_section():
            st.info("Complete the symptom checker first to see your pattern summary.")
            if st.button("Go to symptom checker", type="primary"):
                st.session_state.nav_page = "Symptom checker"
                st.rerun()
        return

    with hs_section():
        st.markdown(f"### {result_data.get('page_title', 'Your symptom pattern')}")
        st.caption(result_data.get("page_intro", ""))
        render_score_cards(scores)

        chart_path = st.session_state.chart_path
        if chart_path:
            full = ROOT / "static" / chart_path
            if full.exists():
                st.markdown("**Pattern chart**")
                st.image(str(full), use_container_width=True)
                st.caption("Educational scores only. Not a clinical measurement.")

        render_meaning_block(result_data)

    st.markdown("#### More detail")

    with st.expander(
        f"Contributing symptoms · {result_data.get('contributing_preview', '')}",
        expanded=False,
    ):
        st.write(result_data.get("contributing_intro", ""))
        chips = result_data.get("contributing_symptoms") or []
        if chips:
            chip_html = "".join(
                f'<span class="hs-insight-pill">{esc(item.get("label", ""))}</span>' for item in chips
            )
            render_html(chip_html)
        else:
            st.caption("No strong contributing symptoms were identified.")

    with st.expander(
        f"Pattern overlap · {result_data.get('overlap_preview', '')}",
        expanded=False,
    ):
        st.write(result_data.get("pattern_overlap_note", ""))

    notes = result_data.get("supplement_notes") or []
    with st.expander(
        f"Supplement notes ({len(notes)}) · {result_data.get('supplements_preview', '')}",
        expanded=False,
    ):
        st.write(result_data.get("supplement_intro", ""))
        for note in notes:
            st.markdown(f"**{note.get('name', 'Note')}**")
            st.write(note.get("summary", ""))
            if note.get("warning"):
                st.warning(note.get("warning"))
        st.caption(result_data.get("supplement_disclaimer", ""))

    with st.expander(
        f"Chart explanation · {result_data.get('chart_preview', '')}",
        expanded=False,
    ):
        st.write(result_data.get("chart_explanation", ""))

    with st.expander(
        f"Note · {result_data.get('note_preview', '')}",
        expanded=False,
    ):
        st.write(result_data.get("friendly_note", ""))


def render_sidebar():
    with st.sidebar:
        logo_path = ROOT / "static" / "images" / "heart_logo.png"
        if logo_path.exists():
            st.image(str(logo_path), width=88)
        else:
            render_html(f'<div style="text-align:center;transform:scale(0.8)">{HEART_SVG}</div>')
        render_html(
            '<p class="hs-sidebar-title">HerSignal</p>'
            '<p style="text-align:center;color:#5b4450;font-size:0.9rem;margin:0;">'
            "Educational PCOS support</p>"
        )

        if "nav_page" not in st.session_state or st.session_state.nav_page not in NAV_PAGES:
            st.session_state.nav_page = "Home"
        choice = st.radio(
            "Navigate",
            NAV_PAGES,
            index=NAV_PAGES.index(st.session_state.nav_page),
            label_visibility="collapsed",
        )
        st.session_state.nav_page = choice

        st.markdown("---")
        st.caption(
            "Insights, login, and PDF export are available in the full Flask app (`python app.py`), "
            "not in this shared demo."
        )


def main():
    st.set_page_config(
        page_title="HerSignal",
        page_icon="💗",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    init_session_state()
    inject_theme()
    render_sidebar()

    page = st.session_state.nav_page
    render_journey(page)
    disclaimer()

    if page == "Home":
        page_home()
    elif page == "Symptom checker":
        page_checker()
    else:
        page_results()


if __name__ == "__main__":
    main()
