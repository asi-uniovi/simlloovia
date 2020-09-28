# coding: utf-8
"""This module implements a simulator for cloud computing based in malloovia
and using simpy.

It assumes one simulation tick is one second."""

import time
from collections import defaultdict
from itertools import islice
from typing import Sequence, List, Dict, Optional, Tuple
import simpy

from malloovia import (InstanceClass, PerformanceSet, PerformanceValues, App,
    AllocationInfo, Workload, TimeUnit)

from .monitor import Monitor

class Request():
    '''Data object to save the creation, start_proc and end_proc times of a
    request, in addition to its number. The class has static variables to count
    the requests per app and give them the request number.

    Args:
        env: simpy enviroment
        app: app corresponding to the request
    '''

    count: int = 0

    def __init__(self, env: simpy.Environment, app: App):
        self.env: simpy.Environment = env
        self.app: App = app

        self.num: int = Request.count
        Request.count += 1

        self.creation_time: float = env.now
        self.start_proc_time: float = -1
        self.end_proc_time: float = -1
        self.lost: bool = False # True when it cannot be processed
        self.vm: Optional[Vm] = None # VM that processed the request

    def start_proc(self, vm: 'Vm'):
        '''Indicate that the processing of the requests has started'''
        self.start_proc_time = self.env.now
        self.vm = vm

    def end_proc(self):
        '''Indicate that the processing of the requests has ended'''
        self.end_proc_time = self.env.now

    @property
    def response_time(self):
        '''Get the response time of the request. Can only be called after it has
        been processed'''
        return self.end_proc_time - self.creation_time

    def mark_as_lost(self):
        '''Indicate that the request has been lost, i.e., it could not be
        processed'''
        self.lost = True
        self.start_proc_time = self.end_proc_time = self.env.now

    def __str__(self):
        return 'Request {num} ({name})'.format(num=self.num, name=self.app.name)

class RequestSink():
    '''Takes a request and stores stats.

    Args:
        env: simpy enviroment
        monitor: monitor to store stats
    '''
    def __init__(self, env: simpy.Environment, monitor: Monitor):
        self.env = env
        self.monitor = monitor

    def add_request(self, req: Request):
        '''Receives the request'''
        if not req.lost: # Lost requests are already recorded in the stats
            self.monitor.add_req_proc(req)

class LoadBalancer():
    '''Simulates a load balancer. It has a list of active VMs per type of
    application and sends the requests received to the appropriate VM taking
    into account the app of the request.

    Args:
        env: simpy enviroment
        request_sink: simulation component where the requests must go at the end
        monitor: monitor to store stats
    '''
    def __init__(self, env: simpy.Environment, request_sink: RequestSink,
            monitor: Monitor):
        self.env = env
        self.request_sink = request_sink
        self.monitor = monitor

        # Dict where the keys are malloovia apps and the values are list of VMs
        self.vms: Dict[App, List[Vm]] = defaultdict(list)

        self.store = simpy.Store(env) # stores requests
        self.action = env.process(self.__process())

    def __process(self):
        while True:
            req = (yield self.store.get())
            self.__distribute_req(req, self.vms[req.app])

    def __distribute_req(self, req: Request, vms_for_app: List['Vm']):
        if not vms_for_app:
            req.mark_as_lost()
            self.monitor.add_req_lost(req)
            self.request_sink.add_request(req)
            return

        # Look for the VM for this app with maximum free capacity
        max_vm = max(vms_for_app, key=lambda vm: vm.free_capacity())

        max_vm.add_request(req)

    def add_request(self, req):
        '''Receive a new request that must be processed'''
        self.store.put(req)

    def update_vm_pool(self, vm: 'Vm'):
        '''Receives a VM and adds it to the pool of available VMs for the
        app indicated in the VM'''

        # Remove from any existing list
        for vms_for_app in self.vms.values():
            if vm in vms_for_app:
                vms_for_app.remove(vm)

        self.vms[vm.app].append(vm)

    def remove_vm(self, vm: 'Vm'):
        '''Removes a VM from the list of available VMs'''
        self.vms[vm.app].remove(vm)

    def end_sim(self):
        '''Indicates to all the running VMs that the simulation has finished'''
        for vms_for_app in self.vms.values():
            for vm in vms_for_app:
                vm.end_sim()

