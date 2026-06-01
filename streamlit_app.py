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
import streamlit.components.v1 as components

from streamlit_interactive_chart import (
    build_interactive_results_html,
    chart_fallback_data_uri,
)

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


@st.cache_data(show_spinner=False)
def logo_data_uri() -> str | None:
    """Inline logo for HTML blocks (Streamlit does not serve /static like Flask)."""
    path = ROOT / "static" / "images" / "heart_logo.png"
    if not path.is_file():
        return None
    import base64

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_logo_markup(size: str = "hero", alt: str = "HerSignal logo") -> str:
    """Centered logo markup: landing (130px), sidebar (88px), compact (78px), empty (96px)."""
    src = logo_data_uri()
    sizes = {
        "hero": ("130", "hs-hero-logo"),
        "sidebar": ("88", "hs-sidebar-logo"),
        "compact": ("78", "hs-hero-logo hs-hero-logo--compact"),
        "empty": ("96", "hs-empty-logo"),
    }
    width, css_class = sizes.get(size, sizes["hero"])
    if src:
        return (
            f'<div class="hs-image-wrap hs-image-wrap--{size}">'
            f'<img src="{src}" alt="{esc(alt)}" class="{css_class}" width="{width}" height="{width}" '
            f'decoding="async" />'
            f"</div>"
        )
    return f'<div class="hs-image-wrap hs-image-wrap--{size}">{HEART_SVG}</div>'


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


def render_hero(title: str, subtitle: str, variant: str = "landing"):
    """Hero block aligned with templates/_hero.html (logo centred above title)."""
    logo = render_logo_markup("hero" if variant == "landing" else "compact")
    variant_class = " hs-hero-card--landing" if variant == "landing" else " hs-hero-card--compact"
    tag = (
        '<p class="hs-brand-tag">HerSignal insight</p>'
        if variant == "landing"
        else ""
    )
    render_html(
        f'<header class="hs-hero-card{variant_class}" aria-labelledby="hs-page-hero-title">'
        f"{logo}"
        f'<div class="hs-hero-text">'
        f"{tag}"
        f'<h1 id="hs-page-hero-title">{esc(title)}</h1>'
        f'<p class="hs-hero-sub">{esc(subtitle)}</p>'
        f"</div>"
        f"</header>"
    )


def render_centered_buttons(primary_label: str, primary_page: str, secondary_label: str, secondary_page: str):
    """Primary / secondary actions centred under the landing hero (Flask btn-row--center)."""
    _pad, col_a, col_b, _pad2 = st.columns([0.65, 1.35, 1.35, 0.65])
    with col_a:
        if st.button(primary_label, type="primary", use_container_width=True, key=f"nav_{primary_page}"):
            st.session_state.nav_page = primary_page
            st.rerun()
    with col_b:
        if st.button(secondary_label, use_container_width=True, key=f"nav_{secondary_page}"):
            st.session_state.nav_page = secondary_page
            st.rerun()


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


def meaning_paragraphs(result_data: dict) -> list[str]:
    paragraphs = result_data.get("why_hersignal_paragraphs") or []
    if not paragraphs and result_data.get("why_hersignal_presented_response"):
        paragraphs = [result_data["why_hersignal_presented_response"]]
    return paragraphs


def render_interactive_results(scores: dict, result_data: dict, chart_path: str | None):
    """Radar chart with score-card hover sync (same behaviour as Flask dashboard.js)."""
    fallback = chart_fallback_data_uri(chart_path, ROOT)
    html_doc = build_interactive_results_html(
        scores,
        meaning_paragraphs(result_data),
        result_data.get("general_disclaimer", "Educational only. Not a diagnosis or treatment plan."),
        chart_fallback_src=fallback,
    )
    components.html(html_doc, height=620, scrolling=False)


def _panel_html(title: str, preview: str, body_html: str, nested: bool = False) -> str:
    nested_class = " hs-results-panel--nested" if nested else ""
    preview_span = (
        f'<span class="hs-results-panel__preview">{esc(preview)}</span>' if preview else ""
    )
    return (
        f'<details class="hs-results-panel{nested_class}">'
        f'<summary class="hs-results-panel__summary">'
        f'<span class="hs-results-panel__title">{esc(title)}</span>'
        f"{preview_span}"
        f"</summary>"
        f'<div class="hs-results-panel__body">{body_html}</div>'
        f"</details>"
    )


