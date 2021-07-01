from typing import Optional, List, Dict
import os
import logging
import json
import time
import fastapi
import fastapi.templating
import pydantic
import queue
import grpc
import concurrent.futures
import sys
import traceback


import gui_pb2
import gui_pb2_grpc


ONTOLOGY = '/app/ontology.json'


logger = logging.getLogger(__name__)
# the next line sets logging level for things outside uvicorn, that means for the gRPC server
# set Python logging level for uvicorn when starting uvicorn!
logging.basicConfig(level=logging.INFO)


class MagazineItem(pydantic.BaseModel):
    magazine: int
    item: int
    color: str


class GoalInformation(pydantic.BaseModel):
    magazines: List[MagazineItem]
    maxstep: int


class GUIUpdate(pydantic.BaseModel):
    output: str


class GUIServicerImpl(gui_pb2_grpc.AI4IndustryGUIServicer):
    def __init__(self, to_protobuf_queue, to_js_queue):
        self.to_protobuf_queue = to_protobuf_queue
        self.to_js_queue = to_js_queue

    def requestPipelineRun(self, request, context):
        logging.info("requestPipelineRun called")

        ret = gui_pb2.SkillMatchAndPlannerRequest()
        ret.skillmatchRequest.ontology = ONTOLOGY
        ret.plannerRequest.ontology = ONTOLOGY

        try:
            logging.info("requestPipelineRun waiting")
            while True:
                try:
                    ret = self.to_protobuf_queue.get(block=True, timeout=1.0)
                    break
                except queue.Empty:
                    if not context.is_active():
                        raise RuntimeError("RPC interrupted - leaving requestPipelineRun")
                    # otherwise retry
            logging.info("received item %s", ret)
        except Exception:
            logging.warning("got exception %s", traceback.format_exc())
            time.sleep(1)
            pass

        return ret

    def displayPipelineResult(self, request: gui_pb2.PlannerResultAndTimeEstimateResult, context):
        logging.info("received pipeline result %s", request)

        # format result
        ol = []  # output lines

        # first display planning steps
        ol.append("Planner Result:")
        planresult = request.plannerResult
        last_step = None
        for a in sorted(planresult.actions, key=lambda x: x.timestep):
            stepstring = ' ' * 9
            if last_step is None or last_step != a.timestep:
                if last_step != a.timestep:
                    ol.append('')
                stepstring = 'Step %2d: ' % a.timestep
            ol.append(stepstring + a.action)
            last_step = a.timestep
        ol.append('')

        # then display product times
        ol.append('Time Estimation Result:')
        teresult = request.timeEstimateResult
        for pet in sorted(teresult.time, key=lambda x: x.product):
            ol.append("For product '%s' estimated time in system is %.1f seconds" % (pet.product, pet.estimatedTimeInSystem))

        output = '\n'.join(ol)

        # send to javascript for display (as a preformatted string in <pre>)
        gu = GUIUpdate(output=output)
        self.to_js_queue.put(gu)

        # dummy return
        return gui_pb2.Empty()


app = fastapi.FastAPI(title='AI4IndustryGUIServer', debug=True)
app.logger = logger

configfile = os.environ['CONFIG'] if 'CONFIG' in os.environ else "config.json"
logging.info("loading config from %s", configfile)
config = json.load(open(configfile, 'rt'))
protobuf_to_js_queue = queue.Queue()
js_to_protobuf_queue = queue.Queue()
templates = fastapi.templating.Jinja2Templates(directory='templates')

grpcserver = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
gui_pb2_grpc.add_AI4IndustryGUIServicer_to_server(GUIServicerImpl(js_to_protobuf_queue, protobuf_to_js_queue), grpcserver)
grpcport = config['grpcport']
# listen on all interfaces (otherwise docker cannot export)
grpcserver.add_insecure_port('0.0.0.0:' + str(grpcport))
logging.info("starting grpc server at port %d", grpcport)
grpcserver.start()


@app.get('/')
def serve_website(request: fastapi.Request):
    return templates.TemplateResponse("gui.html", {'request': request}, headers={'Cache-Control': 'no-cache'})


@app.get('/gui.js')
def serve_js(request: fastapi.Request):
    return fastapi.responses.FileResponse("gui.js", headers={'Cache-Control': 'no-cache'})


@app.get('/gui.css')
def serve_css(request: fastapi.Request):
    return fastapi.responses.FileResponse("gui.css", headers={'Cache-Control': 'no-cache'})


@app.get('/visualisation-webinterface.png')
def serve_image(request: fastapi.Request):
    return fastapi.responses.FileResponse("visualisation-webinterface.png", headers={'Cache-Control': 'no-cache', 'Content-type': 'image/png'})


@app.post('/goal', response_model=None)
def goal(goalinfo: GoalInformation) -> None:
    '''
    If the user submits the form.
    '''
    logging.info("goal(%s)", goalinfo)

    # return design evaluation job from requestSudokuEvaluation()
    ret = gui_pb2.SkillMatchAndPlannerRequest()

    ret.skillmatchRequest.ontology = ONTOLOGY
    ret.skillmatchRequest.positive = True
    ret.skillmatchRequest.negative = False
    ret.plannerRequest.ontology = ONTOLOGY

    # convert transfer format to something more useful (key = (mag,item) value = color)
    magazineinfo = {
        (mi.magazine, mi.item): mi.color
        for mi in goalinfo.magazines
    }

    # configure three magazines
    for mag in [0, 1]:
        dms = gui_pb2.DesiredMagazineState()
        for itm in [0, 1, 2]:
            color = magazineinfo.get((mag, itm), None)
            if color is None:
                # do not process further items (this is ensured by the GUI but let's double check)
                break
            else:
                dms.output.append(color)
        ret.plannerRequest.goal.append(dms)

    ret.plannerRequest.max_time_step = goalinfo.maxstep

    logging.info("GUI sending user activity ...")
    js_to_protobuf_queue.put(ret)
    logging.info("... sent")

    return None


@app.get('/wait_update', response_model=Optional[GUIUpdate])
def wait_update(timeout_ms: int):
    '''
    The GUI periodically calls this method to wait for a new
    update to the GUI. Ideally the GUI calls this each <timeout_ms>
    milliseconds.
    '''
    logging.info("wait_update(%d)", timeout_ms)

    ret = None

    try:
        ret = protobuf_to_js_queue.get(block=True, timeout=timeout_ms / 1000.0)
        logging.info("GUI got update from protobuf!")
    except queue.Empty:
        pass

    if ret is not None:
        logging.info("wait_update returns %s", ret)
    return ret
