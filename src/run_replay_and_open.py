import argparse
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

from experiments.runner import MODEL_RUNNERS
from sim.replay_export import export_replay_trace

# run one replay export and optionally open the streamlit visualizer
# this keeps replay generation separate from csv experiment workflows


def parse_args():
    # parse simulation settings, export output, and optional ui launch settings
    parser = argparse.ArgumentParser(
        description="run one simulation, export replay json, and optionally open streamlit"
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
    parser.add_argument("--open-ui", action="store_true")
    parser.add_argument(
        "--streamlit-app",
        default="src/visualization/streamlit_app.py",
    )
    parser.add_argument("--streamlit-port", type=int, default=None)
    return parser.parse_args()


def main():
    # run one headless simulation and export replay trace json
    args = parse_args()
    run_model = MODEL_RUNNERS[args.model]

    result = run_model(
        sim_time=args.sim_time,
        arrival_mean=args.arrival_mean,
        service_mean=args.service_mean,
        num_nurses=args.num_nurses,
        seed=args.seed,
    )

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

    resolved_output = Path(output_path).resolve()
    print("Replay export complete")
    print("-" * 40)
    print(f"model: {args.model}")
    print(f"seed: {args.seed}")
    print(f"events: {len(result.get('events', []))}")
    print(f"replay json path: {resolved_output}")

    if args.open_ui:
        _launch_streamlit(
            streamlit_app=Path(args.streamlit_app),
            streamlit_port=args.streamlit_port,
        )


def _launch_streamlit(streamlit_app: Path, streamlit_port: int | None) -> None:
    # launch streamlit in a subprocess so replay export can finish immediately
    if find_spec("streamlit") is None:
        print("streamlit is not installed; install requirements and run with --open-ui again")
        return

    project_root = Path(__file__).resolve().parents[1]
    app_path = (project_root / streamlit_app).resolve()
    command = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    if streamlit_port is not None:
        command.extend(["--server.port", str(streamlit_port)])

    process = subprocess.Popen(command, cwd=str(project_root))
    print("Streamlit launch requested")
    print("-" * 40)
    print(f"app: {app_path}")
    if streamlit_port is not None:
        print(f"port: {streamlit_port}")
    print(f"pid: {process.pid}")


if __name__ == "__main__":
    main()

