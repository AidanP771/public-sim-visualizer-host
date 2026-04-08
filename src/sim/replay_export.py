from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any

from visualization.replay_types import ReplayEvent
from visualization.replay_types import ReplayMetadata
from visualization.replay_types import ReplayTrace
from visualization.replay_types import TRACE_VERSION

# convert simulation event logs into replay json traces for offline visualization
# this module is optional and intentionally separate from csv experiment exports

def build_replay_trace(
    events: list[dict[str, Any]],
    scenario_name: str,
    run_id: str,
    model: str,
    sim_end_time: float,
    num_nurses: int,
    seed: int | None = None,
    arrival_mean: float | None = None,
    service_mean: float | None = None,
) -> ReplayTrace:
    # normalize raw simulation events into a replay-friendly event stream
    # sorting by time and source id guarantees stable expansion across runs
    sorted_events = sorted(
        events,
        key=lambda event: (
            float(event.get("time", event.get("t", 0.0))),
            int(event.get("event_id", 0)),
        ),
    )
    replay_events = _expand_events(sorted_events, num_nurses=num_nurses)

    # include run context so replay files are self-contained for the ui
    metadata = ReplayMetadata(
        trace_version=TRACE_VERSION,
        scenario_name=scenario_name,
        run_id=run_id,
        model=model,
        seed=seed,
        sim_end_time=sim_end_time,
        num_nurses=num_nurses,
        arrival_mean=arrival_mean,
        service_mean=service_mean,
        extra={"created_utc": datetime.now(timezone.utc).isoformat()},
    )
    return ReplayTrace(metadata=metadata, events=replay_events)


def write_replay_trace(trace: ReplayTrace, output_path: str | Path) -> Path:
    # write trace json and ensure target folder exists for first-time exports
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(trace.to_dict(), handle, indent=2)
    return path


def export_replay_trace(
    result: dict[str, Any],
    scenario_name: str,
    run_id: str,
    model: str,
    sim_end_time: float,
    num_nurses: int,
    seed: int | None = None,
    arrival_mean: float | None = None,
    service_mean: float | None = None,
    output_path: str | Path | None = None,
) -> Path:
    # keep caller api small by combining trace build and file write in one call
    # default path keeps replay artifacts out of csv reporting directories
    trace = build_replay_trace(
        events=result.get("events", []),
        scenario_name=scenario_name,
        run_id=run_id,
        model=model,
        sim_end_time=sim_end_time,
        num_nurses=num_nurses,
        seed=seed,
        arrival_mean=arrival_mean,
        service_mean=service_mean,
    )

    if output_path is None:
        output_path = (
            _default_replay_dir() / f"{scenario_name}_{run_id}_replay.json"
        )
    return write_replay_trace(trace, output_path)


