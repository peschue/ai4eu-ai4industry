#!/usr/bin/env python3

import logging
import grpc
import json


import planning_pb2 as plpb
import planning_pb2_grpc as plgrpc


configfile = "config.json"
config = json.load(open(configfile, 'rt'))

logging.basicConfig(level=logging.DEBUG)


def main():
    # !!! here it is hardcoded to use the external port that ./helper.py assigns to the docker container !!!
    # !!! if you run without docker, you need to use port 8061 !!!
    channel = grpc.insecure_channel('localhost:8003')
    stub = plgrpc.AI4IndustryPlannerStub(channel)

    ns = 'http://www.ai4eu.eu/pilot/ai4industry#'
    r = [ns + 'RoundWorkpiece']
    smresult = plpb.SkillMatchResult(
        positiveMatches=[
            plpb.SkillMatchTriple(
                requirement=r,
                offer=[ns + 'BlueCap'],
                module=ns + 'presscap1'),
            plpb.SkillMatchTriple(
                requirement=r,
                offer=[ns + 'RedCap'],
                module=ns + 'presscap2'),
        ],
        negativeMatches=[]
    )

    rq = plpb.SkillMatchResultAndPlannerRequest(
        skillmatchResult=smresult,
        plannerRequest=plpb.PlannerRequest(
            ontology='/app/ontology.json',
            goal=[
                plpb.DesiredMagazineState(output=['blue']),
                plpb.DesiredMagazineState(output=['red']),
            ],
            max_time_step=13
        )
    )

    response = stub.computeOptimalPlan(rq)

    logging.info("got response '%s'", response)


main()
