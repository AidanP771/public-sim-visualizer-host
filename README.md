# SimPy Case Study Project (COIS 4470H)

## Overview
This repository contains a hospital triage case study built with SimPy.
It includes:

- a baseline FIFO model
- two extensions (multiple nurses and non-preemptive priority)
- experiment and scenario runners
- csv export utilities
- plotting tools for report-ready figures
- web-based queue visualizer (bonus for the fun of it)

## Team Members
- Aidan Morbi
- Mariam Merza

## Project Structure

```text
/src                  simulation code and entry scripts
/src/models           baseline and extension model definitions
/src/sim              shared metrics and event logging utilities
/src/experiments      experiment runner, scenarios, export, and plots
/src/visualization    replay trace loader, engine, and streamlit app
/scripts              helper launch scripts for replay workflow
/data                 generated csv outputs
/data/replays         sample and generated replay json traces
/results              generated plot images
/docs                 project documentation
README.md
requirements.txt
```

## System Description
This project models a simplified hospital treatment system with triage-aware patients.

- single queue
- single service stage
- one or more nurses as service resources
- infinite waiting room capacity

### Arrival and Triage
- arrivals follow an exponential interarrival distribution
- each patient is classified immediately at arrival as `green`, `yellow`, or `red`
- triage is instant classification only, not a separate process and not a separate queue

### Service and Queueing
- service times follow an exponential distribution
- baseline model uses FIFO queueing
- priority extension uses a non-preemptive priority queue with:
  - `red -> 0`
  - `yellow -> 1`
  - `green -> 2`
- lower numeric value means higher priority
- non-preemptive means treatment in progress is never interrupted

## Features
### Baseline
- FIFO hospital queue simulation (`src/models/hospital_fifo.py`)
- configurable nurse count (`num_nurses`)
- per-patient event logging (`arrival`, `service_start`, `departure`)

### Extensions
- extension 1: multiple nurses (resource capacity > 1)
- extension 2: non-preemptive priority queue (`simpy.PriorityResource`)

### Experiment and Results Support
- multi-replication experiment runner with deterministic seed control
- official scenario definitions for report experiments
- per-run and aggregated csv export
- plotting tool for summary graphs

### Replay Visualization Support
- optional replay json export path for visualized runs
- replay engine that applies one event at a time from a saved trace
- streamlit visualizer with play, pause, next step, reset, and speed control
- live queue/server/completed panels plus a matplotlib side chart

## Experiments
The repo includes official scenarios for:

- nurse count comparison (1, 2, 3 nurses) for FIFO and Priority
- load comparison with one nurse across multiple mean interarrival values
- direct FIFO vs Priority comparison under fixed settings

Each scenario is executed with multiple independent random sequences (replications).

## Results
Generated outputs include:

- per-run csv files in `data/`
- aggregated scenario summary csv files in `data/`
- report-friendly graphs in `results/`

The plot set currently includes:

- average wait vs nurses
- average system time vs nurses
- utilization vs nurses
- priority wait by triage across one-nurse load scenarios

## Theory Validation Support
The generated outputs support comparison with queueing theory expectations, including:

- M/M/1 style behavior under single nurse conditions
- M/M/c style behavior with multiple nurses
- impact of non-preemptive priority on triage class waiting times

## How to Run
### Setup
```bash
pip install -r requirements.txt
```

### Scripts
```bash
python src/main.py
```
quick FIFO vs Priority comparison for nurse counts 1, 2, 3

```bash
python src/run_experiment_demo.py
```
small replication demo plus demo csv export

```bash
python src/run_official_scenarios.py
```
runs all official scenarios and exports final csv outputs

```bash
python src/experiments/plots.py
```
generates graphs from official summary csv into `results/`

```bash
python src/run_replay_demo.py
```
runs one demo simulation and exports a replay trace json

```bash
python src/run_replay_and_open.py --open-ui
```
runs one replay export and opens streamlit in one command

```bash
streamlit run src/visualization/streamlit_app.py
```
launches the replay visualizer ui

The visualizer includes built-in demo presets backed by committed traces:
- `data/replays/demo_priority_1_nurse.json`
- `data/replays/demo_priority_2_nurses.json`
- `data/replays/demo_priority_3_nurses.json`

```bash
scripts\run_replay_visualizer.bat
```
windows helper script that runs one replay export and opens streamlit

## Recommended Workflow
1. run official scenarios:
   - `python src/run_official_scenarios.py`
2. generate plots:
   - `python src/experiments/plots.py`
3. use generated csv files and plots in the report

Replay workflow is separate from official csv/report generation:
1. export a replay trace:
   - `python src/run_replay_demo.py`
2. launch the visualizer:
   - `streamlit run src/visualization/streamlit_app.py`
3. load a json trace from `data/replays/` or upload one in the ui

One-command replay workflow:
1. run:
   - `python src/run_replay_and_open.py --open-ui`
2. or on windows:
   - `scripts\run_replay_visualizer.bat`
3. edit parameters directly in the `.bat` file if you want fixed local defaults
4. in the `.bat` file, leave `SEED` blank to omit `--seed`, or set a number for deterministic replay

## Repository Hygiene Notes
- `data/` contains generated csv outputs
- `results/` contains generated plot images
- both folders can be regenerated by running the scripts above

## Documentation
- graph usage and customization guide: `docs/graph_guide.md`
- replay visualizer guide: `docs/replay_visualizer.md`
- project brief: `docs/4470H_W26_Project.pdf`

## Report Link
Report artifacts are maintained outside this repository and submitted separately. They can be found at `{link to google doc}`
