from collections import defaultdict

# run stats class to track various metrics during the simulation
# here for global access across the codebase
class RunStats:
    def __init__(self):
        # total num of patients who arrived
        self.total_arrived = 0

        # total num of patients who completed service
        self.total_served = 0

        # raw timing data for overall system metrics
        self.wait_times = []
        self.system_times = []
        self.service_times = []

        # total busy time accumulated by all nurses
        self.busy_time = 0.0

        # track the largest queue length observed during the run
        self.max_queue_length = 0

        # store per-triage timing data
        self.wait_times_by_triage = defaultdict(list)
        self.system_times_by_triage = defaultdict(list)
        self.service_times_by_triage = defaultdict(list)

        # count how many patients were served in each triage class
        self.served_by_triage = defaultdict(int)

    # increment total arrivals
    def record_arrival(self):
        self.total_arrived += 1

    # update the max queue length if current length exceeds it
    def record_queue_length(self, queue_length):
        if queue_length > self.max_queue_length:
            self.max_queue_length = queue_length
    

    def record_service_completion(self, triage, wait_time, system_time, service_time):
        # increment total completed patients
        self.total_served += 1

        # store overall timing data
        self.wait_times.append(wait_time)
        self.system_times.append(system_time)
        self.service_times.append(service_time)

        # add to total busy time
        self.busy_time += service_time

        # store per-triage timing data
        self.wait_times_by_triage[triage].append(wait_time)
        self.system_times_by_triage[triage].append(system_time)
        self.service_times_by_triage[triage].append(service_time)

        # increment per triage served count
        self.served_by_triage[triage] += 1

    # calculate average wait time
    def average_wait(self):
        # return avg wait time, or 0 if no patients served
        if not self.wait_times:
            return 0.0
        return sum(self.wait_times) / len(self.wait_times)

    # compatibility wrapper for older call sites
    def average_wait_time(self):
        return self.average_wait()

    # calculate average system time
    def average_system_time(self):
        if not self.system_times:
            return 0.0
        return sum(self.system_times) / len(self.system_times)

    # calculate average service time
    def average_service_time(self):
        if not self.service_times:
            return 0.0
        return sum(self.service_times) / len(self.service_times)

    # calculate average wait time by triage
    def average_wait_by_triage(self, triage):
        times = self.wait_times_by_triage[triage]
        if not times:
            return 0.0
        return sum(times) / len(times)

    # compatibility wrapper for older call sites
    def average_wait_time_by_triage(self, triage):
        return self.average_wait_by_triage(triage)

    # calculate average system time by triage
    def average_system_time_by_triage(self, triage):
        values = self.system_times_by_triage[triage]
        if not values:
            return 0.0
        return sum(values) / len(values)

    # calculate average service time by triage
    def average_service_time_by_triage(self, triage):
        values = self.service_times_by_triage[triage]
        if not values:
            return 0.0
        return sum(values) / len(values)

    # calculate nurse utilization
    def utilization(self, sim_time, num_nurses=1):
        # utilization is total busy time divided by total available nurse time
        # with multiple nurses, total available time is sim_time * num_nurses
        if sim_time <= 0 or num_nurses <= 0:
            return 0.0
        return self.busy_time / (sim_time * num_nurses)

    # summary of key metrics for reporting
    def summary(self, sim_time, num_nurses=1):
        return {
            "total_arrived": self.total_arrived,
            "total_served": self.total_served,
            "average_wait": self.average_wait(),
            "average_system_time": self.average_system_time(),
            "average_service_time": self.average_service_time(),
            "utilization": self.utilization(sim_time, num_nurses),
            "max_queue_length": self.max_queue_length,
            "served_by_triage": dict(self.served_by_triage),
        }
