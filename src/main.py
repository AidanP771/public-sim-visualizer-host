from models.hospital_fifo import run_hospital_fifo_simulation
from models.hospital_priority import run_hospital_priority_simulation

def print_shared_stats(stats, num_nurses, sim_time):
    avg_wait = stats.average_wait()
    avg_system = stats.average_system_time()
    utilization = stats.utilization(sim_time=sim_time, num_nurses=num_nurses)

    print(f"Nurses: {num_nurses}")
    print("  Average wait:", round(avg_wait, 2))
    print("  Average system time:", round(avg_system, 2))
    print("  Utilization:", round(utilization, 3))
    print("  Max queue length:", stats.max_queue_length)

def print_priority_waits(stats):
    print("  Average wait (red):", round(stats.average_wait_by_triage("red"), 2))
    print("  Average wait (yellow):", round(stats.average_wait_by_triage("yellow"), 2))
    print("  Average wait (green):", round(stats.average_wait_by_triage("green"), 2))

def main():
    sim_time = 1000
    arrival_mean = 5
    service_mean = 4
    seed = 42

    print("Hospital Single-Queue Comparison: FIFO vs Priority")
    print(f"Sim time={sim_time}, arrival_mean={arrival_mean}, service_mean={service_mean}, seed={seed}")
    print()

    print("FIFO model")
    print("-" * 40)
    for num_nurses in [1, 2, 3]:
        fifo_result = run_hospital_fifo_simulation(
            sim_time=sim_time,
            arrival_mean=arrival_mean,
            service_mean=service_mean,
            num_nurses=num_nurses,
            seed=seed,
        )

        fifo_stats = fifo_result["stats"]
        print_shared_stats(fifo_stats, num_nurses, sim_time)
        print()

    print("Priority model (non-preemptive)")
    print("-" * 40)
    for num_nurses in [1, 2, 3]:
        priority_result = run_hospital_priority_simulation(
            sim_time=sim_time,
            arrival_mean=arrival_mean,
            service_mean=service_mean,
            num_nurses=num_nurses,
            seed=seed,
        )

        priority_stats = priority_result["stats"]
        print_shared_stats(priority_stats, num_nurses, sim_time)
        print_priority_waits(priority_stats)
        print()

if __name__ == "__main__":
    main()
