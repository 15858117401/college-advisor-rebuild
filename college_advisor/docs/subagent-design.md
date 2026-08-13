# Sub-Agent Design

## 设计原则

- 每个 sub-agent 是一个 Node，实现 `NodeAction<MainState>`
- 内部调用 `ReactAgent.run(userInput, tools, prompt)` 执行 ReAct 循环
- prompt 从 `src/main/resources/prompts/{agentName}.txt` 加载
- tools = base tools（必选）+ 自己的专属 tools（可选，通过 `toolRegistry.plus()` 叠加）
- 执行结果写入 `MainState.response` 或聚合到 plan 的结果集中

---

## Sub-Agents

### RecommenderNode
- **路由名**: `recommender`
- **职责**: 根据用户需求推荐课程；若符合条件的课程过多，自动收紧筛选条件（提高 avg_gpa 要求、降低 workload、降低 difficulty 等），直到结果数量合理
- **调用**: `ReactAgent.run(userInput, tools, prompt)`
- **Tools**: base tools，不额外叠加
- **Prompt**: `prompts/recommender.txt`
- **特殊逻辑**: 收紧条件这一层由 RecommenderNode 自身控制（判断结果数量 → 调整参数 → 重新调 ReactAgent）

---

### SchedulerNode
- **路由名**: `scheduler`
- **职责**: 给定一组课程，排出时间不冲突、workload 均衡的学期课表
- **调用**: `ReactAgent.run(userInput, tools, prompt)`
- **Tools**: base tools，不额外叠加
- **Prompt**: `prompts/scheduler.txt`

---

### CoursePlannerNode
- **路由名**: `course_planner`
- **职责**: 综合课程规划，包括 GPA 目标、毕业要求对照、多学期修读路径规划
- **调用**: `ReactAgent.run(userInput, tools, prompt)`
- **Tools**: base tools，不额外叠加
- **Prompt**: `prompts/course_planner.txt`

---
