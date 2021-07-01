#!/usr/bin/env python3

import logging
import grpc
import json

import timeprediction_pb2 as tppb
import timeprediction_pb2_grpc as tpgrpc

configfile = "config.json"
config = json.load(open(configfile, 'rt'))

logging.basicConfig(level=logging.DEBUG)


def main():
    # !!! here it is hardcoded to use the external port that ./helper.py assigns to the docker container !!!
    # !!! if you run without docker, you need to use port 8061 !!!
    channel = grpc.insecure_channel('localhost:8004')
    stub = tpgrpc.TimeEstimatorStub(channel)

    rq = tppb.PlannerResultAndTimeEstimateRequest(
        plannerResult=tppb.PlannerResult(
            actions=[
                tppb.Action(timestep=1, action='another dummy action'),
                tppb.Action(timestep=3, action='some dummy action'),
            ]
        ),
        timeEstimateRequest=tppb.TimeEstimateRequest(
            products_entering_system=[
                tppb.ProductInput(product='1', type='red', timeEnteringSystem=1.0),
                tppb.ProductInput(product='2', type='blue', timeEnteringSystem=6.0),
            ]
        )
    )

    response = stub.compute(rq)

    logging.info("got response '%s'", response)


main()
