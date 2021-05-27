import os
import logging
import json
import sys
import time
import grpc
import concurrent.futures
import collections
from typing import Dict, List

from . import hexcaller
from . import planning_pb2 as plpb
from . import planning_pb2_grpc as plgrpc


def setup_logging():
    level = logging.INFO
    # fmt="%(levelname)1s:%(filename)10s:%(lineno)3d:%(message)s")
    fmt = "%(levelname)1s: %(message)s"

    logging.basicConfig(level=level, stream=sys.stderr, format=fmt)

    # make log level names shorter so that we can show them
    logging.addLevelName(50, 'C')
    logging.addLevelName(40, 'E')
    logging.addLevelName(30, 'W')
    logging.addLevelName(20, 'I')
    logging.addLevelName(10, 'D')


class GRPCServicer(plgrpc.AI4IndustryPlanner):
    def __init__(self):
        '''
        This planner uses hexlite + the hexlite-owlapi-plugin for reasoning.
        '''
        self.representatives = {
            'http://www.ai4eu.eu/pilot/ai4industry#Can':
                'http://www.ai4eu.eu/pilot/ai4industry#GenericCan',
            'http://www.ai4eu.eu/pilot/ai4industry#BlueCap':
                'http://www.ai4eu.eu/pilot/ai4industry#GenericCapBlue',
            'http://www.ai4eu.eu/pilot/ai4industry#RedCap':
                'http://www.ai4eu.eu/pilot/ai4industry#GenericCapRed',
            'http://www.ai4eu.eu/pilot/ai4industry#WhiteCap':
                'http://www.ai4eu.eu/pilot/ai4industry#GenericCapWhite',
        }
        # list of tuples: (output machine URI, storage index, type)
        # e.g., ("http://www.ai4eu.eu/pilot/ai4industry#storage1", 0, 'red')
        self.current_goal_simplified = []

    def _create_skillmatch_facts(self, smresult: plpb.SkillMatchResult) -> List[str]:
        # ignoring negative matches
        ret = []
        for idx, pm in enumerate(smresult.positiveMatches):
            smstr = 'sm%s' % idx

            for rq in pm.requirement:
                ret.append('skillmatch_workpiece_requirement(%s,"%s")' % (smstr, rq))

            for o in pm.offer:
                ret.append('skillmatch_offer(%s,"%s")' % (smstr, o))

            ret.append('skillmatch_machine(%s,"%s")' % (smstr, pm.module))
        return ret

    def computeOptimalPlan(
        self,
        request: plpb.SkillMatchResultAndPlannerRequest,
        context
    ) -> plpb.PlannerResultAndTimeEstimateRequest:
        logging.info("request: %s", request)

        initial_situation = self._create_initial_situation(request.plannerRequest)
        goal = self._create_goal(request.plannerRequest)
        extra_facts = self._create_skillmatch_facts(request.skillmatchResult)

        if request.plannerRequest.max_time_step > 20:
            raise ValueError("expect max_time_step <= 20, got %d" % request.plannerRequest.max_time_step)

        extra_args = []
        # extra_args.append('--verbose')
        # extra_args.append('--debug')
        # extra_args.append('--dump-grounding')

        r = hexcaller.HEXOWLAPIRunner()
        r.setup(
            horizon=request.plannerRequest.max_time_step,
            ontologymeta=request.plannerRequest.ontology,
            encodings=['/app/encoding.hex'],
            # individuals representing inputs of the system, this is specific to our special encoding
            representatives=self.representatives,
            goal=goal,
            initial=initial_situation,
            extra_facts=extra_facts,
            extra_args=extra_args
        )

        for idx, plan in enumerate(r.yield_plans()):
            logging.info("Plan %d:", idx + 1)
            plan.log()
            # abort after the first answer set
            r.stop()

            ret = self._extract_response_from_plan(plan)
            logging.info("returning result %s", ret)
            return ret

        if not r.yielded():
            logging.warning("No plan!")
            r.display_messages()

        ret = plpb.PlannerResultAndTimeEstimateRequest()
        logging.info("returning empty result %s", ret)
        return ret

    @staticmethod
    def _simplify(s: str):
        pos = s.find('http://www.ai4eu.eu/pilot/ai4industry#')
        if pos == -1:
            return s
        else:
            return s.replace('http://www.ai4eu.eu/pilot/ai4industry#', '#')

    def _format_action(self, a):
        if a['name'] == 'supply':
            piece, to_ = a['args']
            return 'supplying work piece "%d" to machine %s' % (
                piece['args'][1],
                self._simplify(to_))
        elif a['name'] == 'migrate':
            piece, from_, to_ = a['args']
            return 'migrating work piece "%d" from machine %s to machine %s' % (
                piece['args'][1],
                self._simplify(from_),
                self._simplify(to_))
        elif a['name'] == 'applyskill':
            _, machine, piece, cap = a['args']
            return 'applying skill "presscap" at machine %s on workpiece "%d" with cap %s' % (
                self._simplify(machine),
                piece['args'][1],
                self._simplify(cap['args'][0]))
        elif a['name'] == 'store':
            to_, piece = a['args']
            return 'storing work piece "%d" in storage %s' % (
                piece['args'][1],
                self._simplify(to_))
        else:
            return repr(a)

    def _extract_response_from_plan(self, plan: hexcaller.Plan) -> plpb.PlannerResultAndTimeEstimateRequest:
        ret = plpb.PlannerResultAndTimeEstimateRequest()

        actionatoms = [
            a for a in plan.atoms
            if isinstance(a, dict) and a['name'] == 'action']

        actions_by_time = collections.defaultdict(list)
        for a in actionatoms:
            spec, timestep = a['args']
            actions_by_time[timestep].append(spec)

        # string representation of actions
        for timestep in sorted(actions_by_time.keys()):
            for a in actions_by_time[timestep]:
                ret.plannerResult.actions.append(plpb.Action(
                    timestep=timestep,
                    action=self._format_action(a)))

        # time estimate request
        # each time step for supplying is one second

        # self.current_goal_simplified holds list of tuples:
        # (output machine URI, storage index, type)
        # e.g., ("http://www.ai4eu.eu/pilot/ai4industry#storage1", 0, 'red')

        # check final time step for all storages.
        # each item is of form matidx(Can,<idx>) and is in one storage and one index
        # for each item, find out the time step where it is supplied
        # the ProductInput for the TimeEstimateRequest is built as follows:
        # * <idx> is the product name
        # * type from current_goal_simplified is the type
        # * supply timestep is the timeEnteringSystem

        storage_content_atoms = [
            a['args']
            for a in plan.atoms
            if isinstance(a, dict) and a['name'] == 'storageContentAt']
        last_timestep = max([
            timestep
            for _, _, _, timestep in storage_content_atoms], default=1)
        logging.warning("last_timestep = %d", last_timestep)

        last_timestep_storage_contents = [
            (machine, idx, item['args'])
            for machine, idx, item, timestep in storage_content_atoms
            if timestep == last_timestep]
        logging.warning("last_timestep_storage_contents=%s", last_timestep_storage_contents)

        # now get only those storages that are in current_goal_simplified
        stored_item_color: Dict[int, str] = {}
        for storage, idx, color in self.current_goal_simplified:
            content_candidates = [
                item
                for i_storage, i_idx, item in last_timestep_storage_contents
                if i_storage == storage and i_idx == idx]
            if len(content_candidates) != 1:
                # maybe partially reached goal
                logging.warning("content_candidates not singular: %s", content_candidates)
            else:
                # found one candidate
                item = content_candidates[0]
                stored_item_color[item[1]] = color
        logging.warning("stored_item_color = %s", stored_item_color)

        # now check in which timestep the respective item is supplied
        # result is a list of tuples (supply-spec, timestep), e.g.,
        # (
        #   [ # material matidx(#Can,1) is supplied by #supplier1
        #       {'name': 'matidx', 'args': ['"http://www.ai4eu.eu/pilot/ai4industry#Can"', 1]},
        #       '"http://www.ai4eu.eu/pilot/ai4industry#supplier1"'
        #   ],
        #   1 # at timestep 1
        # )
        supply_actions = [
            (aa['args'][0]['args'], aa['args'][1])
            for aa in actionatoms
            if aa['args'][0]['name'] == 'supply']
        # logging.warning("actionatoms = %s", actionatoms)
        logging.warning("supply_actions = %s", supply_actions)
        for spec, timestep in supply_actions:
            # we only need to extract the index from matidx
            idx = spec[0]['args'][1]
            # logging.warning("for product '%d' got timestep %s", idx, repr(timestep))

            if idx in stored_item_color:
                # if not, we have more supply actions than required output, which can happen for example if no output was requested (we use at least 1)
                ret.timeEstimateRequest.products_entering_system.append(
                    plpb.ProductInput(
                        product=str(idx),
                        type=stored_item_color[idx],
                        timeEnteringSystem=float(timestep) + 1.0))

        return ret

    def _create_initial_situation(self, request: plpb.PlannerRequest):
        # this is currently fixed
        initial_situation = {
            "http://www.ai4eu.eu/pilot/ai4industry#supplier1": [
                "http://www.ai4eu.eu/pilot/ai4industry#Can",
                "http://www.ai4eu.eu/pilot/ai4industry#Can",
                "http://www.ai4eu.eu/pilot/ai4industry#Can",
                "http://www.ai4eu.eu/pilot/ai4industry#Can",
                "http://www.ai4eu.eu/pilot/ai4industry#Can",
                "http://www.ai4eu.eu/pilot/ai4industry#Can"
            ],
            "http://www.ai4eu.eu/pilot/ai4industry#presscap1": [
                "http://www.ai4eu.eu/pilot/ai4industry#BlueCap",
                "http://www.ai4eu.eu/pilot/ai4industry#RedCap",
                "http://www.ai4eu.eu/pilot/ai4industry#BlueCap",
            ],
            "http://www.ai4eu.eu/pilot/ai4industry#presscap2": [
                "http://www.ai4eu.eu/pilot/ai4industry#RedCap",
                "http://www.ai4eu.eu/pilot/ai4industry#WhiteCap",
                "http://www.ai4eu.eu/pilot/ai4industry#WhiteCap",
            ],
            "http://www.ai4eu.eu/pilot/ai4industry#storage1": [],
            "http://www.ai4eu.eu/pilot/ai4industry#storage2": [],
        }
        return initial_situation

    def _create_goal(self, request: plpb.PlannerRequest):
        '''
        creates goal datastructure, for example

        goal = {
            "http://www.ai4eu.eu/pilot/ai4industry#storage1": [
                "http://www.ai4eu.eu/pilot/ai4industry#BlueCappedCan",
                "http://www.ai4eu.eu/pilot/ai4industry#RedCappedCan",
            ],
            "http://www.ai4eu.eu/pilot/ai4industry#storage2": [
                "http://www.ai4eu.eu/pilot/ai4industry#WhiteCappedCan",
                "http://www.ai4eu.eu/pilot/ai4industry#RedCappedCan",
            ],
        }
        '''
        if len(request.goal) > 2:
            raise ValueError("there can be at most 2 instances of DesiredMagazineState in goal")
        if any([len(dms.output) > 3 for dms in request.goal]):
            raise ValueError("there can be at most 3 output products in DesiredMagazineState.output")
        if any([item not in ['red', 'white', 'blue'] for dms in request.goal for item in dms.output]):
            raise ValueError("products in DesiredMagazineState.output must be in ['red', 'white', 'blue']")

        goal = {}
        for storageidx, dms in enumerate(request.goal):
            goalstr = "http://www.ai4eu.eu/pilot/ai4industry#storage%d" % (storageidx + 1)
            goal[goalstr] = []
            for item in dms.output:
                itemstr = "http://www.ai4eu.eu/pilot/ai4industry#%sCappedCan" % item.capitalize()
                goal[goalstr].append(itemstr)

        # also store goal for creating time estimation request later on
        self.current_goal_simplified = []
        for storageidx, dms in enumerate(request.goal):
            for itemidx, item in enumerate(dms.output):
                self.current_goal_simplified.append((
                    '"http://www.ai4eu.eu/pilot/ai4industry#storage%d"' % (storageidx + 1),
                    itemidx,
                    item))

        return goal


