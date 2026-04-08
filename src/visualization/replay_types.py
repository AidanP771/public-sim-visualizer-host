from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# define shared replay data structures used by exporter, loader, engine, and ui
# this module keeps the json schema explicit and easy to extend over time

# bump this when the persisted replay format changes in a breaking way
TRACE_VERSION = 1
# list known event names so validation and tooling can share one source
KNOWN_EVENT_TYPES = {
    "arrival",
    "queue_enter",
    "queue_leave",
    "service_start",
    "service_end",
    "departure",
}


@dataclass
class ReplayMetadata:
    # store run-level context that does not change across events
    # fields here describe how to interpret one replay trace file
    trace_version: int = TRACE_VERSION
    scenario_name: str = "unnamed_scenario"
    run_id: str = "run_0"
    model: str = "unknown"
    seed: int | None = None
    sim_end_time: float = 0.0
    num_nurses: int = 1
    arrival_mean: float | None = None
    service_mean: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReplayMetadata":
        # parse metadata from raw json and preserve unknown keys in extra
        # input is a dict from json, output is a normalized dataclass instance
        known_fields = {
            "trace_version",
            "scenario_name",
            "run_id",
            "model",
            "seed",
            "sim_end_time",
            "num_nurses",
            "arrival_mean",
            "service_mean",
        }
        # keep forward-compatible fields so new writers do not break old readers
        extra = {key: val for key, val in value.items() if key not in known_fields}
        return cls(
            trace_version=int(value.get("trace_version", TRACE_VERSION)),
            scenario_name=str(value.get("scenario_name", "unnamed_scenario")),
            run_id=str(value.get("run_id", "run_0")),
            model=str(value.get("model", "unknown")),
            seed=value.get("seed"),
            sim_end_time=float(value.get("sim_end_time", 0.0)),
            num_nurses=max(1, int(value.get("num_nurses", 1))),
            arrival_mean=_optional_float(value.get("arrival_mean")),
            service_mean=_optional_float(value.get("service_mean")),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        # serialize metadata to a json-safe dict and merge extra fields
        # this function has no side effects beyond creating payload
        payload = {
            "trace_version": self.trace_version,
            "scenario_name": self.scenario_name,
            "run_id": self.run_id,
            "model": self.model,
            "seed": self.seed,
            "sim_end_time": self.sim_end_time,
            "num_nurses": self.num_nurses,
            "arrival_mean": self.arrival_mean,
            "service_mean": self.service_mean,
        }
        payload.update(self.extra)
        return payload


@dataclass
class ReplayEvent:
    # represent one ordered replay event after schema normalization
    # hints are optional snapshots that help debugging and future visual layers
    i: int
    t: float
    type: str
    patient_id: str | None = None
    triage: str | None = None
    server_id: int | None = None
    queue_length_hint: int | None = None
    in_service_hint: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any], fallback_index: int) -> "ReplayEvent":
        # parse one raw event dict into a strongly typed event object
        # fallback_index is used when source data does not provide an id
        known_fields = {
            "i",
            "t",
            "time",
            "event_id",
            "type",
            "patient_id",
            "triage",
            "server_id",
            "queue_length_hint",
            "queue_length",
            "in_service_hint",
            "in_service",
        }
        # preserve unrecognized event payload keys so downstream code can opt in
        extra = {key: val for key, val in value.items() if key not in known_fields}
        event_type = str(value.get("type", "")).strip()
        if not event_type:
            raise ValueError("event type is required")

        return cls(
            i=int(value.get("i", value.get("event_id", fallback_index))),
            t=float(value.get("t", value.get("time", 0.0))),
            type=event_type,
            patient_id=_optional_str(value.get("patient_id")),
            triage=_optional_str(value.get("triage")),
            server_id=_optional_int(value.get("server_id")),
            queue_length_hint=_optional_int(
                value.get("queue_length_hint", value.get("queue_length"))
            ),
            in_service_hint=_optional_int(
                value.get("in_service_hint", value.get("in_service"))
            ),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        # serialize one event and omit optional keys when values are missing
        # compact output makes traces easier to inspect manually
        payload = {
            "i": self.i,
            "t": self.t,
            "type": self.type,
        }
        if self.patient_id is not None:
            payload["patient_id"] = self.patient_id
        if self.triage is not None:
            payload["triage"] = self.triage
        if self.server_id is not None:
            payload["server_id"] = self.server_id
        if self.queue_length_hint is not None:
            payload["queue_length_hint"] = self.queue_length_hint
        if self.in_service_hint is not None:
            payload["in_service_hint"] = self.in_service_hint
        payload.update(self.extra)
        return payload


@dataclass
class ReplayTrace:
    # group immutable run metadata with the ordered event sequence
    # this is the in-memory representation of one replay json file
    metadata: ReplayMetadata
    events: list[ReplayEvent]

    def to_dict(self) -> dict[str, Any]:
        # convert the full trace object to json-ready nested dictionaries
        return {
            "metadata": self.metadata.to_dict(),
            "events": [event.to_dict() for event in self.events],
        }


def _optional_str(value: Any) -> str | None:
    # coerce optional string-like values and normalize blank strings to none
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _optional_float(value: Any) -> float | None:
    # coerce optional numeric value to float while preserving missing values
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    # coerce optional numeric value to int while preserving missing values
    if value is None:
        return None
    return int(value)
