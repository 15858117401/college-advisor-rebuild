package com.college_advisor.service.graph.nodes.executionNodes.PlanNode.ExecutionSubGraphNode;

import com.college_advisor.service.graph.nodes.executionNodes.ExecutionSubgraph;
import com.college_advisor.service.graph.state.ErrorState.ErrorContext;
import com.college_advisor.service.graph.state.ErrorState.ErrorInfo;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.graph.state.SubgraphState;
import com.college_advisor.service.tools.CourseDataTools;
import com.college_advisor.service.tools.CourseSectionTools;
import com.college_advisor.service.tools.GraduationTools;
import com.college_advisor.service.tools.ProfessorRatingTools;
import com.college_advisor.service.tools.SkillTools;
import dev.langchain4j.model.chat.ChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.bsc.langgraph4j.action.NodeAction;

import java.util.Map;

public class ExecutionSubgraphNode implements NodeAction<MainState> {

    private final CompiledGraph<SubgraphState> subgraph;

    /** Stub constructor — sub-agents are no-ops (used for skeleton/plan-only tests). */
    public ExecutionSubgraphNode() throws Exception {
        this.subgraph = ExecutionSubgraph.build();
    }

    /** Production constructor — RecommenderNode backed by langchain4j AiServices. */
    public ExecutionSubgraphNode(ChatModel model,
                                 CourseDataTools courseData,
                                 CourseSectionTools sections,
                                 GraduationTools graduation,
                                 ProfessorRatingTools profRating,
                                 SkillTools skill) throws Exception {
        this.subgraph = ExecutionSubgraph.build(model, courseData, sections, graduation, profRating, skill);
    }

    @Override
    public Map<String, Object> apply(MainState state) throws Exception {
        System.out.println("[execution_subgraph] executing");
        SubgraphState result = subgraph.invoke(
                Map.of("plan",            state.taskContext().plan(),
                       "userInput",       state.userInput(),
                       "userPreferences", state.userPreferences())
        ).get();

        if (result.currentError() != null) {
            ErrorInfo inner = result.currentError();
            System.out.println("[execution_subgraph] subgraph failed: " + inner.message);
            ErrorInfo err = new ErrorInfo("execution_subgraph", inner.type, inner.message, false);
            return Map.of(
                    "errorContext", new ErrorContext(err, state.errorContext().nodeRetries(), "fatal_error"),
                    "nodeHistory",  "execution_subgraph"
            );
        }

        String response = result.<String>value("response").orElse("");
        return Map.of(
                "response",    response,
                "taskContext", state.taskContext().withResult(response),
                "nodeHistory", "execution_subgraph"
        );
    }

    public String route(MainState state) throws Exception {
        if (state.currentError() != null) return "fatal_error";
        return "output";
    }
}
