import argparse

from experiments.runner import MODEL_RUNNERS
from sim.replay_export import export_replay_trace

# run one standalone simulation and export a replay json for the streamlit ui
# this script keeps replay generation separate from csv experiment runners

def parse_args():
    # parse command-line options that define one simulation run and output path
    # returns argparse namespace with model, timing, seed, and file options
    parser = argparse.ArgumentParser(
        description="run one simulation and export a replay json trace"
    )
    parser.add_argument("--model", choices=["fifo", "priority"], default="priority")
    parser.add_argument("--sim-time", type=float, default=300.0)
    parser.add_argument("--arrival-mean", type=float, default=5.0)
    parser.add_argument("--service-mean", type=float, default=4.0)
    parser.add_argument("--num-nurses", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario-name", default="replay_demo")
    parser.add_argument("--run-id", default="run_1")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main():
    # execute selected simulation model once and convert events to replay json
    args = parse_args()
    run_model = MODEL_RUNNERS[args.model]

    # run existing headless model without touching csv summary pipelines
    result = run_model(
        sim_time=args.sim_time,
        arrival_mean=args.arrival_mean,
        service_mean=args.service_mean,
        num_nurses=args.num_nurses,
        seed=args.seed,
    )

    # export replay trace as a separate artifact for event-step visualization
    output_path = export_replay_trace(
        result=result,
        scenario_name=args.scenario_name,
        run_id=args.run_id,
        model=args.model,
        sim_end_time=args.sim_time,
        num_nurses=args.num_nurses,
        seed=args.seed,
        arrival_mean=args.arrival_mean,
        service_mean=args.service_mean,
        output_path=args.output,
    )

    # print a compact run summary for quick terminal verification
    print("Replay export complete")
    print("-" * 40)
    print(f"model: {args.model}")
    print(f"seed: {args.seed}")
    print(f"events: {len(result.get('events', []))}")
    print(f"saved replay json: {output_path}")


if __name__ == "__main__":
    main()
