import mock
import unittest

import simpy
from simpy.core import Environment

from malloovia import InstanceClass, App, PerformanceSet, PerformanceValues

from simlloovia.core import (Vm, Monitor, VmManager, RequestSink, LoadBalancer,
    Request)

class Test_Vm(unittest.TestCase):
    def __set_up(self, cores, app_perf):
        self.ic = InstanceClass(
            "ic", name="ic",
            limiting_sets=None, is_reserved=False,
            price=0.1, time_unit='h', max_vms=20, cores=cores)

        self.app = App(id='a', name='a')
        self.perfs = PerformanceSet(
            id="example_perfs",
            time_unit="s",
            values=PerformanceValues({
                self.ic: {self.app: app_perf},
                })
        )

        self.env = simpy.Environment()

        self.monitor = mock.create_autospec(Monitor)
        self.request_sink = mock.create_autospec(RequestSink)
        self.load_balancer = mock.create_autospec(LoadBalancer)
        self.vm_manager = mock.create_autospec(VmManager)

    def test_1_req_1_core_1_perf(self):
        self.__set_up(cores=1, app_perf=1)
        vm = Vm(self.env, ic=self.ic, perfs=self.perfs, out=self.request_sink,
            load_balancer=self.load_balancer, monitor=self.monitor,
            quantum_sec=0.1)

        vm.assign_app(self.app)

        req = Request(self.env, self.app)
        vm.add_request(req)

        self.env.run()

        self.assertAlmostEqual(req.response_time, 1)

    def test_2_req_1_core_1_perf(self):
        self.__set_up(cores=1, app_perf=1)
        vm = Vm(self.env, ic=self.ic, perfs=self.perfs, out=self.request_sink,
            load_balancer=self.load_balancer, monitor=self.monitor,
            quantum_sec=0.1)

        vm.assign_app(self.app)

        req1 = Request(self.env, self.app)
        vm.add_request(req1)

        req2 = Request(self.env, self.app)
        vm.add_request(req2)

        self.env.run()

        self.assertAlmostEqual(req1.response_time, 1.9)
        self.assertAlmostEqual(req2.response_time, 2)

    def test_1_req_2_cores_1_perf(self):
        self.__set_up(cores=2, app_perf=1)
        vm = Vm(self.env, ic=self.ic, perfs=self.perfs, out=self.request_sink,
            load_balancer=self.load_balancer, monitor=self.monitor,
            quantum_sec=0.1)

        vm.assign_app(self.app)

        req = Request(self.env, self.app)
        vm.add_request(req)

        self.env.run()

        self.assertAlmostEqual(req.response_time, 2)

    def test_2_req_2_cores_1_perf(self):
        self.__set_up(cores=2, app_perf=1)
        vm = Vm(self.env, ic=self.ic, perfs=self.perfs, out=self.request_sink,
            load_balancer=self.load_balancer, monitor=self.monitor,
            quantum_sec=0.1)

        vm.assign_app(self.app)

        req1 = Request(self.env, self.app)
        vm.add_request(req1)

        req2 = Request(self.env, self.app)
        vm.add_request(req2)

        self.env.run()

        self.assertAlmostEqual(req1.response_time, 2)
        self.assertAlmostEqual(req2.response_time, 2)


    def test_1_req_2_cores_4_perf(self):
        self.__set_up(cores=2, app_perf=4)
        vm = Vm(self.env, ic=self.ic, perfs=self.perfs, out=self.request_sink,
            load_balancer=self.load_balancer, monitor=self.monitor,
            quantum_sec=0.1)

        vm.assign_app(self.app)

        req = Request(self.env, self.app)
        vm.add_request(req)

        self.env.run()

        self.assertAlmostEqual(req.response_time, 0.5)

    def test_2_req_2_cores_4_perf(self):
        self.__set_up(cores=2, app_perf=4)
        vm = Vm(self.env, ic=self.ic, perfs=self.perfs, out=self.request_sink,
            load_balancer=self.load_balancer, monitor=self.monitor,
            quantum_sec=0.1)

        vm.assign_app(self.app)

        req1 = Request(self.env, self.app)
        vm.add_request(req1)

        req2 = Request(self.env, self.app)
        vm.add_request(req2)

        self.env.run()

        self.assertAlmostEqual(req1.response_time, 0.5)
        self.assertAlmostEqual(req2.response_time, 0.5)

    def test_4_req_2_cores_4_perf(self):
        self.__set_up(cores=2, app_perf=4)
        vm = Vm(self.env, ic=self.ic, perfs=self.perfs, out=self.request_sink,
            load_balancer=self.load_balancer, monitor=self.monitor,
            quantum_sec=0.1)

        vm.assign_app(self.app)

        req1 = Request(self.env, self.app)
        vm.add_request(req1)

        req2 = Request(self.env, self.app)
        vm.add_request(req2)

        req3 = Request(self.env, self.app)
        vm.add_request(req3)

        req4 = Request(self.env, self.app)
        vm.add_request(req4)

        self.env.run()

        self.assertAlmostEqual(req1.response_time, 0.9)
        self.assertAlmostEqual(req2.response_time, 0.9)
        self.assertAlmostEqual(req3.response_time, 1)
        self.assertAlmostEqual(req4.response_time, 1)
