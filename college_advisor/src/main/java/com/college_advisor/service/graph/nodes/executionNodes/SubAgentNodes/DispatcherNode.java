package com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes;

import com.college_advisor.service.graph.state.PlanTask;
import com.college_advisor.service.graph.state.SubgraphState;
import com.college_advisor.service.graph.state.TaskResult;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

public class DispatcherNode implements NodeAction<SubgraphState> {

    @Override
    public Map<String, Object> apply(SubgraphState state) throws Exception {
        Optional<PlanTask> next = findNextTask(state);
        String taskId = next.map(PlanTask::id).orElse("");
        System.out.println("[dispatcher] next task: " + (taskId.isEmpty() ? "none (all done)" : taskId));
        return Map.of("currentTaskId", taskId, "nodeHistory", "dispatcher");
    }

    public String route(SubgraphState state) {
        if (state.currentError() != null) return "subgraph_error_handler";
        String taskId = state.currentTaskId();
        if (taskId.isEmpty()) return "subgraph_output";
        return state.plan().chains().stream()
                .flatMap(java.util.List::stream)
                .filter(t -> t.id().equals(taskId))
                .map(PlanTask::taskType)
                .findFirst()
                .orElse("subgraph_output");
    }

    private Optional<PlanTask> findNextTask(SubgraphState state) {
        Set<String> completedIds = state.taskResults().stream()
                .flatMap(java.util.List::stream)
                .map(TaskResult::taskId)
                .collect(Collectors.toSet());

        return state.plan().chains().stream()
                .flatMap(java.util.List::stream)
                .filter(t -> !completedIds.contains(t.id()))
                .findFirst();
    }
}
