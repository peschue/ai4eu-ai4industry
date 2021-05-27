#!/usr/bin/env python -u

# this is the main entry point for manual experimental runs

import argparse
import sys
import json
import os
import os.path
import logging

BASEDIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')
sys.path = [os.path.join(BASEDIR, 'src')] + sys.path
import ai4industry.hexcaller as hexcaller


HEXLITE_BASE = '/home/ps/_science/hex/hexlite-owlapi-plugin/hexlite'
OWLAPIPLUGIN_BASE = '/home/ps/_science/hex/hexlite-owlapi-plugin'


def setup_logging():
    level = logging.INFO
    #fmt="%(levelname)1s:%(filename)10s:%(lineno)3d:%(message)s")
    fmt="%(levelname)1s: %(message)s"

    logging.basicConfig(level=level, stream=sys.stderr, format=fmt)

    # make log level names shorter so that we can show them
    logging.addLevelName(50, 'C')
    logging.addLevelName(40, 'E')
    logging.addLevelName(30, 'W')
    logging.addLevelName(20, 'I')
    logging.addLevelName(10, 'D')

def main():
    parser = argparse.ArgumentParser(description='AI4Industry experiment runner')
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output.")
    parser.add_argument('-g', '--grounding', action='store_true', help="Dump grounding.")
    args = parser.parse_args()

    setup_logging()

    initial_situation = {
        "http://www.ai4eu.eu/pilot/ai4industry#supplier1": [
                "http://www.ai4eu.eu/pilot/ai4industry#Can",
                "http://www.ai4eu.eu/pilot/ai4industry#Can",
                "http://www.ai4eu.eu/pilot/ai4industry#Can",
            ],
        "http://www.ai4eu.eu/pilot/ai4industry#storage1": [],
        "http://www.ai4eu.eu/pilot/ai4industry#presscap1": [
                "http://www.ai4eu.eu/pilot/ai4industry#WhiteCap",
                "http://www.ai4eu.eu/pilot/ai4industry#WhiteCap",
            ],
        "http://www.ai4eu.eu/pilot/ai4industry#presscap2": [
                "http://www.ai4eu.eu/pilot/ai4industry#RedCap",
                "http://www.ai4eu.eu/pilot/ai4industry#RedCap",
            ],
        }
    goal = {
        "http://www.ai4eu.eu/pilot/ai4industry#storage1": [
                "http://www.ai4eu.eu/pilot/ai4industry#BlueCappedCan",
                "http://www.ai4eu.eu/pilot/ai4industry#WhiteCappedCan",
            ],
        }

    horizfrom, horizto = 8, 8
    #horizfrom, horizto = 13, 13
    # horizfrom, horizto = 13, 18
    HORIZONS = range(horizfrom, horizto+1)

    tempfile_ontology_json = os.path.join(BASEDIR, 'tmp-ontology.json')
    with open(tempfile_ontology_json, 'w+t') as f:
        json.dump(
            {
                "load-uri": os.path.join(BASEDIR, 'ontology', 'ontology.owl'),
                "namespaces": {
                    "owl": "http://www.w3.org/2002/07/owl#",
                    "ai4industry": "http://www.ai4eu.eu/pilot/ai4industry#"
                }
            }, f)

    SETUP = {
        'encoding': [os.path.join(BASEDIR, 'encodings', 'optimized2.hex')],
        'ontologymeta': tempfile_ontology_json,
    }

    extra_args = []
    if args.verbose:
        extra_args.append('--verbose')
    if args.grounding:
        extra_args.append('--dump-grounding')

    for horizon in HORIZONS:
        logging.info("=== HORIZON %d === SETUP %s ===", horizon, SETUP)

        r = hexcaller.HEXOWLAPIRunner(BASEDIR, HEXLITE_BASE, OWLAPIPLUGIN_BASE)

        r.setup(horizon=horizon,
                ontologymeta=SETUP['ontologymeta'],
                encodings=SETUP['encoding'],
                # individuals representing inputs of the system, this is specific to our special encoding
                representatives={
                    'http://www.ai4eu.eu/pilot/ai4industry#Can':
                        'http://www.ai4eu.eu/pilot/ai4industry#GenericCan',
                    #'http://www.evosoft.com/knowledge_graph/evosoftplant_product#Cap':
                    #    'http://www.kr.tuwien.ac.at/research/projects/ai4eu/evosoft_extension#GenericCap',
                    'http://www.ai4eu.eu/pilot/ai4industry#BlueCap':
                        'http://www.ai4eu.eu/pilot/ai4industry#GenericCapBlue',
                    'http://www.ai4eu.eu/pilot/ai4industry#RedCap':
                        'http://www.ai4eu.eu/pilot/ai4industry#GenericCapRed',
                    'http://www.ai4eu.eu/pilot/ai4industry#WhiteCap':
                        'http://www.ai4eu.eu/pilot/ai4industry#GenericCapWhite',
                },
                goal=goal, initial=initial_situation,
                extra_args=extra_args)

        for idx, plan in enumerate(r.yield_plans()):
            logging.info("Plan %d for horizon %d:", idx+1, horizon)
            plan.log()
            # abort after the first answer set
            r.stop()

        if not r.yielded():
            logging.warning("No plan!")
            r.display_messages()

main()
