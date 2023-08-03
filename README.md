# 1 Introduction

Vrun is a regression management script based on VCS simulator.

It supports the following functions:

- VCS single compilation and simulation.
- VCS regression simulation.
- Regression list management.
- Dump waveform in *.vpd or *.fsdb.
- Randomize seed.
- Collect code coverage.

The following features are currently under development:

- Parallel simulation logic.
- Inheritable case list.

# 2 How to use vrun

## 2.1 setup.sh

Generally speaking, vrun will be stored in a separate folder as a tool. You need to create a setup.sh file in the corresponding project directory to let vrun know where the project directory is. 

This setup.sh file must in the root directory of your project.

```shell
export VCS_RUN=the/directory/of/vrun/script
export REPO_BASE=the/directory/of/the/project

alias vrun="python3 $VCS_RUN/vrun.py"
alias proj_run="vrun -cfg $REPO_BASE/the/directory/of/yaml -o $REPO_BASE/out"
alias cdr="cd $REPO_BASE"
alias cdo="cd $REPO_BASE/out"
```

## 2.2 YAML

You have to declare some necessary parameters to run the simulation in YAML form.

```yaml
- vcs: vcs command
  flist: >
    +incdir+$REPO_BASE
    +incdir+$REPO_BASE/{xxx,xxx,xxx,xxx,xxx}
    $REPO_BASE/xxx_pkg.sv
    $REPO_BASE/xxx_tb.sv
  top: xxx_top
  cmp_opts: your additional compile options
  elab_opts: your additional compile options
```

The regression list is also stored in the YAML file.

```yaml
- test: xxx_test
  seed: 123 or empty means random
  iterations: 1 or 5 or more
  sim_opts: your additional simulate options

- test: yyy_test
  seed: 123 or empty means random
  iterations: 1 or 5 or more
  sim_opts: your additional simulate options
```

The YAML file supports import syntax.

```yaml
- import: $REPO_BASE/xxx/xxx/xxx/sub.yaml
```

## 2.3 Example

After completing the writing of setup.sh and YAML configurations. You can use the following command to run you base test.

```shell
proj_run -test xxx_test
```

You also can compile and simulate the testbench separately.

```shell
proj_run -co
proj_run -test xxx_test -so
```

Furthermore, You can use `-vpd` or `-fsdb` to generate waveforms and use `-cov` to collect code coverage.

```shell
proj_run -test xxx_test -vpd
proj_run -test xxx_test -fsdb
proj_run -test xxx_test -cov
```