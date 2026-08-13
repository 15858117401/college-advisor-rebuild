package com.college_advisor.service.graph.nodes.executionNodes;

import com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.CoursePlannerNode;
import com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.DispatcherNode;
import com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.RecommenderNode;
import com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.SchedulerNode;
import com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.SubgraphOutputNode;
import com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.error.SubgraphErrorHandlerNode;
import com.college_advisor.service.graph.nodes.executionNodes.SubAgentNodes.error.SubgraphFatalErrorNode;
import com.college_advisor.service.graph.state.SubgraphState;
import com.college_advisor.service.tools.CourseDataTools;
import com.college_advisor.service.tools.CourseSectionTools;
import com.college_advisor.service.tools.GraduationTools;
import com.college_advisor.service.tools.ProfessorRatingTools;
import com.college_advisor.service.tools.SkillTools;
import dev.langchain4j.model.chat.ChatModel;
import org.bsc.langgraph4j.CompiledGraph;
import org.bsc.langgraph4j.StateGraph;

import java.util.Map;

import static org.bsc.langgraph4j.StateGraph.END;
import static org.bsc.langgraph4j.StateGraph.START;
import static org.bsc.langgraph4j.action.AsyncEdgeAction.edge_async;
import static org.bsc.langgraph4j.action.AsyncNodeAction.node_async;

public class ExecutionSubgraph {

    /** Stub build — all sub-agents use no-arg constructors (no DB, no LLM calls). */
    public static CompiledGraph<SubgraphState> build() throws Exception {
        return build(new DispatcherNode(), new RecommenderNode(),
                new SchedulerNode(), new CoursePlannerNode(), new SubgraphOutputNode(),
                new SubgraphErrorHandlerNode(), new SubgraphFatalErrorNode());
    }

    /** Production build — all sub-agents backed by real tools. */
    public static CompiledGraph<SubgraphState> build(
            ChatModel model,
            CourseDataTools courseData,
            CourseSectionTools sections,
            GraduationTools graduation,
            ProfessorRatingTools profRating,
            SkillTools skill) throws Exception {
        return build(new DispatcherNode(),
                new RecommenderNode(model, courseData, sections, graduation, profRating, skill),
                new SchedulerNode(model, sections),
                new CoursePlannerNode(model, courseData, graduation),
                new SubgraphOutputNode(),
                new SubgraphErrorHandlerNode(), new SubgraphFatalErrorNode());
    }

    private static CompiledGraph<SubgraphState> build(
            DispatcherNode dispatcher, RecommenderNode recommender,
            SchedulerNode scheduler, CoursePlannerNode coursePlanner,
            SubgraphOutputNode output,
            SubgraphErrorHandlerNode errorHandler, SubgraphFatalErrorNode fatalError) throws Exception {

        return new StateGraph<>(SubgraphState.SCHEMA, SubgraphState::new)
                .addNode("dispatcher",              node_async(dispatcher))
                .addNode("recommender",             node_async(recommender))
                .addNode("scheduler",               node_async(scheduler))
                .addNode("course_planner",          node_async(coursePlanner))
                .addNode("subgraph_output",         node_async(output))
                .addNode("subgraph_error_handler",  node_async(errorHandler))
                .addNode("subgraph_fatal_error",    node_async(fatalError))
                .addEdge(START, "dispatcher")
                .addConditionalEdges("dispatcher", edge_async(dispatcher::route),
                        Map.of("recommender",             "recommender",
                               "scheduler",               "scheduler",
                               "course_planner",          "course_planner",
                               "subgraph_output",         "subgraph_output",
                               "subgraph_error_handler",  "subgraph_error_handler"))
                .addConditionalEdges("recommender", edge_async(recommender::route),
                        Map.of("dispatcher",              "dispatcher",
                               "subgraph_output",         "subgraph_output",
                               "subgraph_error_handler",  "subgraph_error_handler"))
                .addConditionalEdges("scheduler", edge_async(scheduler::route),
                        Map.of("dispatcher",              "dispatcher",
                               "subgraph_output",         "subgraph_output",
                               "subgraph_error_handler",  "subgraph_error_handler"))
                .addConditionalEdges("course_planner", edge_async(coursePlanner::route),
                        Map.of("dispatcher",              "dispatcher",
                               "subgraph_output",         "subgraph_output",
                               "subgraph_error_handler",  "subgraph_error_handler"))
                .addConditionalEdges("subgraph_error_handler", edge_async(errorHandler::route),
                        Map.of("recommender",          "recommender",
                               "scheduler",            "scheduler",
                               "course_planner",       "course_planner",
                               "dispatcher",           "dispatcher",
                               "subgraph_fatal_error", "subgraph_fatal_error"))
                .addEdge("subgraph_fatal_error", END)
                .addEdge("subgraph_output", END)
                .compile();
    }
}