class Vm():
    '''Simulates a virtual machine of a fixed instance class. It can only
    process requests from one app at any given time, assigned with the method
    assign_app().

    It takes requests with the method add_request() and processes them at the
    service rate corresponding to the performance of the instance class for the
    kind of app of that request. It then sends the request to the output defined
    as a parameter in the constructor.

    It can obtain the utilization and the cost, but notice that it cannot be
    restarted once it is stopped.

    Args:
        env: simpy enviroment
        ic: instance class for this VM. Determines cost and performance
        perfs: performance for each instance class and app
        out: object that implements add_request() (for instance, RequestSink).
            Where to send the request after it has been processed
        load_balancer: load balancer to register the VM as available for being
            used in a schedule
    '''
    count = 0 # Number of VMs created. Used for naming new VMs

    def __init__(self, env: simpy.Environment, ic: InstanceClass,
                perfs: PerformanceSet, out, load_balancer: LoadBalancer):
        self.env = env
        self.num = Vm.count
        Vm.count += 1

        self.app = None # Initially, no app assigned
        self.keep: bool = False # Initially, it doesn't matter
        self.is_shutting_down: bool = False # Initially, it isn't shutting down
        self.time_comp_ends = None # Indicates when the current computation ends

        self.store = simpy.Store(env)
        self.current_reqs: int = 0 # In the queue or being processed
        self.current_proc_req: Optional[float]  = None # Request being processed now

        self.ic: InstanceClass = ic
        self.perfs: PerformanceSet = perfs

        self.out = out
        self.load_balancer = load_balancer

        # Fields por computing the utilization and the cost
        self.start_time: float = env.now # The VM starts when created
        self.stop_time: Optional[float] = None # Set when the machine stops
        self.sec_used: float = 0 # Accumulated seconds used in computing requests
        self.current_req_start: Optional[float] = None

        self.action = env.process(self.__process())

    def __service_time_sec(self, app: App):
        perf = self.perfs.values[self.ic, app]
        perf_sec = perf / TimeUnit(self.perfs.time_unit).to('s')
        return 1/perf_sec

    def __process(self):
        while True:
            if self.is_shutting_down and len(self.store.items) == 0:
                self.stop_time = self.env.now
                break # No more processing to do. VM is really stopped

            req = (yield self.store.get())

            if req.app != self.app:
                msg = 'Invalid app for this VM {}. Expected: {}. Received: {}'\
                    ' Time: {}'.format(self.name(), self.app, req.app,
                    self.env.now)
                raise Exception(msg)

            req.start_proc(self)

            self.current_proc_req = req

            serv_time_sec = self.__service_time_sec(req.app)
            self.time_comp_ends = self.env.now + serv_time_sec
            self.current_req_start = self.env.now

            yield self.env.timeout(serv_time_sec)

            self.time_comp_ends = None
            self.current_req_start = None

            # This is used to compute the utilization
            self.sec_used += serv_time_sec

            req.end_proc()

            self.current_reqs -= 1
            self.current_proc_req = None

            self.out.add_request(req)

    def add_request(self, req):
        '''Receive a request that must be processed'''
        self.current_reqs += 1
        self.store.put(req)

    def begin_shutdown(self):
        '''Indicate that the VM has to start the shutdown process. Thus, it will
        not be available for the distributor. However, all requests in the queue
        will be processed.'''
        if self.ic.is_reserved:
            print(f'WARNING: shutting down reserved instance ({self.name()}) at'
                  f' time {self.env.now}')

        if self.is_computing():
            print(f'WARNING: shutting down VM {self.name()}, which is still'
                  f' executing a request at time {self.env.now}')

        if self.store.items:
            print(f'WARNING: shutting down VM {self.name()} with'
                f' {len(self.store.items)} pending requests at time'
                f' {self.env.now}')

        self.load_balancer.remove_vm(self)

        self.is_shutting_down = True

        if self.is_free(): # The VM can be really stopped
            self.stop_time = self.env.now

    def is_computing(self):
        '''Returns true is there is no computation going on or the current
        computation is scheduled to finish later. Notice that there migth be a
        request still executing that finishes in this same moment but hasn't
        still been processed'''
        return self.time_comp_ends != None and self.time_comp_ends > self.env.now

    def requests_in_queue_or_processing(self):
        '''Indicate if there are requests in the queue or processing'''
        return self.store.items or self.is_computing()

    def is_free(self):
        '''Returns True is there is no app asigned or there are no requests,
        in the queue or processing'''
        return self.app is None or not self.requests_in_queue_or_processing()

    def assign_app(self, app):
        '''A VM cannot change which app it is executing, so it only can be
        assigned if it has not been assigned before'''
        if self.app and self.app != app:
            msg = f'{self.name()} ({self.ic.name}) cannot be changed from'\
                  f' {self.app} to {app} at time slot {self.env.now}'
            raise Exception(msg)

        self.app = app
        self.load_balancer.update_vm_pool(self)

    def compute_period_cost(self, period_sec):
        '''Returns the cost of running the VM for a period expressed in seconds.
        It uses per-second billing without a minimum billing period.'''
        price = self.ic.price
        price_units = self.ic.time_unit
        sec_per_price_unit = TimeUnit(price_units).to('s')
        price_per_sec = price / sec_per_price_unit

        return period_sec * price_per_sec

    def __sec_running(self):
        '''Returns the seconds the VM has been running until now (or when it
        stopped).'''
        end_time = self.stop_time if self.stop_time else self.env.now
        return end_time - self.start_time

    def compute_cost(self):
        '''Returns the cost of the VM until until now (or when it stopped).'''
        return self.compute_period_cost(self.__sec_running())

    def compute_util(self):
        '''Returns the utilization of the VM from the start until now (or when
        it stopped).'''
        sec_used = self.sec_used

        # If a request is being processed, add the time from when the request
        # started until now
        if self.current_req_start:
            sec_used += self.env.now - self.current_req_start

        util = sec_used/self.__sec_running()

        return util

    def name(self):
        '''Returns the name of the VM'''
        return 'VM {}'.format(self.num)

    def free_capacity(self):
        '''Returns the free capacity approximated by the 1 minus the proportion
        of requests per time unit that the VM can handle'''
        return 1 - (self.current_reqs / self.perfs.values[self.ic, self.app])

    def get_pending_requests(self):
        '''Returns the number of pending requests for this VM. It includes the
        request currently being executed (if it doesn't finish in this time
        slot) and the ones in the queue'''
        res = len(self.store.items)

        if self.is_computing() and self.time_comp_ends > self.env.now:
            res += 1

        return res

    def end_sim(self):
        '''Processes the last event if it finishes at the same time as the
        simulation'''
        if self.current_proc_req and self.time_comp_ends == self.env.now:

            # This is used to compute the utilization
            self.sec_used += self.env.now - self.current_req_start

            self.time_comp_ends= None
            self.current_req_start = None

            self.current_proc_req.end_proc()

            self.out.add_request(self.current_proc_req)

            self.current_reqs -= 1
            self.current_proc_req = None

