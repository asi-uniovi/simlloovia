import sys
import io
import pickle
import unittest

from simlloovia.simulator import Simulator

class TestBasic(unittest.TestCase):
    def test_basic_malloovia(self):
        '''Tests reading a Malloovia SolutionI file and simulating it'''
        with open('tests/sols/basic.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            sim_stats = sim.simulate_malloovia(sol, workload_length=None,
                                    quantum_sec=3600,
                                    animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 26280)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertEqual(sim_stats.avg_resp_time, 2400)
            self.assertEqual(sim_stats.max_resp_time, 3600)
            self.assertAlmostEqual(sim_stats.cost, 87.60)
            self.assertEqual(sim_stats.util, 1)

    def test_basic_malloovia_smooth_workload(self):
        '''Tests reading a Malloovia SolutionI file and simulating it with a
        different workload (smooth)'''
        with open('tests/sols/basic.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            sim_stats = sim.simulate_malloovia_workload_file(
                sol,
                workload_filename_prefix='tests/workloads/basic_short_sec_smooth/wl',
                workload_period_sec=1,
                workload_length=24*3600,
                quantum_sec=3600,
                animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 70)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertEqual(sim_stats.req_pending, 1)
            self.assertEqual(sim_stats.avg_resp_time, 1635.0857142857142)
            self.assertEqual(sim_stats.max_resp_time, 2734)
            self.assertAlmostEqual(sim_stats.cost, 0.31822500000000004)
            self.assertAlmostEqual(sim_stats.util, 0.7474978679831871)

    def test_basic_malloovia_constant_workload(self):
        '''Tests reading a Malloovia SolutionI file and simulating it with a
        different workload (constant)'''
        with open('tests/sols/basic.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            sim_stats = sim.simulate_malloovia_workload_file(
                sol,
                workload_filename_prefix='tests/workloads/basic_short_sec_constant/wl',
                workload_period_sec=1,
                workload_length=24*3600,
                quantum_sec=3600,
                animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 72)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertEqual(sim_stats.avg_resp_time, 1200)
            self.assertEqual(sim_stats.max_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.cost, 0.24)
            self.assertEqual(sim_stats.util, 1)

    def test_no_request(self):
        '''Tests reading a Malloovia SolutionI file and simulating it with a
        different workload (constant) but with a workload_length so short that
        no request is completely processed'''
        import os
        print(f'cwd: {os.getcwd()}')
        with open('tests/sols/basic.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            sim_stats = sim.simulate_malloovia_workload_file(
                sol,
                workload_filename_prefix='tests/workloads/basic_short_sec_constant/wl',
                workload_period_sec=1,
                workload_length=8,
                quantum_sec=3600,
                animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 0)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertEqual(sim_stats.avg_resp_time, 0)
            self.assertEqual(sim_stats.max_resp_time, 0)
            self.assertAlmostEqual(sim_stats.cost, 2.2222222222222223e-05)
            self.assertEqual(sim_stats.util, 1)

    def test_lost(self):
        '''Tests a trace with this structure:
        - First hour, one request at the beginning.
        - Second hour, one request in the middle.
        - Third hour, one request starting just before the end and taking part of the
        next slot.
        - Fourth hour, nothing, appart from the request that didn't finish in the previous
        slot

        There are two apps because this is prepared to be run with the basic
        system used in tracing, but all the requests will be in the first app,
        so the second request is lost.
        '''
        with open('tests/sols/basic.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            sim_stats = sim.simulate_malloovia_workload_file(
                sol,
                workload_filename_prefix='tests/workloads/lost_sec/wl',
                workload_period_sec=1,
                workload_length=4*3600,
                quantum_sec=3600,
                animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 2)
            self.assertEqual(sim_stats.req_lost, 1)
            self.assertEqual(sim_stats.req_pending, 0)
            self.assertAlmostEqual(sim_stats.avg_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.max_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.cost, 0.043052777777789895)
            self.assertAlmostEqual(sim_stats.util, 0.14717670426331843654678300347592)

    def test_lost_with_trace(self):
        '''Similar to the previous test, but with trace enabled.
        '''
        with open('tests/sols/basic.p', 'rb') as f:
            # Capture stdout
            saved_stdout = sys.stdout
            try:
                out = io.StringIO()
                sys.stdout = out

                sol = pickle.load(f)

                sim = Simulator()

                sim_stats = sim.simulate_malloovia_workload_file(
                    sol,
                    workload_filename_prefix='tests/workloads/lost_sec/wl',
                    workload_period_sec=1,
                    workload_length=4*3600,
                    quantum_sec=3600,
                    animate=False, speed=0.1, trace=True)

            finally:
                sys.stdout = saved_stdout

                output = out.getvalue().strip()
                self.assertTrue(output.startswith('[0] prio:'))

                self.assertEqual(sim_stats.req_proc, 2)
                self.assertEqual(sim_stats.req_lost, 1)
                self.assertEqual(sim_stats.req_pending, 0)
                self.assertAlmostEqual(sim_stats.avg_resp_time, 1200)
                self.assertAlmostEqual(sim_stats.max_resp_time, 1200)
                self.assertAlmostEqual(sim_stats.cost, 0.043052777777789895)
                self.assertAlmostEqual(sim_stats.util, 0.14717670426331843654678300347592)

    def test_util(self):
        '''Tests a trace with this structure:
        - First hour, one request at the beginning.
        - Second hour, one request in the middle.
        - Third hour, one request starting just before the end and taking part
          of the next slot.
        - Fourth hour, nothing, appart from the request that didn't finish in
          the previous slot

        Each request takes 1/3 of the hour, and as there are 4 hours, the
        utilization should be close 0.25, but not exactly 0.25 because the
        second VM has a pending request that is extended over the next time
        slot.

        There are two apps because this is prepared to be run with the basic
        system used in tracing. The first and thrid requests will be in the
        first app and the second will be in the second app, because there is
        only one VM, for the first app in the first hour, one VM for the second
        app on the second hour, back to the first app in the third hour and so
        on.
        '''
        with open('tests/sols/basic.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            sim_stats = sim.simulate_malloovia_workload_file(
                sol,
                workload_filename_prefix='tests/workloads/util_sec/wl',
                workload_period_sec=1,
                workload_length=4*3600,
                quantum_sec=3600,
                animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 3)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertAlmostEqual(sim_stats.avg_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.max_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.cost, 0.04305277777777777)
            self.assertAlmostEqual(sim_stats.util,
                0.23051003759665176988011633680925)

    def test_util_from_list(self):
        '''This is similar to the test test_util but passes the workload in a
        list instead of using a file, so that function
        simulate_malloovia_workload() is tested.
        '''
        with open('tests/sols/basic.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            workloads = [
                # App0
                [1] + [0]*3599\
                    + [0]*3600\
                    + [0] * 3499 + [1] + [0]*100\
                    + [0]*3600,

                # App1
                [0]*3600\
                    + [0] * 99 + [1] + [0]*3500\
                    + [0]*3600\
                    + [0]*3600,
            ]

            sim_stats = sim.simulate_malloovia_workload(
                sol,
                workloads=workloads,
                workload_period_sec=1,
                workload_length=4*3600,
                quantum_sec=3600,
                animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 3)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertAlmostEqual(sim_stats.avg_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.max_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.cost, 0.04305277777777777)
            self.assertAlmostEqual(sim_stats.util,
                0.23051003759665176988011633680925)

    def test_util_033_from_list(self):
        '''Each VM has a request that takes 1/3, so the average should be 1/3.
        '''
        with open('tests/sols/basic.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            workloads = [
                # App0
                [1] + [0]*3599\
                    + [0]*3600\
                    + [0] * 1499 + [1] + [0]*2100\
                    + [0]*3600,

                # App1
                [0]*3600\
                    + [0] * 99 + [1] + [0]*3500\
                    + [0]*3600\
                    + [0] * 99 + [1] + [0]*3500,
            ]

            sim_stats = sim.simulate_malloovia_workload(
                sol,
                workloads=workloads,
                workload_period_sec=1,
                workload_length=4*3600,
                quantum_sec=3600,
                animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 4)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertAlmostEqual(sim_stats.avg_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.max_resp_time, 1200)
            self.assertAlmostEqual(sim_stats.cost, 0.04)
            self.assertAlmostEqual(sim_stats.util, 1/3)

    def test_basic_reserved_malloovia(self):
        '''Tests reading a Malloovia SolutionI file and simulating it. The
        solution uses reserved instances'''
        with open('tests/sols/basic_reserv.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            sim_stats = sim.simulate_malloovia(sol, workload_length=None,
                                    quantum_sec=3600,
                                    animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 26280)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertEqual(sim_stats.avg_resp_time, 2400)
            self.assertEqual(sim_stats.max_resp_time, 3600)
            self.assertAlmostEqual(sim_stats.cost, 175.2)
            self.assertEqual(sim_stats.util, 0.5)


