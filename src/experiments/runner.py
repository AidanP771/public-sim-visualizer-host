from models.hospital_fifo import run_hospital_fifo_simulation
from models.hospital_priority import run_hospital_priority_simulation


MODEL_RUNNERS = {
    "fifo": run_hospital_fifo_simulation,
    "priority": run_hospital_priority_simulation,
}


def build_replication_seeds(replications, base_seed=42, seeds=None):
    # build deterministic seeds unless explicit seeds are provided
    if replications <= 0:
        raise ValueError("replications must be at least 1")

    if seeds is not None:
        if len(seeds) != replications:
            raise ValueError("len(seeds) must match replications")
        return list(seeds)

    return [base_seed + i for i in range(replications)]


def run_experiment_batch(
    model,
    replications,
    sim_time,
    arrival_mean,
    service_mean,
    num_nurses=1,
    base_seed=42,
    seeds=None,
):
    # run one scenario through the selected model
    model_key = model.lower()
    if model_key not in MODEL_RUNNERS:
        raise ValueError("model must be 'fifo' or 'priority'")

    run_model = MODEL_RUNNERS[model_key]
    run_seeds = build_replication_seeds(
        replications=replications,
        base_seed=base_seed,
        seeds=seeds,
    )

    rows = []
    for seed in run_seeds:
        # run one replication and capture summary stats
        result = run_model(
            sim_time=sim_time,
            arrival_mean=arrival_mean,
            service_mean=service_mean,
            num_nurses=num_nurses,
            seed=seed,
        )
        stats = result["stats"]

        row = {
            "model": model_key,
            "sim_time": sim_time,
            "arrival_mean": arrival_mean,
            "service_mean": service_mean,
            "num_nurses": num_nurses,
            "seed": seed,
            "total_arrived": stats.total_arrived,
            "total_served": stats.total_served,
            "average_wait": stats.average_wait(),
            "average_system_time": stats.average_system_time(),
            "utilization": stats.utilization(sim_time=sim_time, num_nurses=num_nurses),
            "max_queue_length": stats.max_queue_length,
        }

        # add triage specific waits for priority rows
        if model_key == "priority":
            row["average_wait_red"] = stats.average_wait_by_triage("red")
            row["average_wait_yellow"] = stats.average_wait_by_triage("yellow")
            row["average_wait_green"] = stats.average_wait_by_triage("green")

        rows.append(row)

    return rows
