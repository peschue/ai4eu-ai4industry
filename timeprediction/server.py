import os
import logging
import json
import time
import grpc
import concurrent.futures


import timeprediction_pb2 as tppb
import timeprediction_pb2_grpc as tpgrpc


logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)


class GRPCServicer(tpgrpc.TimeEstimatorServicer):
    def __init__(self):
        pass

    def compute(self, request: tppb.PlannerResultAndTimeEstimateRequest, context):
        rq = request.timeEstimateRequest
        logging.info("time estimation request: %s", rq)

        result = tppb.TimeEstimateResult(
            time=[
                tppb.ProductEstimatedTime(
                    product='dummy reply product',
                    estimatedTimeInSystem=12.34)
            ]
        )

        logging.info("returning result %s", result)
        ret = tppb.PlannerResultAndTimeEstimateResult(
            plannerResult=request.plannerResult,
            timeEstimateResult=result
        )
        return ret


configfile = os.environ['CONFIG'] if 'CONFIG' in os.environ else "config.json"
logging.info("loading config from %s", configfile)
config = json.load(open(configfile, 'rt'))
grpcserver = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
tpgrpc.add_TimeEstimatorServicer_to_server(GRPCServicer(), grpcserver)
grpcport = config['grpcport']
# listen on all interfaces (otherwise docker cannot export)
grpcserver.add_insecure_port('0.0.0.0:' + str(grpcport))
logging.info("starting grpc server at port %d", grpcport)
grpcserver.start()

while True:
    time.sleep(1)
