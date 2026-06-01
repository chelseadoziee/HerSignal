"""
Helpers for saved educational score snapshots (no raw symptom answers stored).
"""


def dominant_category_label(scores):
    """
    Human-readable label for which category registered strongest in this snapshot.
    """
    h = float(scores.get("hormonal") or 0)
    m = float(scores.get("metabolic") or 0)
    inf = float(scores.get("inflammatory") or 0)
    items = [("Hormonal", h), ("Metabolic", m), ("Inflammatory", inf)]
    mx = max(h, m, inf)
    if mx <= 0:
        return "Balanced pattern"
    tops = [name for name, v in items if abs(v - mx) < 1e-9]
    if len(tops) > 1:
        return " · ".join(tops)
    return tops[0]


def format_delta(value):
    """Short string for UI (+1.5, −0.25, —)."""
    if value is None:
        return "—"
    if abs(value) < 1e-9:
        return "0"
    if value > 0:
        return f"+{value:g}"
    return f"{value:g}"


def snapshots_with_deltas(rows_newest_first):
    """
    rows_newest_first: ORM objects with hormonal, metabolic, inflammatory, created_at.

    Returns list of dicts for templates, each with optional delta_* vs the next older row.
    """
    out = []
    for i, row in enumerate(rows_newest_first):
        older = rows_newest_first[i + 1] if i + 1 < len(rows_newest_first) else None
        entry = {
            "id": row.id,
            "created_at": row.created_at,
            "hormonal": row.hormonal,
            "metabolic": row.metabolic,
            "inflammatory": row.inflammatory,
            "dominant_label": row.dominant_label,
            "test_type": getattr(row, "test_type", None) or "baseline",
            "delta_hormonal": None,
            "delta_metabolic": None,
            "delta_inflammatory": None,
        }
        if older:
            dh = round(row.hormonal - older.hormonal, 2)
            dm = round(row.metabolic - older.metabolic, 2)
            di = round(row.inflammatory - older.inflammatory, 2)
            entry["delta_hormonal"] = dh
            entry["delta_metabolic"] = dm
            entry["delta_inflammatory"] = di
            entry["delta_hormonal_display"] = format_delta(dh)
            entry["delta_metabolic_display"] = format_delta(dm)
            entry["delta_inflammatory_display"] = format_delta(di)
        else:
            entry["delta_hormonal_display"] = "—"
            entry["delta_metabolic_display"] = "—"
            entry["delta_inflammatory_display"] = "—"
        out.append(entry)
    return out


def snapshot_select_options(rows_newest_first):
    """For compare dropdowns: id + short label."""
    out = []
    for row in rows_newest_first:
        tt = getattr(row, "test_type", None) or "baseline"
        suffix = " · Follow-up" if str(tt).lower() == "retake" else " · Baseline"
        out.append(
            {
                "id": row.id,
                "label": row.created_at.strftime("%d %b %Y · %H:%M") + suffix,
            }
        )
    return out


def sparkline_specs(rows_oldest_first, width=140, height=42, padding=6):
    """
    Build SVG polyline point strings per category (oldest → newest, left → right).
    Returns dict hormonal|metabolic|inflammatory -> {points, width, height, stroke} or {} if no rows.
    """
    if not rows_oldest_first:
        return {}
    n = len(rows_oldest_first)
    specs_meta = [
        ("hormonal", "#8a3d67"),
        ("metabolic", "#2d6a4f"),
        ("inflammatory", "#b85c6a"),
    ]
    result = {}
    for key, stroke in specs_meta:
        vals = [float(getattr(r, key, 0) or 0) for r in rows_oldest_first]
        vmin, vmax = min(vals), max(vals)
        span = max(vmax - vmin, 1e-9)
        parts = []
        if n == 1:
            v = vals[0]
            norm = (v - vmin) / span
            y = (height - padding) - norm * (height - 2 * padding)
            parts = [f"{padding:.1f},{y:.1f}", f"{width - padding:.1f},{y:.1f}"]
        else:
            for i, v in enumerate(vals):
                x = padding + (i / (n - 1)) * (width - 2 * padding)
                norm = (v - vmin) / span
                y = (height - padding) - norm * (height - 2 * padding)
                parts.append(f"{x:.1f},{y:.1f}")
        result[key] = {
            "points": " ".join(parts),
            "width": width,
            "height": height,
            "stroke": stroke,
        }
    return result
