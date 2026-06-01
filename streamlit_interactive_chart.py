"""Interactive results chart for Streamlit (mirrors static/js/dashboard.js)."""

from __future__ import annotations

import html
import json
from pathlib import Path

CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"


def _esc(text) -> str:
    return html.escape(str(text or ""))


def build_interactive_results_html(
    scores: dict,
    meaning_paragraphs: list[str],
    general_disclaimer: str,
    chart_fallback_src: str | None = None,
) -> str:
    """Score cards + radar chart + meaning block in one document (hover sync)."""
    hormonal = int(scores.get("hormonal") or 0)
    metabolic = int(scores.get("metabolic") or 0)
    inflammatory = int(scores.get("inflammatory") or 0)
    top_key = max(
        ("hormonal", "metabolic", "inflammatory"),
        key=lambda k: scores.get(k, 0) or 0,
    )
    max_val = max(hormonal, metabolic, inflammatory, 0)

    def score_card(key: str, label: str) -> str:
        top = " score-card top-score" if key == top_key and max_val > 0 else " score-card"
        value = int(scores.get(key) or 0)
        return (
            f'<div class="{top.strip()}" data-chart-category="{key}">'
            f"<h3>{_esc(label)}</h3>"
            f'<p class="score-card-value">{value}</p>'
            f"</div>"
        )

    paras = "".join(f'<p class="results-meaning-para">{_esc(p)}</p>' for p in meaning_paragraphs)
    fallback_img = ""
    if chart_fallback_src:
        fallback_img = (
            f'<img src="{_esc(chart_fallback_src)}" alt="Symptom pattern chart" '
            f'class="chart-image chart-image--fallback" hidden />'
        )

    scores_json = json.dumps(
        {"hormonal": hormonal, "metabolic": metabolic, "inflammatory": inflammatory}
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;700&family=Source+Sans+3:wght@400;600;700&display=swap" />
<style>
:root {{
  --hs-text: #3c2a35;
  --hs-accent: #8a3d67;
  --hs-muted: #5b4450;
  --hs-primary: #b94f87;
  --hs-surface: #ffffff;
  --hs-border: #ebcddd;
  --hs-secondary-bg: #fff7fb;
  --hs-secondary-border: #dcb7ca;
  --hs-shadow-soft: rgba(120, 70, 100, 0.06);
  --font-display: "Fraunces", Georgia, serif;
  --font-body: "Source Sans 3", system-ui, sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  padding: 0;
  font-family: var(--font-body);
  color: var(--hs-text);
  background: transparent;
}}
.score-cards {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 0 0 24px;
}}
@media (max-width: 640px) {{
  .score-cards {{ grid-template-columns: 1fr; }}
}}
.score-card {{
  text-align: center;
  padding: 20px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #fff7fb 0%, #fffdfd 100%);
  border: 1px solid #efd7e4;
  box-shadow: 0 6px 18px var(--hs-shadow-soft);
  cursor: default;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}}
