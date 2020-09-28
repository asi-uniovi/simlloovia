'''This module defines two classes related to monitoring: SimulationStats and
Monitor.
'''
import time
from typing import List
from dataclasses import dataclass
import statistics
import numpy as np

@dataclass
class SimulationStats():
    """Statics about the simulation"""

    """Number of requests injected"""
    req_injected: int

    """Number of requests processed (not including the lost ones)"""
    req_proc: int

    """Number of peding requests, i.e., still executing when the simulation
    finishes"""
    req_pending: int

    """Number of lost requests, i.e., requests that were not processed"""
    req_lost: int

    """Average response time of the processed requests"""
    avg_resp_time: float

    """Maximum response time of the processed requests"""
    max_resp_time: float

    """Minium response time of the processed requests"""
    min_resp_time: float

    """Median response time of the processed requests"""
    median_resp_time: float

    """90 percentile response time of the processed requests"""
    perc90_resp_time: float

    """95 percentile response time of the processed requests"""
    perc95_resp_time: float

    """Total cost of the VMs"""
    cost: float

    """Average utilization (between 0 and 1) of the VMs"""
    util: float

    """Time used in the simulation"""
    sim_time: float

    """Time used for computing the stats"""
    stats_time: float

    def __repr__(self):
        return (f'Requests: '
                f'Injected: {self.req_injected}. '
                f'Processed: {self.req_proc}. '
                f'Pending requests: {self.req_pending}. '
                f'Lost: {self.req_lost}.\n'
                f'Response time: '
                f'Average: {self.avg_resp_time:.4f} s '
                f'Max: {self.max_resp_time:.4f} s '
                f'Min: {self.min_resp_time:.4f} s '
                f'Median: {self.median_resp_time:.4f} s '
                f'90-perc: {self.perc90_resp_time:.4f} s '
                f'95-perc: {self.perc95_resp_time:.4f} s\n'
                f'Cost: {self.cost:.2f}. Util: {self.util:.2f}\n'
                f'Sim time: {self.sim_time:2f} s. Stats time: {self.stats_time:.2f} s')

class Monitor():
    '''Obtains staticstics about the system'''
    def __init__(self):
        # All of these are counts of different types of requests
        self.req_injected: int = 0
        self.req_proc: int = 0
        self.req_lost: int = 0
        self.req_pending: int = 0

        self.response_times: List[float] = []
        self.ev_times: List = []
        self.vm_utils = {}

        self.sim_start: float = 0
        self.sim_end: float = 0
        self.stats_start: float = 0
        self.stats_end: float = 0

        self.cost: float = 0
        self.util: float = 0 # Value between 0 and 1

    def add_req_injected(self, req):
        '''Adds an injected requests'''
        self.req_injected += 1

    def add_req_proc(self, req):
        '''Adds a processed request and stores its statistics'''
        self.req_proc += 1
        resp_time = req.response_time
        self.response_times.append(resp_time)

        self.ev_times.append([req.creation_time, req.start_proc_time,
                            req.end_proc_time, req.app, req.vm, req.lost])

    def add_req_lost(self, req):
        '''Adds a lost request'''
        self.req_lost += 1

    def update_req_pending(self, req_pending: int):
        '''Sets the number of pending requests'''
        self.req_pending = req_pending

    def start_sim(self):
        '''Indicate that the simulation has started. Records the start time'''
        self.sim_start = time.time()

    def end_sim(self):
        '''Indicate that the simulation has ended. Records the end time'''
        self.sim_end = time.time()

    def update_cost(self, current_cost: float):
        '''Adds the cost of the current active VMs for one time slot'''
        self.cost += current_cost

    def update_util(self, current_util: float, vm_utils):
        '''Updates the (accumulated) utilization and the dictionary of utils per
        VM'''
        self.util = current_util
        self.vm_utils = vm_utils

    def get_stats(self) -> SimulationStats:
        '''Obtain simulation statistics'''
        stats_start = time.time()

        count = len(self.response_times)
        assert  count == self.req_proc

        if count > 0:
            mean = statistics.mean(self.response_times)
            max_time = max(self.response_times)
            min_time = min(self.response_times)
            median_time = np.percentile(self.response_times, 50)
            perc90_time = np.percentile(self.response_times, 90)
            perc95_time = np.percentile(self.response_times, 95)
        else:
            mean = 0
            max_time = 0
            min_time = 0
            median_time = 0
            perc90_time = 0
            perc95_time = 0

        stats_end = time.time()

        return SimulationStats(req_injected=self.req_injected,
            req_proc=self.req_proc,
            req_pending=self.req_pending,
            req_lost=self.req_lost,
            avg_resp_time=mean,
            max_resp_time=max_time,
            min_resp_time=min_time,
            median_resp_time=median_time,
            perc90_resp_time=perc90_time,
            perc95_resp_time=perc95_time,
            cost=self.cost,
            util=self.util,
            sim_time=self.sim_end - self.sim_start,
            stats_time=stats_end - stats_start)

    def get_ev_times(self):
        '''Return the event times of each request'''
        return self.ev_times

    def get_vm_utils(self):
        '''Return the utilizations of each VM'''
        return self.vm_utils