def _expand_events(
    raw_events: list[dict[str, Any]],
    num_nurses: int,
) -> list[ReplayEvent]:
    # expand compact model logs into explicit state transitions for step replay
    # shadow queue and server maps encode assumptions that source logs omit
    replay_events: list[ReplayEvent] = []
    waiting_queue: list[str] = []
    active_servers: dict[int, str] = {}
    patient_server: dict[str, int] = {}
    completed_ids: set[str] = set()

    next_index = 0

    def append_event(
        t: float,
        event_type: str,
        patient_id: str | None = None,
        triage: str | None = None,
        server_id: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        # attach local snapshot hints so ui can debug state mismatches if needed
        # monotonically increasing index keeps tie-time ordering deterministic
        nonlocal next_index
        payload = extra.copy() if extra is not None else {}
        replay_events.append(
            ReplayEvent(
                i=next_index,
                t=t,
                type=event_type,
                patient_id=patient_id,
                triage=triage,
                server_id=server_id,
                queue_length_hint=len(waiting_queue),
                in_service_hint=len(active_servers),
                extra=payload,
            )
        )
        next_index += 1

    for raw_event in raw_events:
        t = float(raw_event.get("time", raw_event.get("t", 0.0)))
        event_type = str(raw_event.get("type", ""))
        patient_id = _optional_patient_id(raw_event.get("patient_id"))
        triage = _optional_triage(raw_event.get("triage"))
        extra = _event_extra(raw_event)

        if event_type == "arrival":
            # split arrival and queue admission so replay can show both transitions
            append_event(
                t=t,
                event_type="arrival",
                patient_id=patient_id,
                triage=triage,
                extra=extra,
            )
            if patient_id is not None and patient_id not in completed_ids:
                if patient_id not in waiting_queue and patient_id not in patient_server:
                    waiting_queue.append(patient_id)
                append_event(
                    t=t,
                    event_type="queue_enter",
                    patient_id=patient_id,
                    triage=triage,
                )

        elif event_type == "service_start":
            # remove patient from waiting before assigning service to mirror state flow
            if patient_id is not None and patient_id in waiting_queue:
                waiting_queue.remove(patient_id)
            if patient_id is not None:
                append_event(
                    t=t,
                    event_type="queue_leave",
                    patient_id=patient_id,
                    triage=triage,
                )

                server_id = patient_server.get(patient_id)
                if server_id is None:
                    # choose lowest free server to keep inferred ids reproducible
                    server_id = _first_free_server(active_servers, num_nurses)
                    patient_server[patient_id] = server_id
                active_servers[server_id] = patient_id

                append_event(
                    t=t,
                    event_type="service_start",
                    patient_id=patient_id,
                    triage=triage,
                    server_id=server_id,
                    extra=extra,
                )

        elif event_type == "departure":
            # emit service_end then departure so engine can close service and lifecycle separately
            server_id = patient_server.get(patient_id) if patient_id is not None else None
            if server_id is None and patient_id is not None:
                server_id = _find_server_by_patient(active_servers, patient_id)
            if patient_id is not None and patient_id in waiting_queue:
                waiting_queue.remove(patient_id)

            append_event(
                t=t,
                event_type="service_end",
                patient_id=patient_id,
                triage=triage,
                server_id=server_id,
            )

            if server_id is not None:
                active_servers.pop(server_id, None)

            append_event(
                t=t,
                event_type="departure",
                patient_id=patient_id,
                triage=triage,
                server_id=server_id,
                extra=extra,
            )

            if patient_id is not None:
                completed_ids.add(patient_id)
                patient_server.pop(patient_id, None)

        else:
            # carry unknown events through so newer producers do not break old viewers
            append_event(
                t=t,
                event_type=event_type,
                patient_id=patient_id,
                triage=triage,
                extra=extra,
            )

    return replay_events


def _event_extra(raw_event: dict[str, Any]) -> dict[str, Any]:
    # preserve non-core fields so future replay views can opt into richer data
    excluded_keys = {
        "event_id",
        "time",
        "t",
        "type",
        "patient_id",
        "triage",
        "queue_length",
        "in_service",
    }
    return {key: value for key, value in raw_event.items() if key not in excluded_keys}


def _find_server_by_patient(active_servers: dict[int, str], patient_id: str) -> int | None:
    # recover server id from active map when explicit mapping is missing
    for server_id, active_patient_id in active_servers.items():
        if active_patient_id == patient_id:
            return server_id
    return None


def _first_free_server(active_servers: dict[int, str], num_nurses: int) -> int:
    # lowest-index policy makes inferred assignment deterministic during rebuild
    for server_id in range(num_nurses):
        if server_id not in active_servers:
            return server_id
    return 0


def _optional_patient_id(value: Any) -> str | None:
    # coerce ids to string so dict lookups remain stable across mixed input types
    if value is None:
        return None
    return str(value)


def _optional_triage(value: Any) -> str | None:
    # normalize triage for consistent badge and metric grouping downstream
    if value is None:
        return None
    return str(value)


def _default_replay_dir() -> Path:
    # keep replay output in a dedicated folder separate from summary csv files
    return Path(__file__).resolve().parents[2] / "data" / "replays"
