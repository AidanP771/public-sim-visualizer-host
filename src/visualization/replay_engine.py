from __future__ import annotations

from visualization.replay_state import ReplayState
from visualization.replay_types import ReplayEvent
from visualization.replay_types import ReplayTrace

# apply replay events deterministically and maintain a reconstructed system state
# this engine is the only component that mutates replay state during playback

class ReplayEngine:
    # coordinate all replay progression so state changes happen in one place
    # current_event_index tracks the next unapplied event for deterministic stepping
    def __init__(self, trace: ReplayTrace):
        # seed state with metadata capacity so server assignments have fixed bounds
        self.trace = trace
        self.state = ReplayState(num_nurses=trace.metadata.num_nurses)
        self.current_event_index = 0
        self.state.reset()

    @property
    def total_events(self) -> int:
        # expose fixed event count for progress indicators and index clamping
        return len(self.trace.events)

    @property
    def has_events(self) -> bool:
        # quick guard for empty-trace ui states
        return self.total_events > 0

    def has_next_event(self) -> bool:
        # stepping is allowed while cursor has not reached the event list end
        return self.current_event_index < self.total_events

    def reset(self) -> None:
        # reset supports replay restart and rebuild without reloading from disk
        self.current_event_index = 0
        self.state.reset()

    def apply_next_event(self) -> ReplayEvent | None:
        # apply exactly one transition so ui controls can step deterministically
        # returning none at end keeps callers from reading past trace boundaries
        if not self.has_next_event():
            return None

        event = self.trace.events[self.current_event_index]
        self._apply_event(event)
        self.current_event_index += 1
        return event

    def rebuild_to_index(self, target_index: int) -> None:
        # replay from zero to cursor instead of seeking mutable state in place
        # this guarantees the same state for the same index on every rebuild
        bounded_index = max(0, min(target_index, self.total_events))
        self.reset()
        for _ in range(bounded_index):
            self.apply_next_event()

    def _apply_event(self, event: ReplayEvent) -> None:
        # apply one event as an atomic state transition at the current clock
        # tolerant updates allow traces with redundant queue markers
        self.state.clock = event.t
        event_type = event.type
        patient_id = event.patient_id
        triage = event.triage
        patient = None

        if patient_id is not None:
            patient = self.state.ensure_patient(patient_id, triage=triage)

        if event_type == "arrival" and patient_id is not None:
            # arrival initializes patient timeline and increments once per id
            # id guard prevents accidental double-counting from noisy traces
            if patient.arrival_time is None:
                patient.arrival_time = event.t
            if patient_id not in self.state.arrived_ids:
                self.state.arrived_ids.add(patient_id)
                self.state.total_arrived += 1

        elif event_type == "queue_enter" and patient_id is not None:
            # queue enter is idempotent so duplicate markers do not corrupt order
            if patient_id not in self.state.waiting_queue:
                self.state.waiting_queue.append(patient_id)

        elif event_type == "queue_leave" and patient_id is not None:
            # queue leave is best-effort because some traces may omit queue enter
            if patient_id in self.state.waiting_queue:
                self.state.waiting_queue.remove(patient_id)

        elif event_type == "service_start" and patient_id is not None:
            # service start moves patient from waiting to active treatment
            if patient_id in self.state.waiting_queue:
                self.state.waiting_queue.remove(patient_id)

            # deterministic server resolution keeps replay consistent across rebuilds
            server_id = self._resolve_server_id(event, patient_id)
            self.state.active_servers[server_id] = patient_id
            patient.assigned_server_id = server_id

            if patient.service_start_time is None:
                patient.service_start_time = event.t

        elif event_type == "service_end" and patient_id is not None:
            # service end closes busy-time accounting even before departure is processed
            if patient.service_end_time is None:
                patient.service_end_time = event.t
            self._account_busy_time(patient, event.t)

        elif event_type == "departure" and patient_id is not None:
            # departure finalizes patient lifecycle and releases server occupancy
            if patient_id in self.state.waiting_queue:
                self.state.waiting_queue.remove(patient_id)

            server_id = self._resolve_server_id(event, patient_id, fallback_assign=False)
            if server_id is not None:
                self.state.active_servers.pop(server_id, None)
                patient.assigned_server_id = server_id

            if patient.service_end_time is None:
                patient.service_end_time = event.t
            self._account_busy_time(patient, event.t)

            if patient.departure_time is None:
                patient.departure_time = event.t

            if patient_id not in self.state.served_ids:
                # served count is guarded to keep averages stable on duplicate departures
                self.state.served_ids.add(patient_id)
                self.state.total_served += 1
                self.state.completed_patients.append(patient_id)
                wait_time = patient.wait_time
                if wait_time is not None:
                    self.state.wait_sum += max(0.0, wait_time)

        # snapshot after every event so chart and event list stay in lockstep
        self.state.append_recent_event(event)
        self.state.record_history()

    def _resolve_server_id(
        self,
        event: ReplayEvent,
        patient_id: str,
        fallback_assign: bool = True,
    ) -> int | None:
        # prefer explicit ids, then prior assignment, then active lookup
        # fallback is only used on service start to avoid inventing servers on departure
        if event.server_id is not None:
            return event.server_id

        patient = self.state.patients.get(patient_id)
        if patient is not None and patient.assigned_server_id is not None:
            return patient.assigned_server_id

        for server_id, active_patient_id in self.state.active_servers.items():
            if active_patient_id == patient_id:
                return server_id

        if not fallback_assign:
            return None

        # choosing the lowest free index keeps assignment deterministic
        for server_id in range(self.trace.metadata.num_nurses):
            if server_id not in self.state.active_servers:
                return server_id
        return 0

    def _account_busy_time(self, patient, end_time: float) -> None:
        # busy time is counted once because traces may include both end and departure
        # this preserves utilization-related metrics when replaying expanded traces
        if patient.busy_accounted:
            return
        if patient.service_start_time is None:
            return
        duration = max(0.0, end_time - patient.service_start_time)
        self.state.busy_time += duration
        patient.busy_accounted = True
