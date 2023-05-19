"""
File: vcs.py
Author: Ser_Lip
Description: Ser_Lip's vcs command script
TODO: >
  vcs vlogan,vcs,sim opts logic
  yaml optimize
  regr logic
  other optimize
"""

import os
import sys
import argparse
import subprocess
import logging
import yaml
import random
import datetime

class seedGen(object):
  """
  An object that will generate a pseudo-random seed for test iterations.
  """
  def __init__(self, start_seed):
    self.start_seed = start_seed

  def get(self, test_iter=0):
    return self.start_seed + test_iter

  def getRand(self):
    return random.getrandbits(31)


def parse_args(cwd):
  """
  Create a command line parser.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument("-cfg", "--config", type=str,
                      help="Script config in YAML, include file list and vcs args.", dest="cfg")
  parser.add_argument("-test", "--testcase", type=str,
                      help="The UVM TESTNAME to run.", dest="test")
  parser.add_argument("-regr", "--regression", type=str,
                      help="The regression list to run.", dest="regr")
  parser.add_argument("-o", "--output", type=str,
                      help="Output directory path.", dest="o")
  parser.add_argument("-v", "--verbose", type=str, default="UVM_HIGH",
                      help="The UVM verbose in simulation.")
  parser.add_argument("-time", "--timeout", type=int, default=300,
                      help="The command timeout limit.", dest="time")
  parser.add_argument("-co", "--compile_only", action="store_true", default=False,
                      help="Compile the generator only.", dest="co")
  parser.add_argument("-so", "--simulate_only", action="store_true", default=False,
                      help="Simulate the generator only.", dest="so")
  parser.add_argument("-copt", "--cmp_opts", type=str, default="",
                        help="Compile options for the generator.")
  parser.add_argument("-sopt", "--sim_opts", type=str, default="",
                      help="Simulation options for the generator.")
  parser.add_argument("-seed", "--seed", type=int, default=None,
                      help="Randomize seed.", dest="seed")
  parser.add_argument("-iter", "--iterations", type=int, default=1,
                      help="Test iterations.", dest="iter")
  parser.add_argument("-clean", "--clean_output", action="store_true", default=False,
                      help="Clean last run's output.", dest="clean")
  args = parser.parse_args()

  if not args.cfg:
    args.cfg = cwd + "/cfg/vcs.yaml"
  if not os.path.isfile(args.cfg):
    logging.error("Didn't find vcs script's config. Please check '--config' option.")
    sys.exit(1)
  if args.test is not None and args.regr is not None:
    logging.error("Single case mode and Regression mode is not compatible.")
    sys.exit(1)
  if not args.o:
    args.o = cwd + "/out"
  if args.co and args.so:
    logging.error("--compile_only and --simulate_only is not compatible.")
    sys.exit(1)
  if args.seed is not None and args.seed < 0:
    raise ValueError("Seed must be a non-negative integer.")
  return args


def run_cmd(cmd, timeout_s=600, exit_on_error=True):
  """
  Run command with timeout limit and return output.
  """
  logging.info(cmd)
  try:
    ps = subprocess.Popen(
      "exec " + cmd,
      shell=True,
      executable='/bin/bash',
      universal_newlines=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT
    )
  except subprocess.CalledProcessError:
    logging.error(ps.commuicate()[0])
    sys.exit(1)
  except KeyboardInterrupt:
    logging.debug("\nExited Ctrl-C from user request.")
    sys.exit(1)
  try:
    output = ps.communicate(timeout=timeout_s)[0]
  except subprocess.TimeoutExpired:
    logging.error("Timeout[%ds]: %s"%(timeout_s, cmd))
    output = ""
    ps.kill()
    sys.exit(1)
  rc = ps.returncode
  if rc and rc > 0:
    logging.debug(output)
    logging.error("Error return code: %s"%rc)
    if exit_on_error:
      sys.exit(1)
  logging.debug(output)
  return output


def read_yaml(yaml_file):
  """
  Read YAML file to a dictionary

  Args:
    yaml_file : YAML file

  Returns:
    yaml_data : data read from YAML in dictionary format
  """
  with open(yaml_file, "r") as f:
      try:
          yaml_data = yaml.safe_load(f)
      except yaml.YAMLError as exc:
          logging.error(exc)
          sys.exit(1)
  return yaml_data


def create_output(output, clean, prefix="out_"):
  """
  Create output directory

  Args:
    output : Name of specified output directory
    noclean: Do not clean the output of the previous runs

  Returns:
    Output directory
  """
  # Create output directory
  if output is None:
    output = prefix + str(datetime.date.today())
  if clean is True:
    os.system("rm -r {}".format(output))

  logging.info("Creating output directory: %s" % output)
  subprocess.run(["mkdir", "-p", output])
  return output


flist_cnt = 0
def load_config(cfg, vcs_opts, test_list):
  """
  Extract script config from YAML.
  """
  yaml_data = read_yaml(cfg)
  global flist_cnt
  for entry in yaml_data:
    if "import" in entry:
      load_config(os.path.expandvars(entry['import']), vcs_opts, test_list)
    elif "vcs" in entry:
      vcs_opts.update(entry)
      flist_cnt += 1
      if flist_cnt > 1:
        logging.error("Found more than one flist entry in config.")
        sys.exit(1)
      if "flist" not in entry:
        logging.error("Didn't find flist in vcs_opts.")
        sys.exit(1)
    elif "test" in entry:
      test_list.append(entry)


def get_env_var(var, debug_cmd=None):
    """Get the value of environment variable

    Args:
      var : Name of the environment variable

    Returns:
      val : Value of the environment variable
    """
    try:
        val = os.environ[var]
    except KeyError:
        if debug_cmd:
            return var
        else:
            logging.warning("Please set the environment variable {}".format(var))
            sys.exit(1)
    return val


def load_regression_list(regr, regr_list):
  """
  Extract regression list from file.
  """
  yaml_data = read_yaml(regr)
  for entry in yaml_data:
    if "test" in entry:
      regr_list.append(entry)


def gen(matched_list, vcs_opts, args, output_dir, cwd):
  """
  Run the simulator.
  """
  if args.co is False and len(matched_list) == 0:
    return
  vlogan_cmd = ("vlogan -full64 -sverilog -lca -ntb_opts uvm-1.2 -timescale=1ps/1ps "
                "-l %s/compile/vlogan.log" % output_dir)
  vcs_cmd = ("vcs -full64 -sverilog -lca -ntb_opts uvm-1.2 -partcomp "
             "-CFLAGS '--std=c99 -fno-extended-identifiers' "
             "-LDFLAGS '-Wl,--no-as-needed' -debug_acc+all "
             "-l %s/compile/vcs.log -o %s/compile/vcs.simv" % (output_dir, output_dir))
  sim_cmd = "%s/compile/vcs.simv " % output_dir

  if not args.so:
    cmp_output = create_output(output_dir+"/compile", args.clean)
    os.chdir(cmp_output)
    run_cmd(vlogan_cmd, args.time)
    #with open("%s/f.lst" % cwd, "w") as f:
    #  f.write("%s" % vcs_opts["flist"])
    vlogan_cmd = vlogan_cmd + " " + vcs_opts["flist"]
    logging.info("------ Starting vlogan ------")
    run_cmd(vlogan_cmd, args.time)
    logging.info("------ Finished ------:")
    vcs_cmd = vcs_cmd + " -top mcdf_tb"
    logging.info("------ Starting vcs ------")
    run_cmd(vcs_cmd, args.time)
    logging.info("------ Finished ------:")
  if not args.co:
    for test in matched_list:
      for i in range(test["iterations"]):
        if i != 0:
          test["seed"] = random.getrandbits(31)
        sim_output = create_output(output_dir+"/"+test["test"]+"_%s"%test["seed"], args.clean)
        os.chdir(cmp_output)
        sim_test_cmd = sim_cmd + "+UVM_TESTNAME=%s -l %s/sim.log" % (test["test"], sim_output)
        logging.info("------ Starting sim ------")
        run_cmd(sim_test_cmd, args.time)
        logging.info("------ Finished ------:")



def main():
  """
  This is the main entry point.
  """
  try:
    #cwd = os.path.dirname(os.path.realpath(__file__))
    cwd = os.getcwd()
    args = parse_args(cwd)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logging.info("Starting to run VCS script in cwd:\n%s" % cwd)
    if args.seed is not None:
      mainSeed = seedGen(args.seed)
    else:
      mainSeed = seedGen(0)
    output_dir = create_output(args.o, args.clean)

    vcs_opts = {}
    test_list = []
    load_config(args.cfg, vcs_opts, test_list)

    matched_list = []
    if args.test is not None:
      for entry in test_list:
        if entry["test"] == args.test:
          matched_list.append(entry)
          if args.seed is not None:
            matched_list[-1]["seed"] = mainSeed.get()
          elif "seed" in entry:
            matched_list[-1]["seed"] = entry["seed"]
          else:
            matched_list[-1]["seed"] = mainSeed.getRand()
          if args.iter != 0:
            matched_list[-1]["iterations"] = args.iter
          elif "iterations" in entry:
            matched_list[-1]["iterations"] = entry["iterations"]
          else:
            matched_list[-1]["iterations"] = 1
    elif args.regr is not None:
      regr_list = []
      load_regression_list(args.regr, regr_list)
      for entry in test_list:
        for regr_entry in regr_list:
          if entry["test"] == regr_entry["test"]:
            matched_list.append(entry)
            if args.seed is not None:
              matched_list[-1]["seed"] = mainSeed.get()
            elif "seed" in regr_entry:
              matched_list[-1]["seed"] = regr_entry["seed"]
            elif "seed" in entry:
              matched_list[-1]["seed"] = entry["seed"]
            else:
              matched_list[-1]["seed"] = mainSeed.getRand()
            if args.iter != 1:
              matched_list[-1]["iterations"] = args.iter
            elif "iterations" in regr_entry:
              matched_list[-1]["iterations"] = regr_entry["iterations"]
            elif "iterations" in entry:
              matched_list[-1]["iterations"] = entry["iterations"]
            else:
              matched_list[-1]["iterations"] = 1

    gen(matched_list, vcs_opts, args, output_dir, cwd)

  except KeyboardInterrupt:
    logging.info("\nExited Ctrl+C from user request.")
    sys.exit(1)

if __name__ == "__main__":
  main()