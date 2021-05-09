#!/usr/bin/env python3

import logging
import grpc
import json

import skillmatching_pb2 as smpb
import skillmatching_pb2_grpc as smgrpc

configfile = "config.json"
config = json.load(open(configfile, 'rt'))

logging.basicConfig(level=logging.DEBUG)


def main():
    # !!! here it is hardcoded to use the external port that ./helper.py assigns to the docker container !!!
    # !!! if you run without docker, you need to use port 8061 !!!
    channel = grpc.insecure_channel('localhost:8002')
    stub = smgrpc.SkillMatcherStub(channel)

    rq = smpb.SkillMatchAndPlannerRequest(
        skillmatchRequest=smpb.SkillMatchRequest(
            ontology='ontology.owl',
            positive=True,
            negative=False,
        ),
        plannerRequest=smpb.PlannerRequest(
            ontology='ontology.owl',
            max_time_step=5
        )
    )

    response = stub.compute(rq)

    logging.info("got response '%s' (expect 4 positive matches and planner request with max_time_step=5)", response)


main()