.score-card h3 {{
  margin: 0 0 8px;
  font-family: var(--font-display);
  font-size: 1rem;
  color: #8a3d67;
}}
.score-card-value {{
  margin: 0;
  font-size: 2.2rem;
  font-weight: 700;
  color: #4f3844;
  line-height: 1;
}}
.score-card.top-score {{
  background: linear-gradient(135deg, #f4d7e6 0%, #f8eaf2 45%, #fff8fc 100%);
  border: 2px solid #c95f91;
}}
.score-card.chart-highlight {{
  border-color: #c95f91;
  box-shadow: 0 10px 26px var(--hs-shadow-soft);
  transform: translateY(-2px);
}}
.results-insight-row {{
  display: grid;
  grid-template-columns: minmax(240px, 0.95fr) minmax(260px, 1.05fr);
  gap: 24px;
  align-items: stretch;
}}
@media (max-width: 720px) {{
  .results-insight-row {{ grid-template-columns: 1fr; }}
}}
.chart-panel {{
  background: linear-gradient(180deg, #fff8fb 0%, #fffdfd 100%);
  border: 1px solid #efd7e4;
  border-radius: 20px;
  padding: 20px;
  box-shadow: 0 8px 22px var(--hs-shadow-soft);
  display: flex;
  flex-direction: column;
  min-height: 100%;
}}
.chart-panel h3 {{
  margin: 0 0 12px;
  font-family: var(--font-display);
  font-size: 1.15rem;
  color: var(--hs-accent);
}}
.chart-canvas-wrap {{
  position: relative;
  flex: 1;
  min-height: 260px;
  max-height: 340px;
  width: 100%;
}}
.chart-canvas-wrap canvas {{
  width: 100% !important;
  height: 100% !important;
}}
.chart-interaction-hint {{
  margin: 12px 0 0;
  font-size: 0.78rem;
  color: var(--hs-muted);
  text-align: center;
}}
.chart-panel--static .chart-canvas-wrap,
.chart-panel--static .chart-interaction-hint {{ display: none; }}
.chart-panel--static .chart-image--fallback {{
  display: block !important;
  max-height: 300px;
  margin: 0 auto;
  border-radius: 16px;
}}
.chart-image--fallback {{ max-width: 100%; height: auto; }}
.results-meaning-feature {{
  padding: 28px 30px;
  border-radius: 24px;
  background: linear-gradient(145deg, var(--hs-secondary-bg) 0%, var(--hs-surface) 100%);
  border: 1px solid var(--hs-secondary-border);
  box-shadow: 0 10px 28px var(--hs-shadow-soft);
  line-height: 1.75;
  height: 100%;
}}
.results-brand-tag {{
  margin: 0 0 10px;
  font-family: var(--font-display);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--hs-primary);
}}
.results-meaning-feature h3 {{
  margin: 0 0 14px;
  font-family: var(--font-display);
  font-size: 1.35rem;
  color: var(--hs-accent);
}}
.results-meaning-footnote {{
  font-size: 0.88rem;
  color: var(--hs-muted);
  margin: 0 !important;
}}
</style>
</head>
<body>
<div class="score-cards">
  {score_card("hormonal", "Hormonal")}
  {score_card("metabolic", "Metabolic")}
  {score_card("inflammatory", "Inflammatory")}
</div>
<div class="results-insight-row">
  <div class="chart-panel chart-panel--interactive" id="results-pattern-chart-panel"
       data-hormonal="{hormonal}" data-metabolic="{metabolic}" data-inflammatory="{inflammatory}">
    <h3>Pattern chart</h3>
    <div class="chart-canvas-wrap">
      <canvas id="results-pattern-chart" role="img"
        aria-label="Interactive radar chart of hormonal, metabolic, and inflammatory educational scores"></canvas>
    </div>
    <p class="chart-interaction-hint">Hover or tap each point to explore your category scores.</p>
    {fallback_img}
  </div>
  <section class="results-meaning-feature" aria-labelledby="results-meaning-heading">
    <p class="results-brand-tag">HerSignal insight</p>
    <h3 id="results-meaning-heading">What this may mean</h3>
    {paras}
    <p class="results-meaning-footnote">{_esc(general_disclaimer)}</p>
  </section>
</div>
<script src="{CHART_JS_CDN}" crossorigin="anonymous"></script>
<script>
(function () {{
  const panel = document.getElementById("results-pattern-chart-panel");
  const canvas = document.getElementById("results-pattern-chart");
  const scores = {scores_json};

  function showStatic() {{
    if (!panel) return;
    panel.classList.add("chart-panel--static");
    const img = panel.querySelector(".chart-image--fallback");
    if (img) img.hidden = false;
  }}

  if (!panel || !canvas || typeof Chart === "undefined") {{
    showStatic();
    return;
  }}

  const categories = [
    {{ key: "hormonal", label: "Hormonal", color: "#b94f87" }},
    {{ key: "metabolic", label: "Metabolic", color: "#7a4f8a" }},
    {{ key: "inflammatory", label: "Inflammatory", color: "#c97a4a" }},
  ];
  const values = categories.map((item) => {{
    const parsed = parseFloat(scores[item.key]);
    return Number.isNaN(parsed) ? 0 : parsed;
  }});
  const scaleMax = Math.max(5, Math.ceil(Math.max(...values, 0)));
  const scoreCards = document.querySelectorAll(".score-card[data-chart-category]");

  function clearHighlights() {{
    scoreCards.forEach((card) => card.classList.remove("chart-highlight"));
  }}
  function highlightCategory(index) {{
    clearHighlights();
    if (index === undefined || index === null || index < 0) return;
    const key = categories[index]?.key;
    if (!key) return;
    const card = document.querySelector('.score-card[data-chart-category="' + key + '"]');
    if (card) card.classList.add("chart-highlight");
  }}

  const ctx = canvas.getContext("2d");
  if (!ctx) {{
    showStatic();
    return;
  }}

  const chart = new Chart(ctx, {{
    type: "radar",
    data: {{
      labels: categories.map((item) => item.label),
      datasets: [{{
        label: "Your pattern",
        data: values,
        backgroundColor: "rgba(185, 79, 135, 0.22)",
        borderColor: "#b94f87",
        borderWidth: 2,
        pointBackgroundColor: categories.map((item) => item.color),
        pointBorderColor: "#ffffff",
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 8,
        pointHoverBackgroundColor: categories.map((item) => item.color),
      }}],
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      animation: {{ duration: 900, easing: "easeOutQuart" }},
      interaction: {{ mode: "nearest", intersect: true }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: "rgba(60, 42, 53, 0.92)",
          titleFont: {{ family: "'Source Sans 3', sans-serif", size: 13 }},
          bodyFont: {{ family: "'Source Sans 3', sans-serif", size: 13 }},
          padding: 12,
          callbacks: {{
            label(context) {{
              return "Educational score: " + (context.raw ?? 0);
            }},
          }},
        }},
      }},
      scales: {{
        r: {{
          beginAtZero: true,
          min: 0,
          max: scaleMax,
          ticks: {{
            stepSize: 1,
            backdropColor: "transparent",
            color: "rgba(91, 68, 80, 0.75)",
          }},
          grid: {{ color: "rgba(235, 205, 221, 0.65)" }},
          angleLines: {{ color: "rgba(235, 205, 221, 0.85)" }},
          pointLabels: {{
            font: {{ family: "'Fraunces', Georgia, serif", size: 13 }},
            color: "#7a2f56",
          }},
        }},
      }},
      onHover(_event, elements) {{
        if (elements.length) highlightCategory(elements[0].index);
        else clearHighlights();
      }},
    }},
  }});

  canvas.addEventListener("mouseleave", clearHighlights);
  scoreCards.forEach((card) => {{
    card.addEventListener("mouseenter", () => {{
      const key = card.dataset.chartCategory;
      const index = categories.findIndex((item) => item.key === key);
      if (index === -1) return;
      highlightCategory(index);
      const meta = chart.getDatasetMeta(0);
      const point = meta.data[index];
      if (point) {{
        chart.setActiveElements([{{ datasetIndex: 0, index }}]);
        chart.tooltip.setActiveElements([{{ datasetIndex: 0, index }}], {{
          x: point.x,
          y: point.y,
        }});
        chart.update();
      }}
    }});
    card.addEventListener("mouseleave", () => {{
      clearHighlights();
      chart.setActiveElements([]);
      chart.tooltip.setActiveElements([]);
      chart.update();
    }});
  }});
}})();
</script>
</body>
</html>"""


def chart_fallback_data_uri(chart_path: str | None, root: Path) -> str | None:
    if not chart_path:
        return None
    full = root / "static" / chart_path
    if not full.is_file():
        return None
    import base64

    data = base64.b64encode(full.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"
