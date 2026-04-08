from experiments.export import aggregate_rows
from experiments.export import write_rows_to_csv
from experiments.runner import run_experiment_batch


DEFAULT_SIM_TIME = 1000
DEFAULT_SERVICE_MEAN = 4
DEFAULT_REPLICATIONS = 20
DEFAULT_BASE_SEED = 1000
DEFAULT_FIXED_LOAD_ARRIVAL_MEAN = 5
DEFAULT_LOAD_ARRIVAL_MEANS = [3, 4, 5, 6, 7]
DEFAULT_MODELS = ["fifo", "priority"]
DEFAULT_NURSE_COUNTS = [1, 2, 3]


def build_official_scenarios(
    sim_time=DEFAULT_SIM_TIME,
    service_mean=DEFAULT_SERVICE_MEAN,
    replications=DEFAULT_REPLICATIONS,
    base_seed=DEFAULT_BASE_SEED,
):
    # define the official report scenario set
    scenarios = []
    scenario_index = 0

    # compare nurse counts under fixed load
    for model in DEFAULT_MODELS:
        for num_nurses in DEFAULT_NURSE_COUNTS:
            scenarios.append(
                {
                    "scenario_group": "nurse_count_comparison",
                    "scenario_name": f"{model}_nurses_{num_nurses}_fixed_load",
                    "model": model,
                    "sim_time": sim_time,
                    "arrival_mean": DEFAULT_FIXED_LOAD_ARRIVAL_MEAN,
                    "service_mean": service_mean,
                    "num_nurses": num_nurses,
                    "replications": replications,
                    "base_seed": base_seed + (scenario_index * 1000),
                }
            )
            scenario_index += 1

    # compare congestion levels with one nurse
    for model in DEFAULT_MODELS:
        for arrival_mean in DEFAULT_LOAD_ARRIVAL_MEANS:
            scenarios.append(
                {
                    "scenario_group": "load_comparison_one_nurse",
                    "scenario_name": f"{model}_one_nurse_arrival_{arrival_mean}",
                    "model": model,
                    "sim_time": sim_time,
                    "arrival_mean": arrival_mean,
                    "service_mean": service_mean,
                    "num_nurses": 1,
                    "replications": replications,
                    "base_seed": base_seed + (scenario_index * 1000),
                }
            )
            scenario_index += 1

    # include a direct fifo vs priority comparison case
    for model in DEFAULT_MODELS:
        scenarios.append(
            {
                "scenario_group": "fifo_vs_priority_comparison",
                "scenario_name": f"{model}_medium_load_two_nurses",
                "model": model,
                "sim_time": sim_time,
                "arrival_mean": DEFAULT_FIXED_LOAD_ARRIVAL_MEAN,
                "service_mean": service_mean,
                "num_nurses": 2,
                "replications": replications,
                "base_seed": base_seed + (scenario_index * 1000),
            }
        )
        scenario_index += 1

    return scenarios


def run_scenarios(scenarios):
    # run each scenario and attach scenario labels to each row
    all_rows = []
    for scenario in scenarios:
        rows = run_experiment_batch(
            model=scenario["model"],
            replications=scenario["replications"],
            sim_time=scenario["sim_time"],
            arrival_mean=scenario["arrival_mean"],
            service_mean=scenario["service_mean"],
            num_nurses=scenario["num_nurses"],
            base_seed=scenario["base_seed"],
        )

        for row in rows:
            row["scenario_group"] = scenario["scenario_group"]
            row["scenario_name"] = scenario["scenario_name"]

        all_rows.extend(rows)

    return all_rows


def run_official_scenarios(
    sim_time=DEFAULT_SIM_TIME,
    service_mean=DEFAULT_SERVICE_MEAN,
    replications=DEFAULT_REPLICATIONS,
    base_seed=DEFAULT_BASE_SEED,
):
    # build the official scenario definitions and run them
    scenarios = build_official_scenarios(
        sim_time=sim_time,
        service_mean=service_mean,
        replications=replications,
        base_seed=base_seed,
    )
    rows = run_scenarios(scenarios)
    return scenarios, rows


def run_and_export_official_scenarios(
    sim_time=DEFAULT_SIM_TIME,
    service_mean=DEFAULT_SERVICE_MEAN,
    replications=DEFAULT_REPLICATIONS,
    base_seed=DEFAULT_BASE_SEED,
    runs_filename="official_experiment_runs.csv",
    summary_filename="official_experiment_summary.csv",
    data_dir=None,
):
    # run official scenarios and export both run level and summary csv files
    scenarios, rows = run_official_scenarios(
        sim_time=sim_time,
        service_mean=service_mean,
        replications=replications,
        base_seed=base_seed,
    )

    summary_rows = aggregate_rows(
        rows,
        group_by=[
            "scenario_group",
            "scenario_name",
            "model",
            "sim_time",
            "arrival_mean",
            "service_mean",
            "num_nurses",
        ],
    )

    runs_path = write_rows_to_csv(rows, runs_filename, data_dir=data_dir)
    summary_path = write_rows_to_csv(summary_rows, summary_filename, data_dir=data_dir)

    return {
        "scenarios": scenarios,
        "rows": rows,
        "summary_rows": summary_rows,
        "runs_path": runs_path,
        "summary_path": summary_path,
    }
