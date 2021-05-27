import sys
import json
import os
import logging
import subprocess
import tempfile
import threading
import time
import traceback
from collections import defaultdict
from typing import List, Dict

from .format_answerset import PlanFormatter


class Plan:
    def __init__(self, answerset):
        self.answerset = answerset
        self.cost = answerset['cost']
        self.atoms = answerset['atoms']

    def log(self):
        logging.info("Plan:")
        planformatter = PlanFormatter()
        planformatter.print_plan(self.answerset)
        bypred = defaultdict(list)
        for atm in self.atoms:
            if isinstance(atm, str):
                bypred[atm].append(())
            else:
                bypred[atm['name']].append(atm['args'])
        [
            logging.info("  predicate '{}': extension {}, e.g., {}".format(
                pred, len(atms), repr(atms[0])
            ))
            for pred, atms in bypred.items()
        ]

    def __str__(self):
        return 'Answer set of cost {}\n  Atoms = {}'.format(self.cost, self.atoms)


class StderrCollectorThread(threading.Thread):
    def __init__(self, in_stream):
        super().__init__()
        self.in_stream = in_stream
        self.start()

        self.messages = []
        self.jsons = []

    def run(self):
        line = None
        try:
            line = self.in_stream.readline()
            while line != '' and not self.in_stream.closed:
                # logging.info("STDERR %s", line[:-1])
                if line.startswith('{'):
                    try:
                        self.jsons.append(json.loads(line))
                    except Exception:
                        self.messages.append(line.strip())
                else:
                    self.messages.append(line.strip())
                    # also echo to stderr
                    sys.stderr.write(line)
                    sys.stderr.flush()

                # get next line
                line = self.in_stream.readline()
        except Exception:
            logging.error("StderrCollectorThread died with %s, line=%s", traceback.format_exc(), line)
        # logging.debug("StderrCollectorThread stopped %d", self.in_stream.closed)


