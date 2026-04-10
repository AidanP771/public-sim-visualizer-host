from experiments.export import aggregate_rows
from experiments.export import write_rows_to_csv
from experiments.runner import run_experiment_batch


def print_experiment_rows(rows):
    for row in rows:
        print(
            f"  seed={row['seed']} served={row['total_served']}/{row['total_arrived']} "
            f"wait={row['average_wait']:.2f} system={row['average_system_time']:.2f} "
            f"util={row['utilization']:.3f} max_q={row['max_queue_length']}"
        )
        if row["model"] == "priority":
            print(
                f"    wait_red={row['average_wait_red']:.2f} "
                f"wait_yellow={row['average_wait_yellow']:.2f} "
                f"wait_green={row['average_wait_green']:.2f}"
            )


def _format_table(headers, rows):
    # build a simple ascii table with dynamic column widths
    string_rows = [[str(value) for value in row] for row in rows]
    widths = [len(header) for header in headers]

    for row in string_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def make_separator():
        return "+-" + "-+-".join("-" * width for width in widths) + "-+"

    def make_row(values):
        padded = [f"{value:<{widths[index]}}" for index, value in enumerate(values)]
        return "| " + " | ".join(padded) + " |"

    lines = [make_separator(), make_row(headers), make_separator()]
    for row in string_rows:
        lines.append(make_row(row))
    lines.append(make_separator())
    return "\n".join(lines)


def _build_model_summary_index(summary_rows):
    # index summary rows by (model, num_nurses) for quick lookups
    return {
        (row["model"], int(row["num_nurses"])): row
        for row in summary_rows
    }


def _print_comparison_table(summary_rows, nurse_levels):
    summary_by_model_and_nurses = _build_model_summary_index(summary_rows)

    headers = [
        "nurses",
        "fifo_wait",
        "prio_wait",
        "delta_wait",
        "fifo_system",
        "prio_system",
        "delta_system",
        "fifo_util",
        "prio_util",
        "delta_util",
    ]

    rows = []
    for nurses in nurse_levels:
        fifo = summary_by_model_and_nurses[("fifo", nurses)]
        priority = summary_by_model_and_nurses[("priority", nurses)]

        rows.append(
            [
                nurses,
                f"{fifo['average_wait']:.2f}",
                f"{priority['average_wait']:.2f}",
                f"{priority['average_wait'] - fifo['average_wait']:+.2f}",
                f"{fifo['average_system_time']:.2f}",
                f"{priority['average_system_time']:.2f}",
                f"{priority['average_system_time'] - fifo['average_system_time']:+.2f}",
                f"{fifo['utilization']:.3f}",
                f"{priority['utilization']:.3f}",
                f"{priority['utilization'] - fifo['utilization']:+.3f}",
            ]
        )

    print("FIFO vs PRIORITY (averaged over replications)")
    print(_format_table(headers, rows))


def _print_priority_triage_table(summary_rows, nurse_levels):
    summary_by_model_and_nurses = _build_model_summary_index(summary_rows)

    headers = ["nurses", "wait_red", "wait_yellow", "wait_green"]
    rows = []
    for nurses in nurse_levels:
        priority = summary_by_model_and_nurses[("priority", nurses)]
        rows.append(
            [
                nurses,
                f"{priority['average_wait_red']:.2f}",
                f"{priority['average_wait_yellow']:.2f}",
                f"{priority['average_wait_green']:.2f}",
            ]
        )

    print("PRIORITY triage waits (averaged)")
    print(_format_table(headers, rows))


def main():
    sim_time = 1000
    arrival_mean = 5
    service_mean = 4
    replications = 3
    nurse_levels = [1, 2, 3]
    models = ["fifo", "priority"]

    print("Experiment runner demo")
    print("-" * 40)
    print(
        f"Comparing models {models} across nurses={nurse_levels} "
        f"with {replications} replications each"
    )
    print()

    demo_rows = []
    for nurses in nurse_levels:
        print(f"nurses={nurses}")
        for model in models:
            rows = run_experiment_batch(
                model=model,
                replications=replications,
                sim_time=sim_time,
                arrival_mean=arrival_mean,
                service_mean=service_mean,
                num_nurses=nurses,
                base_seed=100,
            )
            demo_rows.extend(rows)
            print(f"{model.upper()} per-run")
            print_experiment_rows(rows)
            print()
        print("-" * 40)

    runs_path = write_rows_to_csv(demo_rows, "experiment_demo_runs.csv")
    summary_rows = aggregate_rows(demo_rows)
    summary_path = write_rows_to_csv(summary_rows, "experiment_demo_summary.csv")

    _print_comparison_table(summary_rows, nurse_levels)
    print()
    _print_priority_triage_table(summary_rows, nurse_levels)
    print()

    print(f"saved per-run csv: {runs_path}")
    print(f"saved summary csv: {summary_path}")


if __name__ == "__main__":
    main()
