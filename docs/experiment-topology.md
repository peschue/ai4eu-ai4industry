see [ai4industry-interaces-pipelines.pdf](ai4industry-interaces-pipelines.pdf)

# (Currently) impossible: RPC-based communication with Splitter and Collator (page 1)

Via Splitter:
* GUI -SkillMatchRequest-> Skillmatcher
* GUI -PlannerRequest ...

Via Collator:
* ... PlannerRequest-> Planner
* Skillmatcher -SkillMatchResult-> Planner

Via Splitter:
* Planner -TimeEstimateRequest-> Timeprediction
* Planner -PlannerResult ...

Via Collator:
* ... PlannerResult -> GUI
* Timeprediction -TimeEstimateResult-> GUI

```
service SkillMatcher {
    rpc compute(SkillMatchRequest) returns (SkillMatchResult);
}

service AI4IndustryGUI {
    rpc requestPipelineRun(Empty) returns (SkillMatchAndPlannerRequest);
    rpc displayPipelineResult(PlannerResultAndTimeEstimateResult) returns (Empty);
}
```

This does not work, because a Splitter output cannot be connected to a Collator input.

# March Release of AI4EU Platform: Passthrough RPC Pipeline (Page 2)

* GUI -> Skillmatcher (SkillMatchAndPlannerRequest)
* Skillmatcher -> Planner (SkillMatchResultAndPlannerRequest)
* Planner -> Timeprediction (PlannerResultAndTimeEstimateRequest)
* Timeprediction -> Gui (PlannerResultAndTimeEstimateResult)

```
service SkillMatcher {
    rpc compute(SkillMatchAndPlannerRequest) returns (SkillMatchResultAndPlannerRequest);
}

service AI4IndustryGUI {
    rpc requestPipelineRun(Empty) returns (SkillMatchAndPlannerRequest);
    rpc displayPipelineResult(PlannerResultAndTimeEstimateResult) returns (Empty);
}
```

# Hopefully June Release: Event-based communication (Page 2)

We have parallel streams.
Skillmatcher and Timeprediction are RPC calls.
GUI and Planning are 2-stream-in, 2-stream-out components

The advantage is:
* planning results can be displayed earlier than time estimation results
* Skillmatcher and TimeEstimation can be generic components

GUI streams requests into Splitter:
* GUI -SkillMatchRequest-> Skillmatcher
* GUI -PlannerRequest ...

Via Collator:
* ... PlannerRequest-> Planner
* Skillmatcher -SkillMatchResult-> Planner

Via Splitter:
* Planner -TimeEstimateRequest-> Timeprediction
* Planner -PlannerResult-> stream into GUI

* Timeprediction -TimeEstimateResult-> stream into GUI

```
service SkillMatcher {
    rpc compute(SkillMatchRequest) returns (SkillMatchResult);
}

service AI4IndustryGUI {
    rpc requestSkillMatchRequest(Empty) returns (stream SkillMatchRequest);
    rpc requestPlannerRequest(Empty) returns (stream PlannerRequest);
    rpc displayPlannerResult(stream PlannerResult) returns (Empty);
    rpc displayTimeEstimateResult(stream TimeEstimateResult) returns (Empty);
}
```

# Most elegant solution: Event-based communication + implicit collation/splitting (Page 4)

We have parallel streams only for things that do not happen at the same time
(in this case only for GUI updates).

* GUI streams out SkillMatchAndPlannerRequest
* Platform implicitly sends only SkillMatchRequest to Skillmatching
* Platform implicitly collects pairs (SkillMatchResult, PlannerRequest) and calls Planning with each pair
* Planning produces PlannerResultAndTimeEstimateRequest as output
* Platform implicitly sends PlannerResult to input stream of GUI for display
* Platform implicitly sends TimeEstimateRequest to TimeEstimation
* TimeEstimation produces TimeEstimateResult
* Platform streams TimeEstimateResult into GUI
