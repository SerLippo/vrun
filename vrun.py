"""
File: vrun.py
Author: Ser_Lip
Description: Ser_Lip's vcs command script
TODO: >
    yaml optimize
    regr parallel logic
    other optimize
"""

import os
import re
import argparse
import subprocess
import logging
import yaml
import random
import datetime

class seedGen(object):
    """
    An object that will generate a pseudo-random seed for test iterations.

    Not used now!
    """
    def __init__(self, startSeed):
        self.startSeed = startSeed

    def get(self, testIter=0):
        return self.startSeed + testIter

    def getRand(self):
        return random.getrandbits(31)


def parseArgs(cwd):
    """
    Create a command line parser.

    Args:
        cwd : current work directory.

    Returns:
        args : command line parser.
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
    parser.add_argument("-v", "--verbose", type=str, default="UVM_LOW",
                                            help="The UVM verbose in simulation.", dest="v")
    parser.add_argument("-time", "--timeout", type=int, default=300,
                                            help="The command timeout limit.", dest="time")
    parser.add_argument("-co", "--compile_only", action="store_true", default=False,
                                            help="Compile the generator only.", dest="co")
    parser.add_argument("-so", "--simulate_only", action="store_true", default=False,
                                            help="Simulate the generator only.", dest="so")
    parser.add_argument("-copt", "--cmp_opts", type=str, default=None,
                                            help="Compile options for the generator.", dest="copt")
    parser.add_argument("-eopt", "--elab_opts", type=str, default=None,
                                            help="Elabration options for the generator.", dest="eopt")
    parser.add_argument("-sopt", "--sim_opts", type=str, default=None,
                                            help="Simulation options for the generator.", dest="sopt")
    parser.add_argument("-seed", "--seed", type=int, default=None,
                                            help="Randomize seed.", dest="seed")
    parser.add_argument("-iter", "--iterations", type=int, default=1,
                                            help="Test iterations.", dest="iter")
    parser.add_argument("-vpd", "--vpd", action="store_true", default=False,
                                            help="Enable DVE vpd dump.", dest="vpd")
    parser.add_argument("-fsdb", "--fsdb", action="store_true", default=False,
                                            help="Enable Verdi fsdb dump.", dest="fsdb")
    parser.add_argument("-cov", "--cov", action="store_true", default=False,
                                            help="Enable code coverage collect.", dest="cov")
    parser.add_argument("-clean", "--clean_output", action="store_true", default=False,
                                            help="Clean last run's output.", dest="clean")
    parser.add_argument("-st", "--show_tests", action="store_true", default=False,
                                            help="Show all test in this repo.", dest="st")
    parser.add_argument("-dstep", "--dve_step", action="store_true", default=False,
                                            help="Simulation in DVE step mode.", dest="dstep")
    parser.add_argument("-vstep", "--verdi_step", action="store_true", default=False,
                                            help="Simulation in Verdi step mode.", dest="vstep")
    args = parser.parse_args()

    if not args.cfg:
        args.cfg = cwd + "/cfg/vcs.yaml"
    if not os.path.isfile(args.cfg):
        logging.error("Didn't find vcs script's config.")
        raise Exception("<Config Error> Please check '--config' or '-cfg' option.")
    if args.test is not None and args.regr is not None:
        logging.error("Single case mode and Regression mode is not compatible.")
        raise Exception("<Config Error> This Script can't have -test & -regr both.")
    if not args.o:
        args.o = cwd + "/out"
    if args.co and args.so:
        logging.error("--compile_only and --simulate_only is not compatible.")
        raise Exception("<Config Error> This Script can't have -co & -so both.")
    if args.seed is not None and args.seed < 0:
        raise ValueError("<Config Error> Seed must be a non-negative integer.")
    return args


def runCmd(cmd, tmoutSecond=600, exitOnError=True):
    """
    Run command with timeout limit and return output.

    Args:
        cmd : command to run.
        tmoutSecond : timeout in second.
        exitOnError : whether exit the script when command errors.

    Return :
        output : command output.
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
        raise Exception("<Command Error> Subprocess running failed.")
    except KeyboardInterrupt:
        logging.debug("\nExited Ctrl-C from user request.")
        raise KeyboardInterrupt("<Keyboard Error> Exited Ctrl+C from user request.")
    try:
        output = ps.communicate(timeout=tmoutSecond)[0]
    except subprocess.TimeoutExpired:
        logging.error("Timeout[%ds]: %s"%(tmoutSecond, cmd))
        output = ""
        ps.kill()
        raise Exception("<Command Error> Subprocess timeout.")
    rc = ps.returncode
    if rc and rc > 0:
        logging.debug(output)
        logging.error("Error return code: %s"%rc)
        if exitOnError:
            raise Exception("<Command Error> Subprocess running failed with return code: %s."%rc)
    logging.debug(output)
    return output


