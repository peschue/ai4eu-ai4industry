see [experiment-topology.drawio.pdf](experiment-topology.drawio.pdf)

# March Release of AI4EU Platform: Passthrough RPC Pipeline (Page 1)

We need to create a linear "Pipeline" with passthrough components.

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