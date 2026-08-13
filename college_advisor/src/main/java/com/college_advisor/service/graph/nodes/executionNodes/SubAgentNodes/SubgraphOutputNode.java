package com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes;

import com.college_advisor.service.graph.state.PlanTask;
import com.college_advisor.service.graph.state.SubgraphState;
import com.college_advisor.service.graph.state.TaskResult;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class SubgraphOutputNode implements NodeAction<SubgraphState> {

    @Override
    public Map<String, Object> apply(SubgraphState state) throws Exception {
        System.out.println("[subgraph_output] aggregating results");

        if (state.currentError() != null) {
            System.out.println("[subgraph_output] error detected, propagating: "
                    + state.currentError().message);
            return Map.of("nodeHistory", "subgraph_output");
        }

        Map<String, String> resultById = state.taskResults().stream()
                .flatMap(List::stream)
                .collect(Collectors.toMap(
                        TaskResult::taskId,
                        r -> r.result() != null ? r.result() : "(no result)"));

        StringBuilder sb = new StringBuilder();
        List<List<PlanTask>> chains = state.plan().chains();

        for (int i = 0; i < chains.size(); i++) {
            List<PlanTask> chain = chains.get(i);
            if (chains.size() > 1) {
                sb.append("=== Part ").append(i + 1).append(" ===\n\n");
            }
            for (PlanTask task : chain) {
                sb.append("## ").append(formatTaskType(task.taskType())).append("\n");
                sb.append(resultById.getOrDefault(task.id(), "(no result)"));
                sb.append("\n\n");
            }
        }

        return Map.of("response", sb.toString().strip(), "nodeHistory", "subgraph_output");
    }

    private String formatTaskType(String taskType) {
        return switch (taskType) {
            case "recommender"   -> "Course Recommendations";
            case "scheduler"     -> "Schedule";
            case "course_planner"-> "Degree Plan";
            default              -> taskType;
        };
    }
}