def render_results_panels(result_data: dict):
    contrib_body = (
        f'<p class="hs-card-intro">{esc(result_data.get("contributing_intro", ""))}</p>'
    )
    chips = result_data.get("contributing_symptoms") or []
    if chips:
        chip_html = "".join(
            f'<span class="hs-insight-pill">{esc(item.get("label", ""))}</span>' for item in chips
        )
        contrib_body += f'<div>{chip_html}</div>'
    else:
        contrib_body += '<p class="hs-card-note">No strong contributing symptoms were identified.</p>'
    panels = [
        _panel_html(
            "Contributing symptoms",
            result_data.get("contributing_preview", ""),
            contrib_body,
        ),
        _panel_html(
            "Pattern overlap",
            result_data.get("overlap_preview", ""),
            f'<p>{esc(result_data.get("pattern_overlap_note", ""))}</p>',
        ),
    ]

    notes = result_data.get("supplement_notes") or []
    supp_inner = f'<p class="hs-card-intro">{esc(result_data.get("supplement_intro", ""))}</p>'
    if notes:
        nested_parts = []
        for note in notes:
            note_body = f"<p>{esc(note.get('summary', ''))}</p>"
            if note.get("warning"):
                note_body += f'<p class="hs-supplement-warning">{esc(note.get("warning"))}</p>'
            preview_span = (
                f'<span class="hs-results-panel__preview">{esc(note.get("preview", ""))}</span>'
                if note.get("preview")
                else ""
            )
            nested_parts.append(
                f'<details class="hs-results-panel hs-results-panel--nested">'
                f'<summary class="hs-results-panel__summary">'
                f'<span class="hs-results-panel__title">{esc(note.get("name", "Note"))}</span>'
                f"{preview_span}"
                f"</summary>"
                f'<div class="hs-results-panel__body">{note_body}</div>'
                f"</details>"
            )
        supp_inner += "".join(nested_parts)
        supp_inner += (
            f'<p class="hs-card-note" style="margin-top:14px">'
            f'{esc(result_data.get("supplement_disclaimer", ""))}</p>'
        )
    else:
        supp_inner += '<p class="hs-card-note">No supplement notes for this pattern.</p>'
    panels.append(
        _panel_html(
            f"Supplement notes ({len(notes)})",
            result_data.get("supplements_preview", ""),
            supp_inner,
        )
    )
    panels.append(
        _panel_html(
            "Chart explanation",
            result_data.get("chart_preview", ""),
            f'<p>{esc(result_data.get("chart_explanation", ""))}</p>',
        )
    )
    panels.append(
        _panel_html(
            "Note",
            result_data.get("note_preview", ""),
            f'<p>{esc(result_data.get("friendly_note", ""))}</p>',
        )
    )
    render_html(f'<div class="hs-results-panels-stack">{"".join(panels)}</div>')


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


def render_footer_credit():
    render_html('<p class="hs-site-credit">By Chelsea Dozie</p>')


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
        variant="landing",
    )
    render_centered_buttons(
        "Start symptom checker",
        "Symptom checker",
        "View latest results",
        "Results",
    )

    with hs_section():
        render_html(
            '<section class="hs-dashboard-panel" aria-labelledby="hs-home-helps-heading">'
            '<h2 id="hs-home-helps-heading" class="hs-dashboard-title">What HerSignal helps with</h2>'
        )
        render_feature_cards()
        render_html("</section>")

    with hs_section():
        render_html(
            '<section class="hs-dashboard-panel hs-dashboard-panel--chat" '
            'aria-labelledby="hs-ask-heading">'
            '<h2 id="hs-ask-heading" class="hs-dashboard-title">Ask HerSignal</h2>'
        )
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
        render_html("</section>")


