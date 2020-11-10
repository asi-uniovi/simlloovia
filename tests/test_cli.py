"Test the command line interface"
import os
import glob
import unittest

from click.testing import CliRunner
import pandas as pd

from simlloovia import cli, core


class TestCliModule(unittest.TestCase):
    """Test the command line interface"""

    def test_cli_no_evs_no_utils(self):
        """Test that the command line works with a simple simulation"""

        runner = CliRunner()
        result = runner.invoke(cli.simulate, ["--sol-file", "tests/sols/basic.p",
            "--output-prefix", "clitest", "--output-dir", ".",
            "--workload-length", "3600"])

        assert result.exit_code == 0

        files = glob.glob("clitest*")
        assert 'clitest.csv' in files
        assert 'clitest_out.txt' in files
        assert 'clitest_reqs.csv' not in files
        assert 'clitest_utils.csv' not in files

    def test_cli_with_evs(self):
        """Test that the command line works with a simple simulation"""

        runner = CliRunner()
        runner.echo_stdin = True
        result = runner.invoke(cli.simulate, ["--sol-file", "tests/sols/basic.p",
            "--output-prefix", "clitest", "--output-dir", ".",
            "--workload-length", "3600", "--save-evs", "true"])

        assert result.exit_code == 0

        files = glob.glob("clitest*")
        assert 'clitest.csv' in files
        assert 'clitest_out.txt' in files
        assert 'clitest_reqs.csv' in files
        assert 'clitest_utils.csv' not in files

        df = pd.read_csv('clitest_reqs.csv')
        assert len(df) == 10800

        req1_row = df.iloc[1]
        assert req1_row.req == 1
        assert req1_row.creation == 0
        assert req1_row.start == 1200
        assert req1_row.end == 2400
        assert req1_row.app == 'a0'
        assert req1_row.vm == 'VM 0'
        assert req1_row.ic == 'priv'
        assert req1_row.lost == False

    def test_cli_with_utils(self):
        """Test that the command line works with a simple simulation"""

        runner = CliRunner()
        runner.echo_stdin = True
        result = runner.invoke(cli.simulate, ["--sol-file", "tests/sols/basic.p",
            "--output-prefix", "clitest", "--output-dir", ".",
            "--workload-length", "3600", "--save-utils", "true"])

        assert result.exit_code == 0

        files = glob.glob("clitest*")
        assert 'clitest.csv' in files
        assert 'clitest_out.txt' in files
        assert 'clitest_evs.csv' not in files
        assert 'clitest_reqs.csv' not in files
        assert 'clitest_utils.csv' in files

        df = pd.read_csv('clitest_utils.csv')
        assert len(df) == 3600

        util0_row = df.iloc[0]
        assert util0_row.vm_name == 'VM 0'
        assert util0_row.ic == 'priv'
        assert util0_row.util == 1

        last_util_row = df.iloc[-1]
        assert last_util_row.vm_name == 'VM 3599'
        assert last_util_row.ic == 'priv'
        assert last_util_row.util == 1

    def test_cli_with_config_file(self):
        runner = CliRunner()
        runner.echo_stdin = True
        result = runner.invoke(cli.simulate, ["--config", "tests/config_test"])

        assert result.exit_code == 0

    def test_cli_yaml(self):
        """Test that the command line works with a YAML file"""

        runner = CliRunner()
        runner.echo_stdin = True
        result = runner.invoke(cli.simulate, ["--sol-file",
            "tests/sols/3vm.yaml", "--output-prefix", "clitest",
            "--output-dir", "."])

        assert result.exit_code == 0

    def setUp(self):
        core.Vm.count = 0

    def tearDown(self):
        files = glob.glob("clitest*")
        for f in files:
            os.remove(f)
