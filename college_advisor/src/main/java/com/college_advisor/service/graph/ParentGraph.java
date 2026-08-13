package com.college_advisor.service.graph;

import com.college_advisor.service.graph.client.RouterClient;
import com.college_advisor.service.graph.nodes.*;
import com.college_advisor.service.tools.CourseDataTools;
import com.college_advisor.service.tools.CourseSectionTools;
import com.college_advisor.service.tools.GraduationTools;
import com.college_advisor.service.tools.ProfessorRatingTools;
import com.college_advisor.service.tools.SkillTools;
import dev.langchain4j.model.chat.ChatModel;
import com.college_advisor.service.graph.nodes.error.ErrorHandlerNode;
import com.college_advisor.service.graph.nodes.error.FatalErrorNode;
import com.college_advisor.service.graph.nodes.executionNodes.PlanNode.SingleTaskNode.SingleTaskNode;
import com.college_advisor.service.graph.nodes.executionNodes.ClarifyNode.ClarifyNode;
import com.college_advisor.service.graph.nodes.executionNodes.PlanNode.ExecutionSubGraphNode.ExecutionSubgraphNode;
import com.college_advisor.service.graph.nodes.executionNodes.PlanNode.MultiTaskNode.MultiTaskNode;
import com.college_advisor.service.graph.nodes.executionNodes.SimpleTaskNode.SimpleTaskNode;
import com.college_advisor.service.graph.nodes.routerNode.RouterNode;
import com.college_advisor.service.graph.state.MainState;
import com.college_advisor.service.graph.nodes.OutputNode;
import org.bsc.langgraph4j.CompiledGraph;
import org.bsc.langgraph4j.StateGraph;

import java.util.Map;

import static org.bsc.langgraph4j.StateGraph.END;
import static org.bsc.langgraph4j.StateGraph.START;
import static org.bsc.langgraph4j.action.AsyncEdgeAction.edge_async;
import static org.bsc.langgraph4j.action.AsyncNodeAction.node_async;

public class ParentGraph {

    public static CompiledGraph<MainState> build() throws Exception {
        return build("simple_task");
    }

    /**
     * Production mode — all active nodes use langchain4j ChatModel.
     */
    public static CompiledGraph<MainState> build(
            RouterClient routerClient,
            ChatModel chatModel,
            CourseDataTools courseData,
            CourseSectionTools courseSections,
            GraduationTools graduation,
            ProfessorRatingTools profRating,
            SkillTools skill) throws Exception {

        var router      = new RouterNode(routerClient);
        var clarify     = new ClarifyNode(chatModel);
        var simpleTask  = new SimpleTaskNode(chatModel, courseData, courseSections, graduation, profRating);
        var buildSingle = new SingleTaskNode(chatModel);
        var planner     = new MultiTaskNode(chatModel);
        var execSub     = new ExecutionSubgraphNode(chatModel, courseData, courseSections, graduation, profRating, skill);
        var errHandler  = new ErrorHandlerNode();
        var fatalErr    = new FatalErrorNode();
        var output      = new OutputNode();

        return buildGraph(router, clarify, simpleTask, buildSingle, planner, execSub,
                errHandler, fatalErr, output);
    }

    /**
     * No-DB test mode — real router + real ClarifyNode/SingleTaskNode/MultiTaskNode, stub ExecutionSubgraph.
     */
    public static CompiledGraph<MainState> build(
            RouterClient routerClient,
            ChatModel chatModel) throws Exception {

        var router      = new RouterNode(routerClient);
        var clarify     = new ClarifyNode(chatModel);
        var simpleTask  = new SimpleTaskNode();
        var buildSingle = new SingleTaskNode(chatModel);
        var planner     = new MultiTaskNode(chatModel);
        var execSub     = new ExecutionSubgraphNode();
        var errHandler  = new ErrorHandlerNode();
        var fatalErr    = new FatalErrorNode();
        var output      = new OutputNode();

        return buildGraph(router, clarify, simpleTask, buildSingle, planner, execSub,
                errHandler, fatalErr, output);
    }

    /** 测试用：stub router（固定路由）+ 真实 langchain4j SimpleTaskNode */
    public static CompiledGraph<MainState> build(String forceRoute,
                                                  ChatModel chatModel,
                                                  CourseDataTools courseData,
                                                  CourseSectionTools courseSections,
                                                  GraduationTools graduation,
                                                  ProfessorRatingTools profRating) throws Exception {

        var router      = new RouterNode(forceRoute);
        var clarify     = new ClarifyNode(chatModel);
        var simpleTask  = new SimpleTaskNode(chatModel, courseData, courseSections, graduation, profRating);
        var buildSingle = new SingleTaskNode(chatModel);
        var planner     = new MultiTaskNode(chatModel);
        var execSub     = new ExecutionSubgraphNode();
        var errHandler  = new ErrorHandlerNode();
        var fatalErr    = new FatalErrorNode();
        var output      = new OutputNode();

        return buildGraph(router, clarify, simpleTask, buildSingle, planner, execSub,
                errHandler, fatalErr, output);
    }

