@echo off
setlocal

rem replay run settings
set MODEL=priority
set SIM_TIME=400
set ARRIVAL_MEAN=15
set SERVICE_MEAN=10
set NUM_NURSES=3
set SEED=
set SCENARIO_NAME=demo_lambda_15_mu_10_nurses_3
set RUN_ID=run_01
set OUTPUT_PATH=data/replays/demo_lambda_15_mu_10_nurses_3.json
set STREAMLIT_PORT=

set SEED_ARG=
if not "%SEED%"=="" set SEED_ARG=--seed %SEED%

set PORT_ARG=
if not "%STREAMLIT_PORT%"=="" set PORT_ARG=--streamlit-port %STREAMLIT_PORT%

set PYTHON_EXE=
if exist ".venv\Scripts\python.exe" set PYTHON_EXE=.venv\Scripts\python.exe
if "%PYTHON_EXE%"=="" set PYTHON_EXE=python

%PYTHON_EXE% src\run_replay_and_open.py --open-ui --model %MODEL% --sim-time %SIM_TIME% --arrival-mean %ARRIVAL_MEAN% --service-mean %SERVICE_MEAN% --num-nurses %NUM_NURSES% %SEED_ARG% --scenario-name %SCENARIO_NAME% --run-id %RUN_ID% --output %OUTPUT_PATH% %PORT_ARG%

endlocal