class HEXOWLAPIRunner:
    def __init__(
        self,
        hexlite_path='/opt/bin/hexlite',
        pluginpath_builtin='/opt/hexlite/plugins',
        pluginpath_extra='/app/ai4industry/hexplugins',
        # . is part of the classpath for log4j2.xml
        java_classpath='.:/opt/hexlite/java-api/target/hexlite-java-plugin-api-1.4.0.jar:'
            '/opt/hexlite-owlapi-plugin/plugin/target/owlapiplugin-1.1.0.jar'
    ):
        self.hexlite_path = hexlite_path
        self.pluginpath_builtin = pluginpath_builtin
        self.pluginpath_custom = pluginpath_extra
        self.java_classpath = java_classpath
        self.cmdline_arguments = None

    def _readfile(self, file_name):
        with open(file_name, 'rt') as inf:
            return inf.read()

    def _write_temp_file(self, horizon, ontology_meta_json, facts: List[str] = [], rules: List[str] = []):
        with tempfile.NamedTemporaryFile(mode='w+t', delete=False) as outf:
            outf.write("#const maxTime={}.\n".format(horizon))
            outf.write('#const onto="{}".\n'.format(ontology_meta_json))
            outf.write('\n')
            outf.write('\n'.join([x + '.' for x in facts]))
            outf.write('\n')
            outf.write('\n'.join(rules))
            outf.write('\n')
            return outf.name

    def _generate_initial_facts(self, initial, number_of_items_in_goal):
        facts = []
        idx = 0
        for storage, contents in initial.items():
            cnt = [
                'matidx("{}",{})'.format(mat, idx + lidx)
                for lidx, mat in enumerate(contents)
                if lidx < number_of_items_in_goal  # limit number of items in storage to number of items in goal - we can never need more
            ]
            idx += len(cnt)
            if len(cnt) > 0:
                facts.append('storageContent("{}",c({}),0)'.format(storage, ','.join(cnt)))
            else:
                facts.append('storageContent("{}",c,0)'.format(storage))

        return facts

    def _generate_representative_facts(self, representatives) -> List[str]:
        facts = []
        for class_str, rep_str in representatives.items():
            facts.append('representedBy("{}","{}")'.format(class_str, rep_str))
        return facts

    def _generate_goal(self, goal: Dict[str, List[str]]) -> List[str]:
        facts = []
        for midx, (storage_module, desired_classes) in enumerate(goal.items()):
            for iidx, cls in enumerate(desired_classes):
                facts.append('goal_part(m%d_i%d,"%s",%d,"%s")' % (midx, iidx, storage_module, iidx, cls))
        return facts

    def setup(self, encodings: List[str], horizon, ontologymeta, representatives, goal, initial, extra_facts=[], extra_args=[]):
        assert(isinstance(horizon, int) and horizon > 1)
        self.horizon = horizon
        self.ontology_meta_json = ontologymeta
        number_of_items_in_goal = max(sum([len(s) for s in goal.values()]), 1)
        self.facts = self._generate_initial_facts(initial, number_of_items_in_goal) + self._generate_representative_facts(representatives) + self._generate_goal(goal) + extra_facts
        # logging.warning("limiting to %d items in goal", number_of_items_in_goal)
        self.constraints = [
            ':- {n} < #count {{ Mat,Module,T : action(supply(Mat,Module),T) }}.'.format(n=number_of_items_in_goal),
            ':- #count {{ Mat,Module,T : action(supply(Mat,Module),T) }} < {n}.'.format(n=number_of_items_in_goal)
        ]
        self.temp_hex = self._write_temp_file(self.horizon, self.ontology_meta_json, self.facts, self.constraints)
        self.encodings = encodings
        self.env = os.environ.copy()
        self.env['CLASSPATH'] = self.java_classpath
        self.extra_args = extra_args
        self.yielded_plans = 0
        self.stop_enumeration = False

    def yield_plans(self):
        cmdline = [
            self.hexlite_path,
            '--flpcheck=none',
            '--pluginpath', self.pluginpath_builtin,
            '--plugin', 'javaapiplugin',
                        'at.ac.tuwien.kr.hexlite.OWLAPIPlugin',
            '--plugin', 'stringplugin',
            '--pluginpath', self.pluginpath_custom,
            '--plugin', 'jsonoutputplugin',
            '--plugin', 'listplugin',
            '--number', '1',
            '--stats'] + self.extra_args + [
            '--', self.temp_hex] + self.encodings
        hexlite = subprocess.Popen(
            cmdline, shell=False, env=self.env,
            stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)

        # read stderr in stats collector thread
        ct = StderrCollectorThread(hexlite.stderr)

        # read stdout in main thread
        while hexlite.poll() is None and not self.stop_enumeration:
            line = hexlite.stdout.readline()
            if len(line) != 0:
                # logging.info("got line %s", line[:-1])
                try:
                    asinfo = json.loads(line)
                    # logging.info("got answer set %s", json.dumps(asinfo, indent=2))
                    self.yielded_plans += 1
                    yield Plan(asinfo)
                except json.JSONDecodeError:
                    logging.error("JSONDecodeError on output '%s' (ignoring line)", line.rstrip())

        # this is supposed to be the deadlock-free way of doing this
        if hexlite.poll() is None:
            hexlite.terminate()
            outs = hexlite.stdout.read()
            if len(outs) > 0:
                logging.info("after termination got stdout starting with %s", outs[:79])
            timeout = 10
            while (hexlite.poll() is None and timeout > 0):
                time.sleep(0.1)
                timeout -= 1
            if hexlite.poll() is None:
                logging.warning("need to kill hexlite")
                hexlite.kill()

        ct.join()

        os.remove(self.temp_hex)

        self.messages = ct.messages
        self.jsons = ct.jsons

    def stop(self):
        self.stop_enumeration = True

    def yielded(self):
        return self.yielded_plans > 0

    def display_messages(self):
        logging.info("MESSAGES:\n%s", "\n".join([ x for x in self.messages if not x.startswith('W:rewriter.py') ]))

    def display_stats(self):
        NEGFILTER = set('all rewriting preparation'.split(' '))

        # logging.info("JSONS:\n%s", "\n".join([ str(x) for x in self.jsons ]))
        answersetjsons = [x for x in self.jsons if x['event'] == 'stats' and x['name'] in ['answersetopt', 'final']]

        for idx, s in enumerate(answersetjsons):

            logging.info("answer %d / %s", idx + 1, s['name'])

            for catname, catstat in s['categories'].items():
                if catname not in NEGFILTER:
                    logging.info("%12s: real %.2f cpu %.2f count %d", catname, catstat[0], catstat[1], catstat[2])

            accstr = ' '.join(["%s=%.2f" % (k, v) for k, v in s['accumulated'].items()])
            logging.info("accumulated:  %s", accstr)
