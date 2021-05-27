#!/usr/bin/env python3

import logging
import json
import time
import grpc
import traceback

# generated from .proto
import orchestrator_pb2 as pb
import orchestrator_pb2_grpc as pb_grpc


logging.basicConfig(level=logging.DEBUG)


configfile = "config.json"
config = json.load(open(configfile, 'rt'))


def main():
    guiconn = 'localhost:' + str(config['gui-grpcport'])
    smconn = 'localhost:' + str(config['skillmatching-grpcport'])
    plconn = 'localhost:' + str(config['planning-grpcport'])
    teconn = 'localhost:' + str(config['timeprediction-grpcport'])

    logging.info("connecting to GUI at %s", guiconn)
    gui_channel = grpc.insecure_channel(guiconn)
    gui_stub = pb_grpc.AI4IndustryGUIStub(gui_channel)

    logging.info("connecting to skillmatcher at %s", smconn)
    sm_channel = grpc.insecure_channel(smconn)
    sm_stub = pb_grpc.SkillMatcherStub(sm_channel)

    logging.info("connecting to planner at %s", plconn)
    pl_channel = grpc.insecure_channel(plconn)
    pl_stub = pb_grpc.AI4IndustryPlannerStub(pl_channel)

    logging.info("connecting to timeestimator at %s", teconn)
    te_channel = grpc.insecure_channel(teconn)
    te_stub = pb_grpc.TimeEstimatorStub(te_channel)

    while True:
        try:
            logging.info("calling gui.requestPipelineRun")
            empty1 = pb.Empty()
            job1 = gui_stub.requestPipelineRun(empty1)

            logging.info("calling skillmatcher")
            job2 = sm_stub.compute(job1)

            logging.info("calling planner")
            job3 = pl_stub.computeOptimalPlan(job2)

            logging.info("calling timeestimator")
            result = te_stub.compute(job3)

            logging.info("calling gui.displayPipelineResult")
            _ = gui_stub.displayPipelineResult(result)

        except Exception:
            logging.error("exception (retrying after 2 seconds): %s", traceback.format_exc())
            # do not spam
            time.sleep(2)


main()
