# report notes

## 1. brief project summary
This project simulates a hospital treatment queue with triage-aware patients.  
It models how queue discipline and staffing levels affect wait times, system time, utilization, and fairness across triage classes.

## 2. implemented features
- baseline: single-queue, single-stage FIFO treatment model
- extension 1: multiple nurses (same queue/stage, higher resource capacity)
- extension 2: non-preemptive priority queue (red highest priority, then yellow, then green)
- experiments and reporting support:
  - multi-replication runner with seed control
  - official scenario definitions
  - per-run and aggregated csv export
  - plotting utility for report-ready figures

## 3. key scripts and what they do
- `src/main.py` - quick FIFO vs Priority comparison for nurse counts 1, 2, 3
- `src/run_experiment_demo.py` - small 3-replication demo with csv export
- `src/run_official_scenarios.py` - runs full official scenario set and writes final csv outputs
- `src/experiments/plots.py` - generates graphs from official summary csv into `results/`

## 4. important output files
- official aggregated summary: `data/official_experiment_summary.csv`
- official per-run output: `data/official_experiment_runs.csv`
- generated graph folder: `results/`

## 5. suggested graphs for the report
- `average_wait_vs_nurses.png`  
  use for showing staffing effect on waiting time
- `average_system_time_vs_nurses.png`  
  use for end-to-end patient time impact
- `utilization_vs_nurses.png`  
  use for capacity/efficiency discussion
- `priority_wait_by_triage_vs_arrival_mean.png`  
  use for fairness tradeoff under priority at one nurse across load levels

## 6. key findings and interpretation notes
- increasing nurse count lowers average wait, average system time, and max queue length
- priority scheduling matters most when congestion is higher
- red patients benefit most under priority
- green patients can wait longer under priority when system is busy
- under lighter load, FIFO and priority outcomes move closer together

## 7. theory comparison notes
- compare FIFO one-nurse scenarios to M/M/1-style expectations
- compare FIFO multi-nurse scenarios to M/M/c-style expectations
- discuss expected differences between simulation and theory:
  - finite run length
  - random variation across replications
  - priority rule effects that change class-level waiting behavior

## 8. potential writing workflow
1. start from `data/official_experiment_summary.csv`
2. select final graphs from `results/`
3. write results and scenario-by-scenario analysis
4. add theory comparison discussion
5. finalize conclusions and limitations