def create_test_request():
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
                module=ns + 'presscap1'),
            plpb.SkillMatchTriple(
                requirement=r,
                offer=[ns + 'RedCap'],
                module=ns + 'presscap2'),
            plpb.SkillMatchTriple(
                requirement=r,
                offer=[ns + 'WhiteCap'],
                module=ns + 'presscap2'),
        ],
        negativeMatches=[]
    )

    rq = plpb.SkillMatchResultAndPlannerRequest(
        skillmatchResult=smresult,
        plannerRequest=plpb.PlannerRequest(
            ontology='/app/ontology.json',
            goal=[
                plpb.DesiredMagazineState(output=['blue', 'red']),
                plpb.DesiredMagazineState(output=['white']),
            ],
            max_time_step=9
        )
    )
    return rq


def main_test():
    setup_logging()
    result = GRPCServicer().computeOptimalPlan(create_test_request(), None)
    logging.warning("result = %s", result)


def main():
    setup_logging()

    configfile = os.environ['CONFIG'] if 'CONFIG' in os.environ else "config.json"
    logging.info("loading config from %s", configfile)
    config = json.load(open(configfile, 'rt'))
    grpcserver = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    plgrpc.add_AI4IndustryPlannerServicer_to_server(GRPCServicer(), grpcserver)
    grpcport = config['grpcport']
    # listen on all interfaces (otherwise docker cannot export)
    grpcserver.add_insecure_port('0.0.0.0:' + str(grpcport))
    logging.info("starting grpc server at port %d", grpcport)
    grpcserver.start()

    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