def readYaml(yamlFile):
    """
    Read YAML file to a dictionary

    Args:
        yamlFile : YAML file

    Returns:
        yamlData : data read from YAML in dictionary format
    """
    with open(yamlFile, "r") as f:
            try:
                    yamlData = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                    logging.error(exc)
                    raise Exception("<YAML Error> YAML data error.")
    return yamlData


def createOutput(output, clean, prefix="out_"):
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


def loadConfig(args, cfg, vcsOpts, testList):
    """
    Extract script config from YAML.

    Args :
        args : command line parser.
        vcsOpts : vcs options data.
        testList : test list extracted from YAML.

    Returns :
        Nothing
    """
    yamlData = readYaml(cfg)
    global vcsOptCnt
    for entry in yamlData:
        if "import" in entry:
            loadConfig(args, os.path.expandvars(entry['import']), vcsOpts, testList)
        elif "vcs" in entry:
            vcsOpts.update(entry)
            vcsOptCnt += 1
            if vcsOptCnt > 1:
                logging.error("Found more than 1 vcsOpts entry in config.")
                raise Exception("<YAML Error> More than 1 vcsOpts in YAML.")
            if "flist" not in entry:
                logging.error("Didn't find flist in vcsOpts.")
                raise Exception("<YAML Error> Didn't find flist in YAML.")
            # Compile options
            cmpOpts = ""
            if args.copt is not None:
                cmpOpts += " " + args.copt
            elif "cmp_opts" in entry:
                cmpOpts += " " + entry["cmp_opts"]
            vcsOpts["cmp_opts"] = cmpOpts
            # Elaboration options
            elabOpts = ""
            if args.eopt is not None:
                elabOpts += " " + args.eopt
            elif "elab_opts" in entry:
                elabOpts += " " + entry["elab_opts"]
            vcsOpts["elab_opts"] = elabOpts
        elif "test" in entry:
            testList.append(entry)


def getEnvVar(var):
    """
    Get the value of environment variable

    Args:
        var : Name of the environment variable

    Returns:
        val : Value of the environment variable
    """
    try:
        val = os.environ[var]
    except KeyError:
        logging.warning("Please set the environment variable {}".format(var))
        raise KeyError("<Key Error> Didn't find environment value with key {}.".format(var))
    return val


def loadRegrList(regr, regrList):
    """
    Extract regression list from file.

    Args:
        regr : regression list path.
        regrList : test list extracted from regression list.

    Returns :
        Nothing
    """
    yamlData = readYaml(regr)
    for entry in yamlData:
        if "test" in entry:
            regrList.append(entry)


