#!/usr/bin/env python3

import logging
import grpc

import gui_pb2
import gui_pb2_grpc


logging.basicConfig(level=logging.INFO)


def test_request_pipeline_run(stub):
    logging.info('request pipeline run waiting for manual submit of form in GUI ...')
    result = stub.requestPipelineRun(gui_pb2.Empty())
    logging.info('... got result %s', result)


def test_display_pipeline_result(stub):
    # now test display result
    pteresult = gui_pb2.PlannerResultAndTimeEstimateResult()

    # example: unique solution
    for a in [
        gui_pb2.Action(timestep=1, action="move can to belt 1"),
        gui_pb2.Action(timestep=2, action="move can to belt 2"),
        gui_pb2.Action(timestep=2, action="move can to belt 1"),
        gui_pb2.Action(timestep=4, action="press red cap on can at station presscap1"),
    ]:
        pteresult.plannerResult.actions.append(a)

    for p in [
        gui_pb2.ProductEstimatedTime(product="red1", estimatedTimeInSystem=3.7),
        gui_pb2.ProductEstimatedTime(product="red2", estimatedTimeInSystem=12.5),
        gui_pb2.ProductEstimatedTime(product="blue3", estimatedTimeInSystem=8.7),
    ]:
        pteresult.timeEstimateResult.time.append(p)
    logging.info('sending pipeline result for display ...')
    response = stub.displayPipelineResult(pteresult)
    logging.info("... got response '%s'", response)


def main():
    # !!! here it is hardcoded to use the external port that ./helper.py assigns to the docker container !!!
    # !!! if you run without docker, you need to use port 8061 !!!
    channel = grpc.insecure_channel('localhost:8001')
    stub = gui_pb2_grpc.AI4IndustryGUIStub(channel)

    test_request_pipeline_run(stub)
    test_display_pipeline_result(stub)


main()
