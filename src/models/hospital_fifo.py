import simpy
import random

from sim.metrics import RunStats
from sim.event_log import EventLog

# triage levels used for immediate classification at arrival
TRIAGE_LEVELS = ["green", "yellow", "red"]

# probability distribution for triage classes
TRIAGE_PROBS = [0.6, 0.3, 0.1]

def sample_triage():
    return random.choices(TRIAGE_LEVELS, TRIAGE_PROBS)[0]

def exponential(mean):
    return random.expovariate(1.0 / mean)


# stores per patient timestamps for wait and system time calculations
class Patient:
    def __init__(self, patient_id, arrival_time, triage, service_time):
        self.id = patient_id
        self.arrival_time = arrival_time
        self.triage = triage
        self.service_time = service_time

        self.service_start_time = None
        self.departure_time = None

# single queue single stage fifo treatment model
def run_hospital_fifo_simulation(sim_time, arrival_mean, service_mean, num_nurses=1, seed=None):
    if seed is not None:
        random.seed(seed)

    if num_nurses <= 0:
        raise ValueError("num_nurses must be at least 1")
    
    env = simpy.Environment()
    server = simpy.Resource(env, capacity=num_nurses)

    stats = RunStats()
    log = EventLog()
    patients = []

    def patient_process(env, patient_id):
        # assign triage and service requirement at arrival
        arrival_time = env.now
        triage = sample_triage()
        service_time = exponential(service_mean)

        patient = Patient(patient_id, arrival_time, triage, service_time)
        patients.append(patient)

        stats.record_arrival()

        # create request now so queue length snapshot includes this patient if queued
        request = server.request()
        stats.record_queue_length(len(server.queue))
        log.log(
            env.now,
            "arrival",
            patient.id,
            patient.triage,
            queue_length=len(server.queue),
            in_service=len(server.users),
        )

        yield request  # wait for a nurse

        # service begins
        patient.service_start_time = env.now
        wait_time = patient.service_start_time - patient.arrival_time

        log.log(
            env.now,
            "service_start",
            patient.id,
            patient.triage,
            queue_length=len(server.queue),
            in_service=len(server.users),
        )

        yield env.timeout(patient.service_time)  # treatment time

        # service ends
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
            patient.id,
            patient.triage,
            queue_length=len(server.queue),
            in_service=len(server.users),
        )
        
    # generate arrivals using exponential interarrival times
    def arrival_process(env):
        patient_id = 0
        while True:
            interarrival = exponential(arrival_mean)
            yield env.timeout(interarrival)  # wait for next arrival

            env.process(patient_process(env, patient_id))
            patient_id += 1
    
    env.process(arrival_process(env))
    env.run(until=sim_time)

    return {
        "stats": stats,
        "patients": patients,
        "events": log.get_events()
    }