class WorkloadInjector():
    '''Simulates a workload injector that generates the workload requests.

    Args:
        env: simpy enviroment
        workloads: workloads as malloovia workloads
        period_sec: a number. It should be the size in simulation ticks
            (seconds) of the workload injection period.
        workload_length: number of workload injection periods. If it is None,
            all the periods present in the first workload will be injected. All
            workloads are assumed to have the same length.
        out: where to send the requests. It must be an object that has the
            function add_request(). Typically, it will be the LoadBalancer.
        monitor: Monitor class that will be informed each time a request is
            injected.
    '''
    def __init__(self, env: simpy.Environment, workloads: Sequence[Workload],
            period_sec: float, workload_length: Optional[int], out,
            monitor: Monitor):
        self.env = env
        self.workloads = workloads
        self.period_sec = period_sec
        self.workload_length = workload_length
        self.out = out
        self.prev_progress = 0
        self.monitor = monitor

        self.action = env.process(self.__process())

    def __generate_requests(self, workload: Workload, time_slot: int):
        requests = workload.values[time_slot]

        for _ in range(requests):
            req = Request(env=self.env, app=workload.app)
            self.out.add_request(req)
            self.monitor.add_req_injected(req)

    def __time_to_str(self, t):
        fmt_str = "%H:%M.%S"
        return time.strftime(fmt_str, (time.localtime(t)))

    def __print_progress(self, ts, timeslot_count, start_time):
        ts = ts + 1 # timeslots start in zero
        progress = ts*100/timeslot_count

        if progress - self.prev_progress < 0.5:
            return # Show at leat 0.5% progress

        self.prev_progress = progress

        now = time.time()
        elapsed = now - start_time
        time_per_ts = elapsed/ts

        remaining_ts = timeslot_count - ts
        remaining_time = remaining_ts * time_per_ts
        if remaining_time < 10:
            # When the end is very close, no more messages. This also speeds up
            # short tests where most of the time is wasted showing the update
            # time
            return

        now_str = self.__time_to_str(now)
        finish_str = self.__time_to_str(now + remaining_time)

        print(f'[{now_str}] {progress:6.2f}% Finish: {finish_str}', flush=True)

    def __process(self):
        if self.workload_length:
            timeslot_count = self.workload_length
        else:
            timeslot_count = len(self.workloads[0].values)

        start_time = time.time()

        for ts in range(timeslot_count):
            self.__print_progress(ts, timeslot_count, start_time)

            # Give time for events of requests to be processed
            yield self.env.timeout(0)

            for w in self.workloads:
                self.__generate_requests(w, ts)
            yield self.env.timeout(self.period_sec)

