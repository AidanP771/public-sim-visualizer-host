from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from visualization.replay_types import ReplayEvent
from visualization.replay_types import ReplayMetadata
from visualization.replay_types import ReplayTrace
from visualization.replay_types import TRACE_VERSION

# load replay traces from disk or text and normalize them for the replay engine
# this module is the boundary between raw json payloads and typed replay objects

def load_replay_trace(path: str | Path) -> ReplayTrace:
    # read a replay json file from path and return a validated trace object
    # input is a file path and output is a parsed replay trace
    replay_path = Path(path)
    with replay_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return parse_replay_trace(data)


def load_replay_trace_from_text(payload: str) -> ReplayTrace:
    # parse replay json content already loaded into memory as text
    # useful for streamlit uploads where file bytes come from the browser
    data = json.loads(payload)
    return parse_replay_trace(data)


def parse_replay_trace(data: dict[str, Any]) -> ReplayTrace:
    # normalize a generic dict into metadata plus ordered replay events
    # this keeps backward compatibility with older traces that used top-level version
    metadata_raw = dict(data.get("metadata", {}))
    if "trace_version" not in metadata_raw:
        metadata_raw["trace_version"] = data.get("trace_version", TRACE_VERSION)
    metadata = ReplayMetadata.from_dict(metadata_raw)

    events_raw = data.get("events", [])
    if not isinstance(events_raw, list):
        raise ValueError("events must be a list")

    # parse each event independently so schema errors are isolated per record
    events = [
        ReplayEvent.from_dict(event_data, fallback_index=index)
        for index, event_data in enumerate(events_raw)
    ]
    _validate_event_order(events)
    return ReplayTrace(metadata=metadata, events=events)


def _validate_event_order(events: list[ReplayEvent]) -> None:
    # enforce deterministic replay order by time and event index
    # side effect is raising an error when ordering assumptions are violated
    previous_time = float("-inf")
    previous_index = -1

    for event in events:
        # reject traces where clock moves backward
        if event.t < previous_time:
            raise ValueError("events must be sorted by nondecreasing time")
        # reject traces where same-time events are out of index order
        if event.t == previous_time and event.i < previous_index:
            raise ValueError("event indexes must be nondecreasing for tied times")
        previous_time = event.t
        previous_index = event.i