def _symptom_answered_count(questions: list) -> int:
    total = 0
    for item in questions:
        val = st.session_state.get(f"sym_{item['id']}")
        if val in ("yes", "no", "maybe"):
            total += 1
    return total


def page_checker():
    from logic.scoring_engine import load_symptom_questions, normalise_response, calculate_category_scores
    from logic.result_generator import generate_result_data
    from dashboard.chart_builder import build_symptom_chart

    render_hero(
        "Understand your pattern",
        "Answer with yes, no, or maybe. Questions are grouped by category.",
        variant="compact",
    )

    with hs_section():
        render_html('<section class="hs-dashboard-panel hs-dashboard-panel--checker">')
        render_html(
            '<p class="hs-symptom-draft-note" role="note">'
            "Answers stay in this session until you submit. The full HerSignal app can save "
            "summary scores to <strong>Insights</strong> when you are logged in."
            "</p>"
        )

        questions = load_symptom_questions()
        if not questions:
            st.error("Symptom questions could not be loaded.")
            return

        total_q = len(questions)
        answered = _symptom_answered_count(questions)
        pct = int((answered / total_q) * 100) if total_q else 0
        render_html(
            f'<div class="hs-symptom-progress" role="region">'
            f'<p class="hs-symptom-progress-text"><strong>{answered}</strong> of {total_q} answered</p>'
            f'<div class="hs-symptom-progress-bar" aria-hidden="true">'
            f'<span class="hs-symptom-progress-fill" style="width:{pct}%"></span>'
            f"</div></div>"
        )

        col_back, _ = st.columns([1, 3])
        with col_back:
            if st.button("Back to chat", use_container_width=True):
                st.session_state.nav_page = "Home"
                st.rerun()

        responses = {}
        with st.form("symptom_form", clear_on_submit=False):
            idx = 0
            for category in ("hormonal", "metabolic", "inflammatory"):
                group = [q for q in questions if q.get("category") == category]
                if not group:
                    continue
                render_html(
                    f'<div class="hs-category hs-category--{category}">'
                    f'<p class="hs-category-title">{esc(CATEGORY_LABELS.get(category, category.title()))}</p>'
                )
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
                render_html("</div>")

            submitted = st.form_submit_button("See my results", type="primary", use_container_width=True)
        render_html("</section>")

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
            render_html(
                '<div class="hs-empty-state">'
                f"{render_logo_markup('empty', alt='')}"
                "<h2>No results yet</h2>"
                '<p class="hs-section-intro">Complete the symptom checker to see your pattern summary.</p>'
                "</div>"
            )
            _pad, col_go, _pad2 = st.columns([1, 1.2, 1])
            with col_go:
                if st.button("Go to symptom checker", type="primary", use_container_width=True):
                    st.session_state.nav_page = "Symptom checker"
                    st.rerun()
        return

    user_name = st.session_state.user_name
    intro = result_data.get("page_intro", "") or "Your latest educational scores are below."
    if user_name:
        intro = f"{user_name}, {intro[0].lower()}{intro[1:]}"

    render_hero(
        result_data.get("page_title", "Your symptom pattern"),
        intro,
        variant="compact",
    )

    with hs_section():
        render_html('<section class="hs-dashboard-panel hs-dashboard-panel--results">')

        btn_a, btn_b, btn_c = st.columns(3)
        with btn_a:
            if st.button("Checker again", use_container_width=True):
                st.session_state.nav_page = "Symptom checker"
                st.rerun()
        with btn_b:
            if st.button("Ask HerSignal", use_container_width=True):
                st.session_state.nav_page = "Home"
                st.rerun()
        with btn_c:
            st.caption("PDF export and saved insights are in the full app.")

        render_interactive_results(scores, result_data, st.session_state.chart_path)

        render_results_panels(result_data)
        render_html("</section>")


def render_sidebar():
    with st.sidebar:
        render_html(
            '<div class="hs-sidebar-brand">'
            f"{render_logo_markup('sidebar')}"
            '<p class="hs-sidebar-title">HerSignal</p>'
            '<p class="hs-sidebar-tagline">Educational PCOS support</p>'
            "</div>"
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

    render_footer_credit()


if __name__ == "__main__":
    main()