class VmManager:
    '''Manages VMs. It has a list of active VMs. It receives allocations and
    reuses the VMs from the current active VMs, shutdowns the ones not needed
    and starts new ones if required.

    Args:
        env: simpy enviroment
        reserved_allocation: allocation of reserved instances
        perf_values: values of each instance class used
        load_balancer: load balancer. It is used to indicate which VMs are
            active
        request_sink: where to send the requests when they are finished
    '''

    def __init__(self, env: simpy.Environment,
            reserved_allocation: AllocationInfo,
            perf_values: PerformanceValues, load_balancer: LoadBalancer,
            request_sink: RequestSink) -> None:

        self.env = env
        self.reserved_allocation = reserved_allocation
        self.perf_values = perf_values
        self.load_balancer = load_balancer
        self.request_sink = request_sink

        # First key is app, second is instace class
        self.running_vms: Dict[App, Dict[InstanceClass, List[Vm]]] = defaultdict(lambda: defaultdict(list))
        self.running_vms_flat: List[Vm] = [] # Copies of running VMs
        self.shutdown_vms: List[Vm] = []
        self.all_vms: List[Vm] = [] # Copies of VMs running and shutdown

        if reserved_allocation:
            self.__launch_reserved_vms()

    def implement_allocation(self, apps: Sequence[App],
            ics: Sequence[InstanceClass], vm_count: Sequence[List[float]]):
        '''Receives an allocation and changes the current allocation to the one
        received by stopping and starting VMs as required.'''

        self.__set_keep_false_for_all_running_vms()

        # Mark all VMs that have to be kept without changing the app they are
        # running. After this, vm_count has the missing VMs
        self.__keep_vms(VmManager.__filter_keep_without_changing_app, apps, ics,
                vm_count)

        self.__shutdown_unrequired_vms()
        self.__launch_missing_vms(apps, ics, vm_count)

    def compute_cost(self):
        '''Returns the cost of all VMs'''
        cost = 0
        for vm in self.all_vms:
            cost += vm.compute_cost()

        return cost

    def compute_util(self)-> Tuple[float, Dict[Vm, float]]:
        '''Returns the average utilization of the all VMs created, and a
        dictionary with the utilizaction per VM'''
        util: float = 0
        vm_utils = {}
        for vm in self.all_vms:
            vm_utils[vm] = vm.compute_util()
            util += vm_utils[vm]

        util = util/len(self.all_vms)

        return util, vm_utils

    def get_pending_requests(self) -> Dict[App, int]:
        '''Returns a dictionary with the number of pending requests (requests
        that are in the queue of some VM or are being executed) per app'''
        res: Dict[App, int] = {}
        for vm in self.all_vms:
            if vm.app in res.keys():
                res[vm.app] += vm.get_pending_requests()
            else:
                res[vm.app] = vm.get_pending_requests()

        return res

    def __launch_vms(self, ic: InstanceClass, app: App, count: int):
        '''Launches count VMs of type ic'''

        for _ in range(int(count)):
            vm = Vm(env=self.env, ic=ic, perfs=self.perf_values,
                out=self.request_sink,
                load_balancer=self.load_balancer)

            self.running_vms[app][ic].append(vm)
            self.running_vms_flat.append(vm)
            self.all_vms.append(vm)

            if app is not None:
                vm.assign_app(app)

    def __launch_reserved_vms(self):
        for ic, vms_number in zip(
                self.reserved_allocation.instance_classes,
                self.reserved_allocation.vms_number):
            self.__launch_vms(ic=ic, app=None, count=vms_number)

    def __set_keep_false_for_all_running_vms(self):
        for vms_for_ic in self.running_vms.values():
            for vms in vms_for_ic.values():
                for vm in vms:
                    vm.keep = False

    @staticmethod
    def __filter_keep_without_changing_app(vm: Vm, app: App, ic: InstanceClass):
        '''Selects the VMs of type 'ic' that are assigned to 'app' or to no
        app'''
        return vm.ic == ic and (vm.app == None or vm.app == app)

    def __keep_vms(self, filter_fun, apps: Sequence[App],
            ics: Sequence[InstanceClass], vm_count: Sequence[List[float]]):
        '''Selects the VMs that fulfill filter_fun and sets keep to true
        and the app to the app indicated in vm_count. It updates vm_count.'''
        for app_index, app in enumerate(apps):
            for ic_index, ic in enumerate(ics):
                required_vms = int(vm_count[app_index][ic_index])

                # Keep up to required_vms
                vms_to_keep = list(islice(
                    filter(lambda vm: filter_fun(vm, app, ic),
                           self.running_vms_flat),
                    required_vms))

                for vm in vms_to_keep:
                    vm.keep = True

                    # Check that the VM is not changing app if it has pending
                    # requests
                    if vm.app is not None and vm.app != app and not vm.is_free():
                        req_count = len(vm.store.items)
                        if vm.is_computing():
                            req_count += 1
                        print(f'WARNING: {vm.name()} repurposed for {app} but '
                              f'still has {req_count} requests from {vm.app} '
                              f'at time {self.env.now}')
                        print(f'VM computation ends at {vm.time_comp_ends}')

                    vm.assign_app(app)

                vm_count[app_index][ic_index] -= len(vms_to_keep)

    def __shutdown_unrequired_vms(self):
        # This list is created to avoid chaning the list self.vms while we are
        # iterating over it. Thus, we do it in two steps
        vms_to_remove = []

        # Step 1: get the list of vms to remove
        for vm in self.running_vms_flat:
            if not vm.keep and not vm.ic.is_reserved:
                vm.begin_shutdown()
                vms_to_remove.append(vm)

        # Step 2: actually remove them
        for vm in vms_to_remove:
            self.running_vms_flat.remove(vm)
            self.shutdown_vms.append(vm)

            for vms_for_ic in self.running_vms.values():
                for vms in vms_for_ic.values():
                    if vm in vms:
                        vms.remove(vm)

    def __launch_missing_vms(self, apps: Sequence[App],
            ics: Sequence[InstanceClass], vm_count: Sequence[List[float]]):
        '''Creates the required VMs indicated in vm_count'''
        for app_index, app in enumerate(apps):
            for ic_index, ic in enumerate(ics):
                required_vms = int(vm_count[app_index][ic_index])

                if ic.is_reserved and required_vms > 0:
                    msg = f'ERROR: Not enough reserved instances for {ic.name}'
                    raise Exception(msg)

                self.__launch_vms(ic, app, required_vms)

