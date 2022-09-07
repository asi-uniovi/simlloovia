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

- Check the results in the files `test_out.txt` and `test_reqs.csv`. A dashboard
that summarizes the information graphically can be run with this command:

```bash
python dashboard_sim.py
```

- The parameters can also be passed with a configuration file using the option
`--config FILE`.

Run `simlloovia --help` for more options.

***

# Related publications

- Joaquín Entrialgo, Manuel García, José Luis Díaz, Javier García, Daniel F.
  García, "Modelling and simulation for cost optimization and performance
  analysis of transactional applications in hybrid clouds", In Simulation
  Modelling Practice and Theory, vol. 109, pp. 102311, 2021. (JCR 2021: 4.199.
        Q1)
        [[bibtext](http://www.atc.uniovi.es/joaquin-entrialgo/bibtexbrowser.php?key=entrialgo2021hybrid&bib=entrialgo.bib)]
        [[doi](http://dx.doi.org/https://doi.org/10.1016/j.simpat.2021.102311)]

  Please cite this work if you use `Simlloovia`. The paper describes the
  architecture of the simulator.

- Joaquín Entrialgo, José Luis Díaz, Javier García, Manuel García, Daniel F.
  García, "Cost Minimization of Virtual Machine Allocation in Public Clouds
  Considering Multiple Applications", In Economics of Grids, Clouds, Systems,
  and Services: 14th International Conference, GECON 2017, Biarritz, France,
  September 19-21, 2017, Proceedings, Springer International Publishing, Cham,
  pp. 147-161, 2017.
  [[bibtext](http://www.atc.uniovi.es/joaquin-entrialgo/bibtexbrowser.php?key=entrialgo2017malloovia&bib=entrialgo.bib)]
  [[doi](http://dx.doi.org/10.1007/978-3-319-68066-8_12)]

  This work describes `Malloovia`, which is used as base for `Simlloovia`.

***

Free software: MIT license
