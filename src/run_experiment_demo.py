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


def main():
    sim_time = 1000
    arrival_mean = 5
    service_mean = 4

    print("Experiment runner demo (3 replications)")
    print("-" * 40)

    demo_rows = []
    for model in ["fifo", "priority"]:
        rows = run_experiment_batch(
            model=model,
            replications=3,
            sim_time=sim_time,
            arrival_mean=arrival_mean,
            service_mean=service_mean,
            num_nurses=2,
            base_seed=100,
        )
        demo_rows.extend(rows)
        print(f"{model.upper()} (nurses=2)")
        print_experiment_rows(rows)
        print()

    runs_path = write_rows_to_csv(demo_rows, "experiment_demo_runs.csv")
    summary_rows = aggregate_rows(demo_rows)
    summary_path = write_rows_to_csv(summary_rows, "experiment_demo_summary.csv")
    print(f"saved per-run csv: {runs_path}")
    print(f"saved summary csv: {summary_path}")


if __name__ == "__main__":
    main()
