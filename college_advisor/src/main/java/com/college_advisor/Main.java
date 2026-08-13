package com.college_advisor;

import com.college_advisor.service.graph.ParentGraph;

import java.util.List;
import java.util.Map;

/**
 * 骨架验收入口。
 *
 * 测试 2/3：临时修改 RouterNode.apply() 中 routeDecision 的返回值：
 *   "planner"          → 复合任务路径
 *   "build_single_plan" → 单任务路径
 *   "clarify"          → 反问路径
 */
public class Main {

    public static void main(String[] args) throws Exception {

        var graph = ParentGraph.build();

        System.out.println("=== 测试 1: simple_task 路径（默认）===");
        graph.invoke(Map.of(
                "userInput", "帮我选课",
                "messages",  List.of()
        )).get();

        System.out.println("\n骨架运行完成。");
        System.out.println("修改 RouterNode.apply() 中的 routeDecision 值可验证其余路径：");
        System.out.println("  \"planner\"           → 复合任务路径");
        System.out.println("  \"build_single_plan\" → 单任务路径");
        System.out.println("  \"clarify\"           → 反问路径");
    }
}
