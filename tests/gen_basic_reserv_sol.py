'''This module generates a basic solution with two apps, but requiring reserved
instances'''

import pickle
from typing import Tuple
from datetime import datetime

import pulp
from malloovia import (InstanceClass, App, PerformanceSet, PerformanceValues,
    Problem, PhaseI, Status, Workload)

PRIV_ECUS = 1
WL_LEN = 24*365 # Number of hours of the workload
RPH = 3 # for performance and for workload

def get_perfs(
    ics: Tuple[InstanceClass],
    apps: Tuple[App],
    perf_factor: int,
    perfs_per_ecu: Tuple[int]
    ) -> PerformanceSet:

    perf_dict = {}
    for ic in ics:
        ecus = PRIV_ECUS
        perf_dict[ic] = {
            app: perf * ecus * perf_factor
            for app, perf in zip(apps, perfs_per_ecu)
        }

    performances = PerformanceSet(
        id="performances",
        time_unit="h",
        values=PerformanceValues(perf_dict)
    )
    return performances

def solve_problem(perf_factor, verbose=False):
    ics = [ # Only one
        InstanceClass(id='priv', name='priv',
                    limiting_sets=(),
                    price=0.01,
                    max_vms=2,
                    is_reserved = True,
                    time_unit="h")
    ]

    n_apps = 2

    # Apps
    apps = tuple(App(f'a{i}', name=f'{i}') for i in range(n_apps))

    # Performances
    perfs_per_ecu = [RPH, RPH]
    perfs = get_perfs(ics=tuple(ics), apps=apps, perf_factor=perf_factor,
        perfs_per_ecu=perfs_per_ecu)

    # Workloads
    wls = (
        [RPH, 0] * (WL_LEN//2),
        [0, RPH] * (WL_LEN//2),
    )

    ltwp = []
    for app, wl in zip(apps, wls):
        ltwp.append(
            Workload(
                "ltwp_{}".format(app.id),
                description="rph for {}".format(app.name),
                app=app,
                time_unit="h",
                values=tuple(wl),
            )
        )

    problem = Problem(
        id="Hybrid cloud",
        name="Hybrid cloud",
        workloads=tuple(ltwp),
        instance_classes=tuple(ics),
        performances=perfs,
    )

    print('Solving', datetime.now().strftime("%H:%M:%S"))
    phase_i = PhaseI(problem)
    solver = pulp.COIN(maxSeconds=2200*60, msg=1, fracGap=0.05, threads=8)
    phase_i_solution = phase_i.solve(solver=solver)

    filename = 'sols/basic_reserv.p'
    pickle.dump(phase_i_solution, open(filename, 'wb'))

    status = phase_i_solution.solving_stats.algorithm.status
    if status != Status.optimal:
        print(f"No optimal solution. Status: {status.name} ({status})")
        print('Time', datetime.now().strftime("%H:%M:%S"))

        raise Exception()

    comp_cost_malloovia = phase_i_solution.solving_stats.optimal_cost

    if verbose:
        print("="*80)
        print(f"Computation cost = {comp_cost_malloovia}")
        print("="*80)

def main():
    perf_factor = 1

    print(f' perf_factor: {perf_factor}')

    solve_problem(perf_factor=perf_factor, verbose=True)

if __name__ == "__main__":
    main()