    /** 测试用：stub router（固定路由）+ 真实 ClarifyNode/SingleTaskNode/MultiTaskNode（无 DB） */
    public static CompiledGraph<MainState> build(String forceRoute,
                                                  ChatModel chatModel) throws Exception {

        var router      = new RouterNode(forceRoute);
        var clarify     = new ClarifyNode(chatModel);
        var simpleTask  = new SimpleTaskNode();
        var buildSingle = new SingleTaskNode(chatModel);
        var planner     = new MultiTaskNode(chatModel);
        var execSub     = new ExecutionSubgraphNode();
        var errHandler  = new ErrorHandlerNode();
        var fatalErr    = new FatalErrorNode();
        var output      = new OutputNode();

        return buildGraph(router, clarify, simpleTask, buildSingle, planner, execSub,
                errHandler, fatalErr, output);
    }

    /** 测试用：指定 router 的固定路由决策（stub nodes） */
    public static CompiledGraph<MainState> build(String forceRoute) throws Exception {

        var router      = new RouterNode(forceRoute);
        var clarify     = new ClarifyNode();
        var simpleTask  = new SimpleTaskNode();
        var buildSingle = new SingleTaskNode();
        var planner     = new MultiTaskNode();
        var execSub     = new ExecutionSubgraphNode();
        var errHandler  = new ErrorHandlerNode();
        var fatalErr    = new FatalErrorNode();
        var output      = new OutputNode();

        return buildGraph(router, clarify, simpleTask, buildSingle, planner, execSub,
                errHandler, fatalErr, output);
    }

    private static CompiledGraph<MainState> buildGraph(
            RouterNode router, ClarifyNode clarify, SimpleTaskNode simpleTask,
            SingleTaskNode buildSingle, MultiTaskNode planner,
            ExecutionSubgraphNode execSub, ErrorHandlerNode errHandler,
            FatalErrorNode fatalErr, OutputNode output) throws Exception {

        return new StateGraph<>(MainState.SCHEMA, MainState::new)
                .addNode("router",             node_async(router))
                .addNode("clarify",            node_async(clarify))
                .addNode("simple_task",        node_async(simpleTask))
                .addNode("build_single_plan",  node_async(buildSingle))
                .addNode("planner",            node_async(planner))
                .addNode("execution_subgraph", node_async(execSub))
                .addNode("error_handler",      node_async(errHandler))
                .addNode("fatal_error",        node_async(fatalErr))
                .addNode("output",             node_async(output))
                .addEdge(START, "router")
                .addConditionalEdges("router", edge_async(router::route),
                        Map.of("clarify",           "clarify",
                               "simple_task",        "simple_task",
                               "build_single_plan",  "build_single_plan",
                               "planner",            "planner",
                               "error_handler",      "error_handler"))
                .addConditionalEdges("clarify", edge_async(clarify::route),
                        Map.of("output",        "output",
                               "error_handler", "error_handler"))
                .addConditionalEdges("simple_task", edge_async(simpleTask::route),
                        Map.of("output",        "output",
                               "error_handler", "error_handler"))
                .addConditionalEdges("build_single_plan", edge_async(buildSingle::route),
                        Map.of("execution_subgraph", "execution_subgraph",
                               "error_handler",      "error_handler"))
                .addConditionalEdges("planner", edge_async(planner::route),
                        Map.of("execution_subgraph", "execution_subgraph",
                               "error_handler",      "error_handler"))
                .addConditionalEdges("execution_subgraph", edge_async(execSub::route),
                        Map.of("output",        "output",
                               "error_handler", "error_handler",
                               "fatal_error",   "fatal_error"))
                .addConditionalEdges("error_handler", edge_async(errHandler::route),
                        Map.of("router",             "router",
                               "simple_task",        "simple_task",
                               "build_single_plan",  "build_single_plan",
                               "planner",            "planner",
                               "execution_subgraph", "execution_subgraph",
                               "output",             "output",
                               "fatal_error",        "fatal_error"))
                .addEdge("output",      END)
                .addEdge("fatal_error", END)
                .compile();
    }
}