def processVCS(args, vcsOpts, matchedList, outputDir):
    """
    Run the simulator.

    Args:
        args : command line parser.
        vcsOpts : vcs options data.
        matchedList : test to run.
        outputDir : output directory.

    Returns:
        Nothing
    """
    global isSimed
    global errorCnt
    if args.co is False and len(matchedList) == 0:
        return
    vloganCmd = ("vlogan -full64 -sverilog -lca -ntb_opts uvm-1.2 -timescale=1ns/1ps -kdb "
                                "-l %s/compile/vlogan.log" % outputDir)
    vcsCmd = ("vcs -full64 -sverilog -lca -ntb_opts uvm-1.2 -partcomp -kdb "
                         "-CFLAGS '--std=c99 -fno-extended-identifiers' "
                         "-LDFLAGS '-Wl,--no-as-needed' -debug_acc+all "
                         "-l %s/compile/vcs.log -o %s/compile/vcs.simv" % (outputDir, outputDir))
    simCmd = "%s/compile/vcs.simv +UVM_VERBOSITY=%s" % (outputDir, args.v)

    if not args.so:
        cmp_output = createOutput(outputDir+"/compile", args.clean)
        os.chdir(cmp_output)
        logging.info("------ Starting vlogan UVM ------")
        runCmd(vloganCmd, args.time)
        vloganCmd = vloganCmd + " " + vcsOpts["flist"].strip("\n")
        logging.info("------ Starting vlogan ------")
        with open("vlogan.sh", "w") as f:
            f.write(vloganCmd)
        runCmd(vloganCmd, args.time)
        logging.info("------ Finished ------")
        vcsCmd = vcsCmd + " -top %s" % vcsOpts["top"].strip("\n")
        if args.cov:
            vcsCmd += " -cm line+tgl+fsm+cond+branch+assert -cm_cond allops -cm_dir %s/cov.vdb" % outputDir
        logging.info("------ Starting vcs ------")
        with open("vcs.sh", "w") as f:
            f.write(vcsCmd)
        runCmd(vcsCmd, args.time)
        logging.info("------ Finished ------")
    if not args.co:
        for test in matchedList:
            isSimed = True
            for i in range(test["iterations"]):
                if i != 0:
                    test["seed"] = random.getrandbits(31)
                simOutput = createOutput(outputDir+"/"+test["test"]+"_%s"%test["seed"], True)
                os.chdir(simOutput)
                if "uvm_test" in test:
                    simTestCmd = simCmd + " +UVM_TESTNAME=%s" % test["uvm_test"]
                else:
                    simTestCmd = simCmd + " +UVM_TESTNAME=%s" % test["test"]
                simTestCmd += " -ntb_random_seed=%d -l %s/sim.log" % (test["seed"], simOutput)
                if args.vpd or args.fsdb:
                    simTestCmd += " -ucli -do %s/sim.tcl" % simOutput
                    if args.vpd:
                        simTestCmd += " -vpd_file %s/sim.vpd" % simOutput
                    if args.fsdb:
                        simTestCmd += " +fsdb+autoflush +fsdb+all +fsdb+mda"
                if test["sim_opts"] != "":
                    simTestCmd += test["sim_opts"].strip("\n")
                with open("sim.tcl", "w") as f:
                    if args.vpd:
                        f.write("dump -add /*\n")
                    if args.fsdb:
                        f.write("fsdbDumpfile \"sim.fsdb\"\n")
                        f.write("fsdbDumpvars 0 %s\n" % vcsOpts["top"].strip("\n"))
                    if not(args.dstep or args.vstep):
                        f.write("run")
                if args.cov:
                    simTestCmd += " -cm line+tgl+fsm+cond+branch+assert -cm_cond allops"
                    simTestCmd += " -cm_name %s_%s" % (test["test"], test["seed"])
                logging.info("------ Starting sim ------")
                with open("sim.sh", "w") as f:
                    f.write(simTestCmd)
                runCmd(simTestCmd, args.time)
                with open("sim.log", "r") as f:
                    em = open("error_message.log", "w")
                    wm = open("warning_message.log", "w")
                    for line in f.readlines():
                        if line.startswith("UVM_ERROR") or line.startswith("UVM_FATAL") or "Error" in line:
                            if line != "UVM_ERROR :    0\n" and line != "UVM_FATAL :    0\n":
                                em.write(line)
                        elif line.startswith("UVM_WARNING"):
                            if line != "UVM_WARNING :    0\n":
                                wm.write(line)
                    em.close()
                    wm.close()
                    if os.path.getsize("error_message.log") == 0:
                        with open("PASS", "w") as fp:
                            fp.write("PASS")
                    else:
                        with open("FAIL", "w") as ff:
                            ff.write("FAIL")
                            errorCnt += 1
                logging.info("------ Finished ------")


def organizeTest(testname, testList, matchTest):
    """
    origin test because of extends.

    Args:
        entry : leaf test.
        testList : all test.
    """
    testHit = False
    for entry in testList:
        if testname == entry["test"]:
            testHit = True
            if "sim_opts" not in entry:
                entry["sim_opts"] = ""
            if "extends" in entry:
                fatherTest = {}
                organizeTest(entry["extends"], testList, fatherTest)
                father = fatherTest
                father["sim_opts"] = father["sim_opts"].strip("\n")
                entry["sim_opts"] = entry["sim_opts"].strip("\n")
                father["sim_opts"] = father["sim_opts"].strip()
                entry["sim_opts"] = entry["sim_opts"].strip()
                f_dict = {}
                e_dict = {}
                for f_opt in re.split(r"[ ]+", father["sim_opts"]):
                    f_dict[f_opt.split("=")[0]] = f_opt.split("=")[1]
                for e_opt in re.split(r"[ ]+", entry["sim_opts"]):
                    e_dict[e_opt.split("=")[0]] = e_opt.split("=")[1]
                for param in father:
                    if param == "test" or param == "extends":
                        continue
                    elif param == "sim_opts":
                        for key in f_dict:
                            if key not in e_dict:
                                e_dict[key] = f_dict[key]
                        entry["sim_opts"] = ""
                        for key in e_dict:
                            entry["sim_opts"] += key + "=" + e_dict[key] + " "
                    else:
                        if param not in entry:
                            entry[param] = father[param]
                matchTest.update(entry)
            else:
                matchTest.update(entry)
    if not testHit:
        logging.error("No testname: %s found in test list!" % testname)
        raise Exception("Test not found.")