class MallooviaAllocator():
    '''An allocator that works only with AllocationInfo objects that indicate
    for each workload level the allocation, as in SolutionI objects.

    The workloads are expressed per allocation period. The period is expressed
    in seconds.

    In every scheduling slot, the allocator gets the workload level and tells
    the VM manager to create the corresponding allocation according to the
    solution.

    Args:
        env: simpy enviroment
        allocation: allocation per workload level
        workloads: workload for each allocation period
        period_sec: lenght of the allocation period in seconds
        vm_manager: VM manager that must implement the allocation
        request_sink: where to send the requests when they are finished
        monitor: monitor to store stats
    '''

    def __init__(self, env: simpy.Environment, allocation: AllocationInfo,
            workloads: Sequence[Workload], period_sec: float,
            vm_manager: VmManager, request_sink: RequestSink,
            monitor: Monitor):
        self.env = env
        self.allocation = allocation
        self.workloads = workloads
        self.period_sec = period_sec
        self.vm_manager = vm_manager
        self.request_sink = request_sink
        self.monitor = monitor

        self.action = env.process(self.process())

    def __get_workload_level(self, ts: int):
        '''Gets the workload level for time slot ts as a Tuple'''
        return tuple(w.values[ts] for w in self.workloads)

    def __get_vm_count_copy(self, wl_level) -> Sequence[List[float]]:
        '''Gets the allocation values (vm count for each app) for this
        wl_level'''
        index = self.allocation.workload_tuples.index(wl_level)
        return tuple(list(x) for x in self.allocation.values[index])

    def __process_time_slot(self, ts: int):
        '''Simulates the assigment for time slot ts. It gets the workload level
        for this time slot and the allocation computed by Malloovia for this
        workload level. Then tells the VM manager to allocate the number of VMs
        required for each application.
        '''
        wl_level = self.__get_workload_level(ts)
        vm_count = self.__get_vm_count_copy(wl_level)

        self.vm_manager.implement_allocation(self.allocation.apps,
            self.allocation.instance_classes, vm_count)

    def process(self):
        timeslot_count = len(self.workloads[0].values)
        for ts in range(timeslot_count):
            # Give time for events of requests to be processed
            yield self.env.timeout(0)

            self.__process_time_slot(ts)

            yield self.env.timeout(self.period_sec)
