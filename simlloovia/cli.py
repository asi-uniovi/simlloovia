'''This module defines the command line interface for simlloovia.
'''
import sys
from typing import List, Dict
import pickle
from dataclasses import asdict

import click
import click_config_file
import pandas as pd
import malloovia

from .simulator import Simulator
from .core import Vm

def save_ev_times(output_prefix: str, output_dir: str, ev_times: List[List]):
    '''Saves request event times (creation, start and end) in the file
       reqs:csv, where each line has all the events for a request
    '''
    with open(f'{output_dir}/{output_prefix}_reqs.csv', 'w') as f_reqs:
        f_reqs.write('req,creation,start,end,app,vm,ic,lost\n')

        for i, e in enumerate(ev_times):
            f_reqs.write(f'{i},{e[0]},{e[1]},{e[2]},a{e[3].name},{e[4].name()}'\
                        f',{e[4].ic.id},{e[5]}\n')

def save_vm_utils(output_prefix: str, output_dir: str,
        vm_utils: Dict[Vm, float]):
    with open(f'{output_dir}/{output_prefix}_utils.csv', 'w') as f:
        f.write('vm_name,ic,util\n')
        for vm in vm_utils:
            f.write(f'{vm.name()},{vm.ic.id},{vm_utils[vm]}\n')

# pylint: disable=no-value-for-parameter
@click.command()
@click.option('--sol-file', type=str, required=True,
    help='Malloovia solution file (".p" extension for pickle or ".yaml" for YAML)')
@click.option('--workload', type=str, required=False,
    help='Workload prefix. If missing, the workload in the solution file will '\
         'be used')
@click.option('--workload-period', type=int, required=False, help='Workload period in seconds')
@click.option('--output-prefix', type=str, required=True, help='Output file')
@click.option('--output-dir', type=str, required=True, help='Output directory')
@click.option('--workload-length', type=int, required=False,
    help='Workload length (in number of periods) to simulate. If missing, all '\
         'the workload file will be used')
@click.option('--trace', type=bool, required=False, help='Enable tracing')
@click.option('--save-evs', type=bool, required=False, help='Save request events')
@click.option('--save-utils', type=bool, required=False, help='Save utilization per VM')
@click_config_file.configuration_option(implicit=False)
def simulate(sol_file, workload, workload_period, output_prefix, output_dir,
        workload_length, trace, save_evs, save_utils):
    sys.stdout = open(f'{output_dir}/{output_prefix}_out.txt', 'w')

    if sol_file.endswith('p'):
        sol = pickle.load(open(sol_file, 'rb'))
    elif sol_file.endswith('yaml'):
        sols = malloovia.util.read_solutions_from_yaml(sol_file)
        if len(sols) > 1:
            print('WARNING: only the first solution in the file will be '\
                  'simulated')
        sol = list(sols.values())[0]
    else:
        raise Exception('The solution file extension has to be ".p" (for '\
            'pickle) or ".yaml" (for YAML)')

    if workload and not workload_period:
        raise Exception('If workload is passed, the workload_period has to be passed')

    if workload_period and not workload:
        raise Exception('If workload_period is passed, the workload has to be passed')

    simulator = Simulator()

    if workload:
        sim_stats = simulator.simulate_malloovia_workload_file(solution=sol,
            workload_filename_prefix=workload, workload_period_sec=workload_period,
            workload_length=workload_length, animate=False, speed=0.1, trace=trace)
    else:
        sim_stats = simulator.simulate_malloovia(sol,
            workload_length=workload_length, animate=False, speed=0.1,
            trace=False)

    print(f'Simulation stats for {sol_file}')
    if workload:
        print(f'Workload: {workload}. Length: {workload_length}')
    print(sim_stats)
    print()

    stats_dict = asdict(sim_stats)

    # Add info about the parameters used to simulate
    stats_dict['sol_file'] = sol_file
    stats_dict['workload'] = workload
    stats_dict['workload_period'] = workload_period
    stats_dict['workload_length'] = workload_length

    df = pd.Series(stats_dict)
    print(df)

    df.to_csv(f'{output_dir}/{output_prefix}.csv')

    if save_evs:
        save_ev_times(output_prefix, output_dir, simulator.get_ev_times())

    if save_utils:
        save_vm_utils(output_prefix, output_dir, simulator.get_vm_utils())

if __name__ == "__main__":
    simulate()
