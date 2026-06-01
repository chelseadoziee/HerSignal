from logic.scoring_engine import (
    collect_symptom_responses,
    calculate_category_scores,
)
from logic.result_generator import generate_result_summary
from dashboard.chart_builder import build_symptom_chart


def run_scoring_test():
    responses = collect_symptom_responses()

    print("Collected Responses:")
    for key, value in responses.items():
        print(f"{key}: {value}")

    print()

    scores = calculate_category_scores(responses)

    print("Calculated Scores:")
    for category, score in scores.items():
        print(f"{category}: {score}")

    print()

    summary = generate_result_summary(scores, responses)
    print(summary)

    chart_path = build_symptom_chart(scores)
    print(f"\nChart saved to: {chart_path}")


if __name__ == "__main__":
    run_scoring_test()