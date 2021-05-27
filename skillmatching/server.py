import os
import logging
import json
import time
import grpc
import concurrent.futures


import skillmatching_pb2 as smpb
import skillmatching_pb2_grpc as smgrpc


logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)


class GRPCServicer(smgrpc.SkillMatcher):
    def __init__(self):
        '''
        This skillmatcher is a dummy implementation to replace the proprietary
        component from Siemens AG in the publicly available pipeline.

        It can be replaced in a private pipeline by the real proprietary component.

        This dummy implementation does not perform reasoning. It provides
        the expected output given some selected expected input that is used
        for demonstrating the pipeline.

        See also open-replacement.txt
        '''
        ns = 'http://www.ai4eu.eu/pilot/ai4industry#'
        r = [ns + 'RoundWorkpiece']
        # pre-defined responses to certain requests
        self.PREDEFINED_RESPONSES = {
            ('/app/ontology.json', True, False): smpb.SkillMatchResult(
                positiveMatches=[
                    smpb.SkillMatchTriple(
                        requirement=r,
                        offer=[ns + 'BlueCap'],
                        module=ns + 'presscap1'),
                    smpb.SkillMatchTriple(
                        requirement=r,
                        offer=[ns + 'RedCap'],
                        module=ns + 'presscap1'),
                    smpb.SkillMatchTriple(
                        requirement=r,
                        offer=[ns + 'RedCap'],
                        module=ns + 'presscap2'),
                    smpb.SkillMatchTriple(
                        requirement=r,
                        offer=[ns + 'WhiteCap'],
                        module=ns + 'presscap2'),
                ],
                negativeMatches=[]
            )
        }

        # this response is given for unknown requests
        self.DEFAULT_RESPONSE = smpb.SkillMatchResult()

    def compute(self, request: smpb.SkillMatchAndPlannerRequest, context):
        rq = request.skillmatchRequest
        logging.info("skillmatch request: %s", rq)

        key = (rq.ontology, rq.positive, rq.negative)
        result = self.PREDEFINED_RESPONSES.get(key, self.DEFAULT_RESPONSE)

        logging.info("returning result %s", result)
        ret = smpb.SkillMatchResultAndPlannerRequest(
            skillmatchResult=result,
            plannerRequest=request.plannerRequest
        )
        return ret


configfile = os.environ['CONFIG'] if 'CONFIG' in os.environ else "config.json"
logging.info("loading config from %s", configfile)
config = json.load(open(configfile, 'rt'))
grpcserver = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
smgrpc.add_SkillMatcherServicer_to_server(GRPCServicer(), grpcserver)
grpcport = config['grpcport']
# listen on all interfaces (otherwise docker cannot export)
grpcserver.add_insecure_port('0.0.0.0:' + str(grpcport))
logging.info("starting grpc server at port %d", grpcport)
grpcserver.start()

while True:
    time.sleep(1)
