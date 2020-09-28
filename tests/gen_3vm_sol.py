'''This module generates a solution with one app that has 3 vms in time slot 0
and 1 vm in time slot 1'''

from typing import List, Any, Mapping, Tuple
from collections import namedtuple
from math import gcd
from functools import reduce
import itertools
import malloovia
from malloovia import *
import pandas as pd
import csv
import statistics
import pulp
import pprint
import numpy as np
from datetime import datetime
import pickle

ECUS = 1
WL_LEN = 2 # Number of hours of the workload
RPH = 3 # for performance and for workload

def get_perfs(
    ics: List[malloovia.InstanceClass],
    apps: List[malloovia.App],
    perf_factor: int,
    perfs_per_ecu: List[int]
    ) -> malloovia.PerformanceSet:

    perf_dict = {}
    for ic in ics:
        ecus = ECUS
        perf_dict[ic] = {
            app: perf * ecus * perf_factor
            for app, perf in zip(apps, perfs_per_ecu)
        }

    performances = malloovia.PerformanceSet(
        id="performances", 
        time_unit="h", 
        values=malloovia.PerformanceValues(perf_dict)
    )
    return performances

ExpResult = namedtuple('ExpResult', ['avg_workload',
    'comp_cost_malloovia',
    'creation_time_malloovia',
    'solving_time_malloovia'])

def get_quanta(perf_list, quant_factor):
    '''Get the quantum for each app as the GCD multiplied by quant_factor

    Args:
    - perf_list: Receives a list of performances for each app, i.e., each element
        in the list is the list of performances for every instance for that app
    - quant_factor: factor to multiplicate the GCD
    '''
    # Get the GCD
    quanta = [] # One element per app
    for i in range(len(perf_list)):
        l = [p for p in perf_list[i]]
        quanta.append(reduce(gcd, l))
    print("Quanta GCD:", quanta)
        
    return [q*quant_factor for q in quanta]

def discretize_levels(workloads, quanta):
    assert len(workloads) == len(quanta),\
       "The number of quanta (%d) is not equal to the number of apps (%d)" % (len(quanta), len(workloads))
    quantized = []
    for workload, quantum in zip(workloads, quanta):
        levels = list(range(0,max(workload)+quantum, quantum))
        load_q = np.take(levels, np.digitize(workload, levels, right=True))
        quantized.append(load_q)
    return np.array(quantized)

def solve_problem(perf_factor, quant_factor, verbose=False):

    ics = [ # Only one
        InstanceClass(id=f'ic', name='ic',
                    limiting_sets=(),
                    price=0.01,
                    max_vms=3,
                    is_reserved = False,
                    time_unit="h")
    ]

    n_apps = 1

    # Apps
    apps = [App(f'a{i}', name=f'{i}') for i in range(n_apps)]

    # Performances
    perfs_per_ecu = [RPH, RPH]
    perfs = get_perfs(ics, apps, perf_factor, perfs_per_ecu)

    perf_list = []
    for a in apps:
        l = list(perfs.values[i, a] for i in ics)
        perf_list.append(l)
    
    quanta = get_quanta(perf_list, quant_factor)
    print(f'Quanta used: {quanta}')

    # Workloads
    wls = [
        [3*RPH, RPH] * (WL_LEN//2),
    ]
    print(f'TODO: {len(wls[0])}')
    wls = wls[:n_apps]

    avg_workload = np.mean(wls)
    print(f'total workload before quantization: {np.sum(wls)}')
    print(f'Average workload before quantization: {avg_workload}')

    print('wl no dis:', wls[0][:10])

    if quant_factor != 0:
        wls = discretize_levels(wls, quanta)
        print('wl    dis:', wls[0][:10])

        avg_workload = np.mean(wls)
        print(f'total workload after quantization: {np.sum(wls)}')
        print(f'Average workload after quantization: {avg_workload}')

        wls = wls.tolist()*10 # TODO: fix
    else:
        print('No quantization')
        wls = wls*10 # TODO: fix

    ltwp = []
    for app, wl in zip(apps, wls):
        ltwp.append(
            Workload(
                "ltwp_{}".format(app.id),
                description="rph for {}".format(app.name),
                app=app,
                time_unit="h",
                values=wl,
            )
        )

    problem = Problem(
        id="Hybrid cloud",
        name="Hybrid cloud",
        workloads=ltwp,
        instance_classes=ics,
        performances=perfs,
    )

    print('Solving', datetime.now().strftime("%H:%M:%S"))
    phase_i = PhaseI(problem)
    solver = pulp.COIN(maxSeconds=2200*60, msg=1, fracGap=0.05, threads=8)
    phase_i_solution = phase_i.solve(solver=solver)

    filename = f'sols/3vm.p'
    pickle.dump(phase_i_solution, open(filename, 'wb'))
    
    status = phase_i_solution.solving_stats.algorithm.status
    if status != Status.optimal:
        print(f"No optimal solution. Status: {status.name} ({status})")
        print('Time', datetime.now().strftime("%H:%M:%S"))

        raise Exception()

    comp_cost_malloovia = phase_i_solution.solving_stats.optimal_cost
    creation_time_malloovia = phase_i_solution.solving_stats.creation_time
    solving_time_malloovia = phase_i_solution.solving_stats.solving_time

    if verbose:
        print("="*80)
        print(f"Computation cost = {comp_cost_malloovia}")
        print("="*80)

    return ExpResult(avg_workload,
        comp_cost_malloovia,
        creation_time_malloovia,
        solving_time_malloovia)

def main():
    perf_factor = 1
    quant_factor = 1

    print(f' perf_factor: {perf_factor}'
          f' quant factor: {quant_factor}'
          )

    results = []
    exp_result = solve_problem(perf_factor=perf_factor,
                            quant_factor=quant_factor,
                            verbose=True)
    results.append([perf_factor, quant_factor, *exp_result])

    df = pd.DataFrame(results)
    df.columns = [ "perf_factor", "quant_factor",
                *ExpResult._fields ]

    print(df)

if __name__ == "__main__":
    main()