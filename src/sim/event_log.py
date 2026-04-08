class EventLog:
    def __init__(self):
        # store all sim events in timestamp order
        self.events = []

        # simple running event id for tracking, debugging, and replay
        self._next_event_id = 0

    def log(self, time, event_type, patient_id=None, triage=None, **extra):
        # create one event record with common fields
        event = {
            'event_id': self._next_event_id,
            'time': time,
            'type': event_type,
            'patient_id': patient_id,
            'triage': triage,
        }

        # merge in any extra fields provided e.g. queue length, nurse id, etc
        event.update(extra)

        # append event to timeline
        self.events.append(event)

        # increment id for next event
        self._next_event_id += 1

    def get_events(self):
        # return all events in order
        return self.events