def extractTest(args, testList, matchedList):
    """
    extractTest for matched list.

    Args:
        args : command line parser.
        testList : test list extracted from YAML.
        matchedList : test to run.

    Returns:
        Nothing
    """
    if args.test is not None:
        matchTest = {}
        organizeTest(args.test, testList, matchTest)
        # Seed
        if args.seed is not None:
            matchTest["seed"] = args.seed
        elif "seed" not in matchTest:
            matchTest["seed"] = random.getrandbits(31)
        # UVM Test
        # Iterations
        if args.iter > 1:
            matchTest["iterations"] = args.iter
        elif "iterations" not in matchTest:
            matchTest["iterations"] = args.iter
        # Simulation options
        simOpts = ""
        if args.sopt is not None:
            simOpts += " " + args.sopt
        elif "sim_opts" in matchTest:
            simOpts += " " + matchTest["sim_opts"]
        if args.dstep:
            simOpts += " " + "-gui"
        if args.vstep:
            simOpts += " " + "-gui=verdi"
        matchTest["sim_opts"] = simOpts
        matchedList.append(matchTest)

    elif args.regr is not None:
        regrList = []
        loadRegrList(args.regr, regrList)
        for regrEntry in regrList:
            matchTest = {}
            organizeTest(regrEntry["test"], testList, matchTest)
            # Seed
            if args.seed is not None:
                matchTest["seed"] = args.seed
            elif "seed" in regrEntry:
                matchTest["seed"] = regrEntry["seed"]
            elif "seed" not in matchTest:
                matchTest["seed"] = random.getrandbits(31)
            # UVM Test
            # Iterations
            if args.iter > 1:
                matchTest["iterations"] = args.iter
            elif "iterations" in regrEntry:
                matchTest["iterations"] = regrEntry["iterations"]
            elif "iterations" not in matchTest:
                matchTest["iterations"] = args.iter
            # Simulation options
            simOpts = ""
            if args.sopt is not None:
                simOpts += " " + args.sopt
            elif "sim_opts" in regrEntry:
                simOpts += " " + regrEntry["sim_opts"]
            elif "sim_opts" in matchTest:
                simOpts += " " + matchTest["sim_opts"]
            matchTest["sim_opts"] = simOpts
            matchedList.append(matchTest)


# Global Status
isSimed = False
vcsOptCnt = 0
errorCnt = 0
def main():
    """
    This is the main program.
    """
    try:
        vcsOpts = {}
        testList = []
        matchedList = []

        cwd = os.getcwd()
        FORMAT = "%(asctime)-15s %(levelname)s: %(message)s"
        logging.basicConfig(format=FORMAT,level=logging.INFO)
        args = parseArgs(cwd)
        logging.info("Starting to run VCS script in directory: %s" % cwd)
        logging.info("Output directory is %s" % os.path.expandvars(args.o))
        outputDir = createOutput(args.o, args.clean)

        loadConfig(args, args.cfg, vcsOpts, testList)
        if args.st:
            testNum = 0
            logging.info("The tests that can be executed are:")
            for entry in testList:
                logging.info("%d: %s"%(testNum, entry["test"]))
                testNum += 1

        extractTest(args, testList, matchedList)
        logging.info("Tests that is going to be processed are:")
        for test in matchedList:
            logging.info(test)

        processVCS(args, vcsOpts, matchedList, outputDir)

        if isSimed:
            if errorCnt == 0:
                logging.info("\n" + "\033[0;32m" +
"~~~~~~~~~~~~~~~~~~~ TEST_PASS ~~~~~~~~~~~~~~~~~~~\n" +
"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n" +
"~~~~~~~~~ #####     ##     ####    #### ~~~~~~~~~\n" +
"~~~~~~~~~ #    #   #  #   #       #     ~~~~~~~~~\n" +
"~~~~~~~~~ #    #  #    #   ####    #### ~~~~~~~~~\n" +
"~~~~~~~~~ #####   ######       #       #~~~~~~~~~\n" +
"~~~~~~~~~ #       #    #  #    #  #    #~~~~~~~~~\n" +
"~~~~~~~~~ #       #    #   ####    #### ~~~~~~~~~\n" +
"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\033[0m\n")
            else:
                logging.critical("\n" + "\033[0;31m"
"~~~~~~~~~~~~~~~~~~~ TEST_FAIL ~~~~~~~~~~~~~~~~~~~~\n", +
"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n", +
"~~~~~~~~~~######    ##       #    #     ~~~~~~~~~~\n", +
"~~~~~~~~~~#        #  #      #    #     ~~~~~~~~~~\n", +
"~~~~~~~~~~#####   #    #     #    #     ~~~~~~~~~~\n", +
"~~~~~~~~~~#       ######     #    #     ~~~~~~~~~~\n", +
"~~~~~~~~~~#       #    #     #    #     ~~~~~~~~~~\n", +
"~~~~~~~~~~#       #    #     #    ######~~~~~~~~~~\n", +
"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\033[0m\n")

    except KeyboardInterrupt:
        logging.info("\nExited Ctrl+C from user request.")
        raise KeyboardInterrupt("<Keyboard Error> Exited Ctrl+C from user request.")


if __name__ == "__main__":
    main()