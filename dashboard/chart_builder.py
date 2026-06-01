import uuid
import logging
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


logger = logging.getLogger(__name__)


def build_symptom_chart(scores):
    """
    Build and save a radar chart for the three symptom categories.

    A unique filename is generated for each chart so repeated submissions do not
    overwrite the previous image.
    """
    try:
        if not isinstance(scores, dict):
            logger.error("Chart scores were not provided as a dictionary.")
            return None

        labels = ["Hormonal", "Metabolic", "Inflammatory"]
        values = [
            float(scores.get("hormonal", 0)),
            float(scores.get("metabolic", 0)),
            float(scores.get("inflammatory", 0))
        ]

        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()

        values += values[:1]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

        ax.plot(angles, values, linewidth=2)
        ax.fill(angles, values, alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels)

        max_score = max(5, int(np.ceil(max(values[:-1]))))
        y_ticks = list(range(1, max_score + 1))
        ax.set_yticks(y_ticks)
        ax.set_yticklabels([str(value) for value in y_ticks])

        plt.tight_layout()

        charts_dir = Path("static") / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_id = uuid.uuid4().hex[:8]
        filename = f"symptom_chart_{timestamp}_{unique_id}.png"
        file_path = charts_dir / filename

        plt.savefig(file_path)
        plt.close(fig)

        return f"charts/{filename}"

    except Exception:
        logger.exception("Unexpected error while building symptom chart.")
        try:
            plt.close("all")
        except Exception:
            pass
        return None