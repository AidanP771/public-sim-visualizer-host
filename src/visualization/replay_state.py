from __future__ import annotations

from dataclasses import dataclass, field

from visualization.replay_types import ReplayEvent

# define mutable replay state containers used while applying events in order
# the engine mutates these structures to reconstruct queue and server snapshots

@dataclass
class PatientReplayState:
    # keep all patient timestamps in one place so metrics are derived from events
    # this avoids recomputation drift when replay is rebuilt from any index
    patient_id: str
    triage: str = "unknown"
    arrival_time: float | None = None
    service_start_time: float | None = None
    service_end_time: float | None = None
    departure_time: float | None = None
    assigned_server_id: int | None = None
    busy_accounted: bool = False

    @property
    def wait_time(self) -> float | None:
        # wait is undefined until service has actually started for this patient
        if self.arrival_time is None or self.service_start_time is None:
            return None
        return self.service_start_time - self.arrival_time

    @property
    def system_time(self) -> float | None:
        # system time is only final once departure has been observed
        if self.arrival_time is None or self.departure_time is None:
            return None
        return self.departure_time - self.arrival_time


@dataclass
class ReplayState:
    # represent one deterministic system snapshot at the current event cursor
    # sets like arrived_ids and served_ids guard against double-counting metrics
    num_nurses: int
    clock: float = 0.0
    waiting_queue: list[str] = field(default_factory=list)
    active_servers: dict[int, str] = field(default_factory=dict)
    completed_patients: list[str] = field(default_factory=list)
    patients: dict[str, PatientReplayState] = field(default_factory=dict)
    total_arrived: int = 0
    total_served: int = 0
    busy_time: float = 0.0
    wait_sum: float = 0.0
    recent_events: list[ReplayEvent] = field(default_factory=list)
    history: list[dict[str, float]] = field(default_factory=list)
    arrived_ids: set[str] = field(default_factory=set)
    served_ids: set[str] = field(default_factory=set)

    def reset(self) -> None:
        # full reset makes replay rebuilds deterministic from a known baseline
        # the initial history point ensures charts always start at time zero
        self.clock = 0.0
        self.waiting_queue.clear()
        self.active_servers.clear()
        self.completed_patients.clear()
        self.patients.clear()
        self.total_arrived = 0
        self.total_served = 0
        self.busy_time = 0.0
        self.wait_sum = 0.0
        self.recent_events.clear()
        self.history.clear()
        self.arrived_ids.clear()
        self.served_ids.clear()
        self.record_history()

    def ensure_patient(self, patient_id: str, triage: str | None = None) -> PatientReplayState:
        # centralize patient creation so all event paths mutate the same object
        # triage can be backfilled because some traces provide it intermittently
        if patient_id not in self.patients:
            self.patients[patient_id] = PatientReplayState(patient_id=patient_id)
        patient = self.patients[patient_id]
        if triage:
            patient.triage = triage
        return patient

    def append_recent_event(self, event: ReplayEvent, max_events: int = 8) -> None:
        # keep recent events bounded so ui history stays readable and stable
        # trimming prevents unbounded growth during long replays
        self.recent_events.append(event)
        if len(self.recent_events) > max_events:
            self.recent_events = self.recent_events[-max_events:]

    def record_history(self) -> None:
        # capture a snapshot after each state transition for time-series charts
        # sampling at each step keeps chart points aligned with replay progression
        self.history.append(
            {
                "t": self.clock,
                "queue_length": float(self.queue_length),
                "in_service": float(len(self.active_servers)),
                "completed": float(self.total_served),
                "in_system": float(self.num_in_system),
            }
        )

    @property
    def queue_length(self) -> int:
        # expose queue length once so all views use identical logic
        return len(self.waiting_queue)

    @property
    def num_in_system(self) -> int:
        # system size is defined as waiting plus currently in service
        return len(self.waiting_queue) + len(self.active_servers)

    @property
    def running_average_wait(self) -> float:
        # use incremental sum to keep per-step updates constant time
        if self.total_served <= 0:
            return 0.0
        return self.wait_sum / self.total_served
