import random
import simpy

from sim.event_log import EventLog
from sim.metrics import RunStats

# triage classes and sampling probabilities
TRIAGE_LEVELS = ["green", "yellow", "red"]
TRIAGE_PROBS = [0.6, 0.3, 0.1]

# lower number means higher priority in simpy
TRIAGE_PRIORITY = {
    "red": 0,
    "yellow": 1,
    "green": 2,
}


def sample_triage():
    return random.choices(TRIAGE_LEVELS, TRIAGE_PROBS)[0]


def exponential(mean):
    return random.expovariate(1.0 / mean)


class Patient:
    def __init__(self, patient_id, arrival_time, triage, service_time, priority):
        self.id = patient_id
        self.arrival_time = arrival_time
        self.triage = triage
        self.priority = priority
        self.service_time = service_time

        self.service_start_time = None
        self.departure_time = None


def run_hospital_priority_simulation(
    sim_time,
    arrival_mean,
    service_mean,
    num_nurses=1,
    seed=None,
):
    if seed is not None:
        random.seed(seed)

    if num_nurses <= 0:
        raise ValueError("num_nurses must be at least 1")

    env = simpy.Environment()
    # use priorityresource for non preemptive priority ordering
    server = simpy.PriorityResource(env, capacity=num_nurses)

    stats = RunStats()
    log = EventLog()
    patients = []

    def patient_process(env, patient_id):
        # assign triage and numeric priority at arrival
        arrival_time = env.now
        triage = sample_triage()
        priority = TRIAGE_PRIORITY[triage]
        service_time = exponential(service_mean)

        patient = Patient(
            patient_id=patient_id,
            arrival_time=arrival_time,
            triage=triage,
            service_time=service_time,
            priority=priority,
        )
        patients.append(patient)

        stats.record_arrival()

        # request with triage based priority red 0 yellow 1 green 2
        request = server.request(priority=patient.priority)
        stats.record_queue_length(len(server.queue))
        log.log(
            env.now,
            "arrival",
            patient_id=patient.id,
            triage=patient.triage,
            priority=patient.priority,
            queue_length=len(server.queue),
            in_service=len(server.users),
        )

        yield request

        patient.service_start_time = env.now
        wait_time = patient.service_start_time - patient.arrival_time

        log.log(
            env.now,
            "service_start",
            patient_id=patient.id,
            triage=patient.triage,
            priority=patient.priority,
            queue_length=len(server.queue),
            in_service=len(server.users),
        )

        yield env.timeout(patient.service_time)

        patient.departure_time = env.now
        system_time = patient.departure_time - patient.arrival_time

        stats.record_service_completion(
            triage=patient.triage,
            wait_time=wait_time,
            system_time=system_time,
            service_time=patient.service_time,
        )

        server.release(request)
        log.log(
            env.now,
            "departure",
            patient_id=patient.id,
            triage=patient.triage,
            priority=patient.priority,
            queue_length=len(server.queue),
            in_service=len(server.users),
        )

    def arrival_process(env):
        patient_id = 0
        while True:
            interarrival = exponential(arrival_mean)
            yield env.timeout(interarrival)

            env.process(patient_process(env, patient_id))
            patient_id += 1

    env.process(arrival_process(env))
    env.run(until=sim_time)

    return {
        "stats": stats,
        "patients": patients,
        "events": log.get_events(),
    }
