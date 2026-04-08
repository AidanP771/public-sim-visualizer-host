import csv
from collections import defaultdict
from pathlib import Path


DEFAULT_GROUP_BY = ["model", "sim_time", "arrival_mean", "service_mean", "num_nurses"]
PREFERRED_FIELD_ORDER = [
    "model",
    "sim_time",
    "arrival_mean",
    "service_mean",
    "num_nurses",
    "seed",
    "replications",
    "total_arrived",
    "total_served",
    "average_wait",
    "average_system_time",
    "utilization",
    "max_queue_length",
    "average_wait_red",
    "average_wait_yellow",
    "average_wait_green",
]


def _default_data_dir():
    # resolve project data directory from this module path
    return Path(__file__).resolve().parents[2] / "data"


def _fieldnames_for_rows(rows):
    # keep preferred columns first and append any extra keys
    row_keys = set()
    for row in rows:
        row_keys.update(row.keys())

    ordered = [key for key in PREFERRED_FIELD_ORDER if key in row_keys]
    remaining = sorted(row_keys - set(ordered))
    return ordered + remaining


def write_rows_to_csv(rows, filename, data_dir=None):
    # write result rows to a csv file in the data directory
    if not rows:
        raise ValueError("rows must contain at least one result row")

    output_dir = Path(data_dir) if data_dir is not None else _default_data_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename
    fieldnames = _fieldnames_for_rows(rows)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def aggregate_rows(rows, group_by=None):
    # average numeric metrics across rows grouped by scenario keys
    if not rows:
        return []

    group_keys = list(group_by) if group_by is not None else list(DEFAULT_GROUP_BY)
    grouped = {}

    for row in rows:
        group_id = tuple(row.get(key) for key in group_keys)
        if group_id not in grouped:
            grouped[group_id] = {
                "group_values": {key: row.get(key) for key in group_keys},
                "replications": 0,
                "metric_sums": defaultdict(float),
                "metric_counts": defaultdict(int),
            }

        bucket = grouped[group_id]
        bucket["replications"] += 1

        for key, value in row.items():
            if key in group_keys or key == "seed":
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                bucket["metric_sums"][key] += value
                bucket["metric_counts"][key] += 1

    summary_rows = []
    for bucket in grouped.values():
        # convert grouped sums into mean values
        summary = dict(bucket["group_values"])
        summary["replications"] = bucket["replications"]

        metric_names = sorted(bucket["metric_sums"].keys())
        for metric_name in metric_names:
            total = bucket["metric_sums"][metric_name]
            count = bucket["metric_counts"][metric_name]
            summary[metric_name] = total / count if count > 0 else 0.0

        summary_rows.append(summary)

    return summary_rows
