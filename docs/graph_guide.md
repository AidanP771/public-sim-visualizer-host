# graph guide

## what this tool does

The plotting tool reads the exported official scenario summary csv and generates a small set of report-ready png graphs.

Script:

- `src/experiments/plots.py`

## default input csv

When no input path is provided, the script checks:

1. `data/official_experiment_summary.csv`
2. `data/official_scenarios_demo_summary.csv` (fallback)

## output folder

Graphs are saved to:

- `results/`

If the folder does not exist, the script creates it.

## how to run

From project root:

```powershell
.\.venv\Scripts\python.exe src\experiments\plots.py
```

This builds the default plot set from `create_official_summary_plots(...)`.

Optional custom paths:

```powershell
.\.venv\Scripts\python.exe src\experiments\plots.py --summary-csv data\official_experiment_summary.csv --results-dir results
```

## generate a selected subset by name

Use `--plots` with a comma-separated list:

```powershell
.\.venv\Scripts\python.exe src\experiments\plots.py --plots average_wait_vs_nurses,utilization_vs_nurses
```

The script validates names and only saves the requested graphs.

## available plot names

- `average_wait_vs_nurses`
- `average_system_time_vs_nurses`
- `utilization_vs_nurses`
- `priority_wait_by_triage_vs_arrival_mean`

## generated demo graphs

The script currently generates:

1. `average_wait_vs_nurses.png`
2. `average_system_time_vs_nurses.png`
3. `utilization_vs_nurses.png`
4. `priority_wait_by_triage_vs_arrival_mean.png`

## how to add or modify a graph

Use one of the existing plot helpers as a template.

medium control workflow:

1. copy an existing helper and rename it
2. change the metric fields labels and output filename
3. register it in `PLOT_BUILDERS` in `src/experiments/plots.py`
4. call it by name with `make_plot_set([...])` or pass the name in `--plots`

Helper references:

- `plot_model_metric_vs_nurses(...)`
- `plot_priority_wait_by_triage_vs_load(...)`
- `make_plot_set(...)`
