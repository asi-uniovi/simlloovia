'''This module defines class Simulator, which is the main entry point for
simlloovia.
'''
from typing import Sequence, Tuple, Optional
from functools import wraps
import simpy

from malloovia import (PerformanceSet, AllocationInfo, SolutionI, Workload,
    TimeUnit, ReservedAllocation)

from .core import (WorkloadInjector, LoadBalancer, VmManager, RequestSink,
    MallooviaAllocator)

from .monitor import (Monitor, SimulationStats)

class Simulator():
    '''Main class to simulate transactional systems running on cloud
    infrastructure'''
    def __init__(self):
        self.monitor = Monitor()

    def simulate(self, reserved_allocation: ReservedAllocation,
                performances: PerformanceSet,
                allocation: AllocationInfo,
                allocation_workloads: Sequence[Workload],
                period_allocation_sec: int,
                injector_workloads: Sequence[Workload],
                period_injector_sec: int,
                workload_length: int=None, animate: bool=True, speed: float=1,
                trace: bool=False) -> SimulationStats:
        """Simulates the system passed as arguments

        Args:
            reserved_allocation (ReservedAllocation): allocation of reserved VMs
            performances (PerformanceSet): performance of all instance classes
            allocation (AllocationInfo): allocations
            allocation_workloads (Sequence[Workload]): workload used in the
                allocation
            period_allocation_sec (int): period used in the allocation workloads
            injector_workloads (Sequence[Workload]): workloads to inject
            period_injector_sec (int): period used in the workload to inject
            workload_length (int, optional): number of periods of injection
            animate (bool, optional): use animation. Defaults to True.
            speed (float, optional): sped of the simulation. Defaults to 1.
            trace (bool, optional): generate a trace. Defaults to False.

        Returns:
            SimulationStats: statistics about the simulation
        """
        # Create simulation objects
        env = simpy.Environment()

        sim_length_sec = None
        if workload_length:
            sim_length_sec = workload_length*period_injector_sec


        request_sink = RequestSink(env, self.monitor)

        load_balancer = LoadBalancer(env=env, request_sink=request_sink,
            monitor=self.monitor)

        vm_manager = VmManager(env=env,
                        reserved_allocation=reserved_allocation,
                        perf_values=performances,
                        load_balancer=load_balancer, request_sink=request_sink)

        allocator = MallooviaAllocator(env=env,
            allocation=allocation,
            workloads=allocation_workloads,
            period_sec=period_allocation_sec,
            vm_manager=vm_manager,
            request_sink=request_sink,
            monitor=self.monitor)

        workload_injector = WorkloadInjector(env=env,
            workloads=injector_workloads,
            period_sec=period_injector_sec,
            workload_length=workload_length,
            out=load_balancer,
            monitor=self.monitor)

        # Run simulation
        self.__run_simulation(env=env,
            load_balancer=load_balancer,
            sim_length_sec=sim_length_sec,
            animate=animate,
            speed=speed,
            trace=trace)

        # Get stats
        pending_requests = vm_manager.get_pending_requests()
        self.monitor.update_req_pending(sum(pending_requests.values()))

        self.monitor.update_cost(vm_manager.compute_cost())
        self.monitor.update_util(*vm_manager.compute_util())

        stats = self.monitor.get_stats()

        req_in_sys = stats.req_proc + stats.req_lost + stats.req_pending
        if stats.req_injected != req_in_sys:
            print(f"WARNING: the number of requests injected ({stats.req_injected}) "
                f"doesn't match the requests in the system ({req_in_sys})")

        return stats

    def simulate_malloovia(self, solution: SolutionI, workload_length: int=None,
                animate: bool=True, speed: float=1,
                trace: bool=False) -> SimulationStats:
        '''This function simulates a Malloovia SolutionI sending all the requests
        at the  beginning of the  time slot'''

        # Both the allocation and the workloads have the same period
        period_sec = TimeUnit(solution.problem.workloads[0].time_unit).to('s')

        return self.simulate(
            reserved_allocation=solution.reserved_allocation,
            performances=solution.problem.performances,
            allocation=solution.allocation,
            allocation_workloads=solution.problem.workloads,
            period_allocation_sec=period_sec,
            injector_workloads=solution.problem.workloads,
            period_injector_sec=period_sec,
            workload_length=workload_length,
            animate=animate, speed=speed, trace=trace
        )

    def read_workload(self, filename: str, workload_length: Optional[int]) -> Tuple[int, ...]:
        '''Reads a workload from a file of coma-separated-values file with all the
        workloads in the same line. The format of the file is something like:
                3, 100, 34, 500
        Returns the tuple with the values
        '''
        with open(filename) as f:
            row = f.readline()
            result = (tuple(int(x) for x in row.split(',')[:workload_length]))

        return result

    def simulate_malloovia_workload_file(self, solution: SolutionI,
                workload_filename_prefix: str,
                workload_period_sec: int,
                workload_length: int=None,
                animate: bool=True, speed: float=1,
                trace: bool=False) -> SimulationStats:
        '''This function simulates a Malloovia SolutionI but takes the
        workload from a coma-separated-values file with all the workloads
        in the same line. The format of the file is something like:
                3, 100, 34, 500

        The allocations used will follow the load level of the original problem
        trace, not the workload read from the file.

        There should be a workload file for each app. The filename for each app will
        be obtained by adding the app index to the `workload_filename_prefix`.
        '''

        allocation_period_sec = TimeUnit(solution.problem.workloads[0].time_unit).to('s')

        apps = [w.app for w in solution.problem.workloads]
        injector_workloads = []
        for i, app in enumerate(apps):
            wl = self.read_workload(f'{workload_filename_prefix}{i}.csv', workload_length)
            injector_workloads.append(
                Workload(
                    "injector_app{}".format(app.id),
                    description="rps for {}".format(app.name),
                    app=app,
                    time_unit="s",
                    values=wl,
                )
            )

        return self.simulate(
            reserved_allocation=solution.reserved_allocation,
            performances=solution.problem.performances,
            allocation=solution.allocation,
            allocation_workloads=solution.problem.workloads,
            period_allocation_sec=allocation_period_sec,
            injector_workloads=injector_workloads,
            period_injector_sec=workload_period_sec,
            workload_length=workload_length,
            animate=animate, speed=speed, trace=trace
        )

    def simulate_malloovia_workload(self, solution: SolutionI,
                workloads: Sequence[Tuple[float]],
                workload_period_sec: int,
                workload_length: int=None,
                animate: bool=True, speed: float=1,
                trace: bool=False) -> SimulationStats:
        '''This function simulates a Malloovia SolutionI but takes the workload
        from a list of list. The first index in the list is for apps and the
        second index, for timeslots. So this:

            [
                [100, 3, 75],
                [44, 25, 20]
            ]

        means that app0 has workload 100, 3 and 75 in timeslots 0, 1 and 2,
        repectively, and app1 has workload 44, 25 and 20 in those timeslots.

        The allocations used will follow the load level of the original problem
        trace.
        '''

        allocation_period_sec = TimeUnit(solution.problem.workloads[0].time_unit).to('s')

        apps = [w.app for w in solution.problem.workloads]

        if len(apps) != len(workloads):
            raise Exception(f'The number of workloads in the parameter'\
                f' ({len(workloads)}) and in the file ({len(apps)}) are '\
                f'different.')

        injector_workloads = []
        for i, app in enumerate(apps):
            injector_workloads.append(
                Workload(
                    "injector_app{}".format(app.id),
                    description="rps for {}".format(app.name),
                    app=app,
                    time_unit="s",
                    values=workloads[i],
                )
            )

        return self.simulate(
            reserved_allocation=solution.reserved_allocation,
            performances=solution.problem.performances,
            allocation=solution.allocation,
            allocation_workloads=solution.problem.workloads,
            period_allocation_sec=allocation_period_sec,
            injector_workloads=injector_workloads,
            period_injector_sec=workload_period_sec,
            workload_length=workload_length,
            animate=animate, speed=speed, trace=trace
        )

    def get_ev_times(self):
        return self.monitor.get_ev_times()

    def get_vm_utils(self):
        return self.monitor.get_vm_utils()

    def __run_simulation(self, env: simpy.Environment,
                load_balancer: LoadBalancer,
                sim_length_sec: Optional[int]=None,
                animate: bool=True,
                speed: float=1, trace: bool=False):

        def add_tracing_callback(env: simpy.Environment, callback):
            def get_wrapper(env_step, callback):
                @wraps(env_step)
                def tracing_step():
                    if len(env._queue) > 0:
                        t, prio, eid, event = env._queue[0]
                        callback(t, prio, eid, event)
                    return env_step()
                return tracing_step

            env.step = get_wrapper(env.step, callback)

        def tracing(t, prio, eid, event):
            print(f'[{t}] prio: {prio}, eid: {eid}, event: {event}')

        if trace:
            add_tracing_callback(env, tracing)

        self.monitor.start_sim()

        if sim_length_sec:
            env.run(until=sim_length_sec)
        else:
            env.run()

        load_balancer.end_sim()

        self.monitor.end_sim()
