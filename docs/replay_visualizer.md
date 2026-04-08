# Replay Visualizer Guide

## Purpose
This replay system is separate from the experiment csv pipeline.

- csv exports in `src/experiments` remain unchanged
- replay uses json traces for visual stepping in streamlit
- the visualizer does not run a live simpy environment

## Generate a replay trace
Run a demo replay export:

```bash
python src/run_replay_demo.py
```

Useful options:

```bash
python src/run_replay_demo.py --model priority --num-nurses 2 --seed 42
python src/run_replay_demo.py --output data/replays/my_trace.json
```

The script writes replay json files into `data/replays/` by default.

## One-command replay workflow
Run simulation export and open streamlit in one command:

```bash
python src/run_replay_and_open.py --open-ui
```

Common options:

```bash
python src/run_replay_and_open.py --open-ui --model fifo --num-nurses 3 --seed 42
python src/run_replay_and_open.py --open-ui --output data/replays/custom_trace.json
python src/run_replay_and_open.py --open-ui --streamlit-port 8502
```

The launcher prints the saved replay json path after export.

## Windows helper script
You can run:

```bat
scripts\run_replay_visualizer.bat
```

Edit the parameter block at the top of that file to set defaults.

- if `SEED` is blank, the script omits `--seed` and uses the model default random behavior
- if `SEED` has a number, that value is passed through for deterministic replay runs

## Launch the visualizer
```bash
streamlit run src/visualization/streamlit_app.py
```

Then load a local trace from `data/replays/` or upload a json trace file.

## Built-in demo presets
The visualizer now supports one-click presets for public demos.

- `demo: 1 nurse` -> `data/replays/demo_priority_1_nurse.json`
- `demo: 2 nurses` -> `data/replays/demo_priority_2_nurses.json`
- `demo: 3 nurses` -> `data/replays/demo_priority_3_nurses.json`

On first load, the app auto-loads the `demo: 2 nurses` preset when the file is present.

To regenerate these demo traces:

```bash
python src/run_replay_demo.py --model priority --num-nurses 1 --seed 101 --scenario-name streamlit_demo --run-id nurses_1 --output data/replays/demo_priority_1_nurse.json
python src/run_replay_demo.py --model priority --num-nurses 2 --seed 102 --scenario-name streamlit_demo --run-id nurses_2 --output data/replays/demo_priority_2_nurses.json
python src/run_replay_demo.py --model priority --num-nurses 3 --seed 103 --scenario-name streamlit_demo --run-id nurses_3 --output data/replays/demo_priority_3_nurses.json
```

## Free hosting on Streamlit Community Cloud
Use this path for a no-cost public URL with full Streamlit functionality.

1. Push this repository to GitHub.
2. Open Streamlit Community Cloud and create a new app from the repo.
3. Set branch to your deployment branch (usually `main`).
4. Set app file path to `src/visualization/streamlit_app.py`.
5. Deploy and validate presets, playback controls, and upload flow.

Notes:

- first load may be slower after inactivity due to free-tier sleeping
- this project uses `requirements.txt`, so package install happens automatically at deploy time

## Supported controls
- play
- pause
- next step
- reset
- speed selector (`0.25x`, `0.5x`, `1x`, `2x`, `4x`)

## Replay displays
- simulation clock and event progress
- queue panel
- nurse panel
- completed panel
- live metrics table
- recent events list
- matplotlib chart for queue length and completed count over time

## Trace schema
Each replay json has:

- `metadata`
  - `scenario_name`
  - `run_id`
  - `seed`
  - `sim_end_time`
  - `num_nurses`
  - `trace_version`
- `events` in ordered replay sequence
  - `t`
  - `type`
  - `patient_id` where relevant
  - `triage` where relevant
  - `server_id` where relevant

## Files
- `src/sim/replay_export.py`
- `src/run_replay_demo.py`
- `src/run_replay_and_open.py`
- `src/visualization/replay_types.py`
- `src/visualization/replay_loader.py`
- `src/visualization/replay_state.py`
- `src/visualization/replay_engine.py`
- `src/visualization/streamlit_app.py`
- `scripts/run_replay_visualizer.bat`
- `data/replays/sample_replay_trace.json`
- `data/replays/demo_priority_1_nurse.json`
- `data/replays/demo_priority_2_nurses.json`
- `data/replays/demo_priority_3_nurses.json`
