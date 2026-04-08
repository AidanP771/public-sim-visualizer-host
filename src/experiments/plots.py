import argparse
import csv
from pathlib import Path

import matplotlib
# use a non interactive backend so plots can be saved in scripts
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_PLOT_NAMES = [
    "average_wait_vs_nurses",
    "average_system_time_vs_nurses",
    "utilization_vs_nurses",
    "priority_wait_by_triage_vs_arrival_mean",
]


def default_summary_csv_path():
    # prefer official summary and fall back to demo summary
    project_root = Path(__file__).resolve().parents[2]
    preferred = project_root / "data" / "official_experiment_summary.csv"
    if preferred.exists():
        return preferred
    fallback = project_root / "data" / "official_scenarios_demo_summary.csv"
    return fallback


def default_results_dir():
    return Path(__file__).resolve().parents[2] / "results"


def read_summary_rows(summary_csv_path):
    # read all summary rows from csv into dictionaries
    rows = []
    with Path(summary_csv_path).open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            rows.append(row)
    return rows


def to_float(value):
    if value is None or value == "":
        return None
    return float(value)


def extract_model_series(rows, scenario_group, metric_name):
    # build sorted x and y values for this metric and scenario group
    series = {}
    for row in rows:
        if row.get("scenario_group") != scenario_group:
            continue
        model = row["model"]
        num_nurses = int(float(row["num_nurses"]))
        metric_value = to_float(row.get(metric_name))
        if metric_value is None:
            continue
        if model not in series:
            series[model] = []
        series[model].append((num_nurses, metric_value))

    for model in series:
        series[model].sort(key=lambda item: item[0])
    return series


def plot_model_metric_vs_nurses(rows, metric_name, ylabel, filename, results_dir):
    series = extract_model_series(
        rows=rows,
        scenario_group="nurse_count_comparison",
        metric_name=metric_name,
    )
    if not series:
        raise ValueError("no nurse_count_comparison rows found in summary csv")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for model, points in sorted(series.items()):
        x_values = [x for x, _ in points]
        y_values = [y for _, y in points]
        ax.plot(x_values, y_values, marker="o", linewidth=2, label=model.upper())

    ax.set_xlabel("number of nurses")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{ylabel} vs number of nurses")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    output_path = Path(results_dir) / filename
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_priority_wait_by_triage_vs_load(rows, results_dir):
    # show one nurse priority waits across interarrival means by triage class
    priority_rows = []
    for row in rows:
        if row.get("scenario_group") != "load_comparison_one_nurse":
            continue
        if row.get("model") != "priority":
            continue
        priority_rows.append(row)

    if not priority_rows:
        raise ValueError("no priority one nurse load comparison rows found in summary csv")

    points = []
    for row in priority_rows:
        points.append(
            {
                "arrival_mean": to_float(row["arrival_mean"]),
                "red": to_float(row.get("average_wait_red")),
                "yellow": to_float(row.get("average_wait_yellow")),
                "green": to_float(row.get("average_wait_green")),
            }
        )
    points.sort(key=lambda item: item["arrival_mean"])

    x_values = [item["arrival_mean"] for item in points]
    red_waits = [item["red"] for item in points]
    yellow_waits = [item["yellow"] for item in points]
    green_waits = [item["green"] for item in points]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x_values, red_waits, marker="o", linewidth=2, color="red", label="red")
    ax.plot(x_values, yellow_waits, marker="o", linewidth=2, color="goldenrod", label="yellow")
    ax.plot(x_values, green_waits, marker="o", linewidth=2, color="green", label="green")

    ax.set_xlabel("mean interarrival time")
    ax.set_ylabel("average wait")
    ax.set_title("priority average wait by triage at one nurse")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()

    output_path = Path(results_dir) / "priority_wait_by_triage_vs_arrival_mean.png"
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def build_average_wait_vs_nurses(rows, results_dir):
    return plot_model_metric_vs_nurses(
        rows=rows,
        metric_name="average_wait",
        ylabel="average wait",
        filename="average_wait_vs_nurses.png",
        results_dir=results_dir,
    )


def build_average_system_time_vs_nurses(rows, results_dir):
    return plot_model_metric_vs_nurses(
        rows=rows,
        metric_name="average_system_time",
        ylabel="average system time",
        filename="average_system_time_vs_nurses.png",
        results_dir=results_dir,
    )


def build_utilization_vs_nurses(rows, results_dir):
    return plot_model_metric_vs_nurses(
        rows=rows,
        metric_name="utilization",
        ylabel="utilization",
        filename="utilization_vs_nurses.png",
        results_dir=results_dir,
    )


def build_priority_wait_by_triage_vs_arrival_mean(rows, results_dir):
    return plot_priority_wait_by_triage_vs_load(rows=rows, results_dir=results_dir)


# map plot names to builder functions
PLOT_BUILDERS = {
    "average_wait_vs_nurses": build_average_wait_vs_nurses,
    "average_system_time_vs_nurses": build_average_system_time_vs_nurses,
    "utilization_vs_nurses": build_utilization_vs_nurses,
    "priority_wait_by_triage_vs_arrival_mean": build_priority_wait_by_triage_vs_arrival_mean,
}


def make_plot_set(plot_names, summary_csv_path=None, results_dir=None):
    # load rows once and build only the requested plot names
    if not plot_names:
        raise ValueError("plot_names must include at least one name")

    summary_path = Path(summary_csv_path) if summary_csv_path else default_summary_csv_path()
    if not summary_path.exists():
        raise FileNotFoundError(f"summary csv not found: {summary_path}")

    output_dir = Path(results_dir) if results_dir else default_results_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_summary_rows(summary_path)
    unique_names = list(dict.fromkeys(plot_names))

    unknown_names = [name for name in unique_names if name not in PLOT_BUILDERS]
    if unknown_names:
        available = ", ".join(sorted(PLOT_BUILDERS.keys()))
        unknown = ", ".join(unknown_names)
        raise ValueError(f"unknown plot name(s): {unknown}. available: {available}")

    saved_paths = []
    for name in unique_names:
        saved_paths.append(PLOT_BUILDERS[name](rows, output_dir))
    return saved_paths


def create_official_summary_plots(summary_csv_path=None, results_dir=None):
    # create the default report plot set
    return make_plot_set(
        plot_names=DEFAULT_PLOT_NAMES,
        summary_csv_path=summary_csv_path,
        results_dir=results_dir,
    )


def main():
    parser = argparse.ArgumentParser(description="generate report plots from official summary csv")
    parser.add_argument(
        "--summary-csv",
        dest="summary_csv",
        default=None,
        help="path to official summary csv",
    )
    parser.add_argument(
        "--results-dir",
        dest="results_dir",
        default=None,
        help="directory to save plot images",
    )
    parser.add_argument(
        "--plots",
        dest="plots",
        default=None,
        help="comma separated plot names to build",
    )
    args = parser.parse_args()

    plot_names = None
    if args.plots:
        plot_names = [name.strip() for name in args.plots.split(",") if name.strip()]

    if plot_names:
        saved_paths = make_plot_set(
            plot_names=plot_names,
            summary_csv_path=args.summary_csv,
            results_dir=args.results_dir,
        )
    else:
        saved_paths = create_official_summary_plots(
            summary_csv_path=args.summary_csv,
            results_dir=args.results_dir,
        )

    for path in saved_paths:
        print(f"saved plot: {path}")


if __name__ == "__main__":
    main()
