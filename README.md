# Simlloovia

Simulate transactional systems running on cloud infrastructure

## Introduction

Simlloovia is a Python package to simulate transactional systems running on cloud
infrastructure.

It uses [Malloovia](https://github.com/asi-uniovi/malloovia) as base to
represent the system to be simulated and Simpy as simulation engine.

To use:

- Clone the repository
- From the root of the repository, run this to install in the current
  environment:

    pip install -e .

- To run a simulation use the `simlloovia` command. For example:

```bash
simlloovia --sol-file=tests/sols/basic.p --output-prefix=test --output-dir=. --workload-length=3600 --save-evs=True
```

- Check the results in the files `test_out.txt` and `test_reqs.csv`.

- The parameters can also be passed with a configuration file using the option
`--config FILE`.

Run `simlloovia --help` for more options.

***

Free software: MIT license