class Test3vm(unittest.TestCase):
    def test_3vm_malloovia(self):
        '''Tests reading a Malloovia SolutionI file and simulating it'''
        with open('tests/sols/3vm.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            sim_stats = sim.simulate_malloovia(sol, workload_length=None,
                quantum_sec=3600, animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 12)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertEqual(sim_stats.avg_resp_time, 2400)
            self.assertEqual(sim_stats.max_resp_time, 3600)
            self.assertAlmostEqual(sim_stats.cost, 0.04)
            self.assertEqual(sim_stats.util, 1)

    def test_4pending_requests(self):
        '''There are 4 pending requests at the end of the first hour'''
        with open('tests/sols/3vm.p', 'rb') as f:
            sol = pickle.load(f)

            sim = Simulator()

            workloads = [
                # 1st hour: 4 requests that will be pending
                [0]*3000 + [4] + [0]*599\

                # 2nd hour
                + [0]*3600
            ]

            sim_stats = sim.simulate_malloovia_workload(
                sol,
                workloads=workloads,
                workload_period_sec=1,
                workload_length=2*3600,
                quantum_sec=3600,
                animate=False, speed=0.1, trace=False)

            self.assertEqual(sim_stats.req_proc, 4)
            self.assertEqual(sim_stats.req_lost, 0)
            self.assertEqual(sim_stats.avg_resp_time, (3*1200+2400)/4)
            self.assertEqual(sim_stats.max_resp_time, 2400)

            secs_running_vm_0 = 2*3600
            secs_running_vms_1_or_2 = 3600+600
            secs_used = secs_running_vm_0 + 2*secs_running_vms_1_or_2
            cost_per_sec = 0.01/3600
            self.assertAlmostEqual(sim_stats.cost, secs_used * cost_per_sec)

            u0 = 2*1200 / secs_running_vm_0
            u1 = 1200 / secs_running_vms_1_or_2
            u2 = 1200 / secs_running_vms_1_or_2
            self.assertAlmostEqual(sim_stats.util, (u0+u1+u2)/3)
