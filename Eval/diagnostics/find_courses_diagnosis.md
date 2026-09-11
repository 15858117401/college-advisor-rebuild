# `find_courses` 频繁调用诊断报告

## 结论

问题已稳定复现。相同输入的三次完整运行分别调用 `find_courses` 13、3、20 次，
总耗时分别为 74.59、56.99、66.64 秒。三次 Planner 改写的语义一致，Router 都选择
`advising`，因此 Planner 和 Router 不是调用次数差异的来源。

直接原因是 `gen_ed` 的接口契约和数据库匹配规则不完整：

- `FindCoursesInput.gen_ed` 只接受任意字符串，没有给模型合法类别值或类别发现能力。
- Supabase RPC 对拆分后的 Gen Ed 标签执行忽略大小写、去除首尾空格后的**完整相等**匹配。
- 用户和模型首先使用 `US Minority`，实际标签是
  `Cultural Studies - US Minority`，因此第一次搜索在三次运行中都返回空列表。
- 空结果没有说明“类别名称无效”或返回合法候选值。模型随后猜测多个别名，并且每次参数
  不同；它何时猜中准确标签决定了总调用次数。

这不是 Supabase 异常、参数校验失败、结果未进入下一轮上下文或同一调用的并发重放。
36 次搜索全部正常完成、没有校验错误。每一批 ToolMessage 都在下一轮模型输入中可见。

现有循环保护没有触发属于预期行为。它按工具名、规范化参数和结果识别重复，并在同一组合
连续出现三次后才纠偏。第一轮只有 `gen_ed=Cultural Studies` 完全重复两次；其余失败调用
都使用不同字符串。第二轮和第三轮没有完全相同的参数。保护器因此把这些调用视为不同搜索，
无法识别“围绕同一个类别不断猜别名”的语义循环。

## 调用轨迹

所有有效的精确类别搜索都返回同一顺序：
`AAS 211, AAS 246, PORT 150, AFRO 224, GWS 282`。这证明数据和排序本身稳定。

### 运行 1：13 次搜索

| # | 模型轮次 | 关键参数 | 结果和作用 |
|---:|---:|---|---|
| 1 | 1 | `gen_ed=US Minority` | 空；错误类别名 |
| 2 | 2 | `gen_ed=US Minority Culture` | 空；猜测别名 |
| 3 | 2 | `gen_ed=US Minority Studies` | 空；猜测别名 |
| 4 | 2 | `gen_ed=Minority` | 空；猜测别名 |
| 5 | 2 | `gen_ed=Cultural Studies` | 空；不完整类别名 |
| 6 | 3 | `gen_ed=Advanced Composition` | 返回 5 门，但不验证 US Minority |
| 7 | 3 | `gen_ed=Humanities` | 空；错误类别名 |
| 8 | 3 | `subjects=AFRO,AAS,LLS,GWS` | 返回 5 门，但科目不能证明 Gen Ed 类别 |
| 9 | 3 | `description_query=...race and ethnicity...` | 返回 5 门语义候选，但不能证明 Gen Ed 类别 |
| 10 | 4 | `gen_ed=US Minority Cultures` | 空；猜测别名 |
| 11 | 4 | `gen_ed=Non-Western Cultures` | 空；错误类别 |
| 12 | 4 | `gen_ed=Cultural Studies` | 空；与第 5 次完全重复 |
| 13 | 5 | `gen_ed=Cultural Studies - US Minority` | 有效；返回正确 Top 5 |

运行 1 中，只有第 13 次直接满足用户条件；第 6、8、9 次产生了数据，但放松或改变了
用户条件，属于无效旁路。模型还为旁路结果调用了三次 `get_course_details`，之后才找到准确标签。

### 运行 2：3 次搜索

| # | 模型轮次 | 关键参数 | 结果和作用 |
|---:|---:|---|---|
| 1 | 1 | `gen_ed=US Minority` | 空；错误类别名 |
| 2 | 2 | `gen_ed=US Minority Cultures` | 空；猜测别名 |
| 3 | 2 | `gen_ed=Cultural Studies - US Minority` | 有效；返回正确 Top 5 |

### 运行 3：20 次搜索

| # | 模型轮次 | 关键参数 | 结果和作用 |
|---:|---:|---|---|
| 1 | 1 | `gen_ed=US Minority` | 空；错误类别名 |
| 2 | 2 | `description_query=US Minority gen ed course; gen_ed=US Minority` | 空；错误精确筛选仍生效 |
| 3 | 3 | `gen_ed=US Minority Cultures` | 空；猜测别名 |
| 4 | 3 | `description_query=US Minority gen ed course` | 返回 5 门，但不能证明 Gen Ed 类别 |
| 5 | 4 | `gen_ed=US Minority Culture` | 空；猜测别名 |
| 6 | 4 | `gen_ed=Cultural Studies` | 空；不完整类别名 |
| 7 | 4 | `gen_ed=Humanities & the Arts` | 空；错误类别名 |
| 8 | 4 | `gen_ed=Social & Behavioral Sciences` | 空；错误类别名 |
| 9 | 5 | `gen_ed=USM` | 空；猜测缩写 |
| 10 | 5 | `gen_ed=us minority` | 空；大小写不是问题，标签仍不完整 |
| 11 | 5 | `gen_ed=Advanced Composition` | 返回 5 门，但不验证 US Minority |
| 12 | 5 | `description_query=...US Minority...; gen_ed=Cultural Studies` | 空；错误精确筛选仍生效 |
| 13 | 6 | `gen_ed=U.S. Minority Cultures` | 空；猜测别名 |
| 14 | 6 | `gen_ed=US Minorities` | 空；猜测别名 |
| 15 | 6 | `gen_ed=Minority Cultures` | 空；猜测别名 |
| 16 | 6 | `gen_ed=United States Minority Cultures` | 空；猜测别名 |
| 17 | 7 | `gen_ed=Minority` | 空；猜测别名 |
| 18 | 7 | `gen_ed=Race and Ethnicity` | 空；错误类别名 |
| 19 | 7 | `gen_ed=US Minority Cultures (USM)` | 空；猜测别名 |
| 20 | 7 | `gen_ed=Cultural Studies - US Minority` | 有效；返回正确 Top 5 |

三次运行都在第一次调用 `find_courses` 的同时加载
`course_and_section_recommendation` skill。该 skill 明确要求空结果后不要重复或放松条件，
但模型仍然猜测替代标签。它也要求继续查询 Spring 2026 sections 和课程教师历史 GPA，
因此成功搜索后每次还有 2 次 `get_course_sections` 和 2 次
`get_course_instructor_gpas`。是否默认附带班次是产品行为选择，不是本次搜索循环的根因。

## 实施验证

`gen_ed` 已于后续实现中改为当前 15 个规范类别组成的枚举，并允许 `null`。使用同一输入
连续复现两次，两次都在第一次搜索时选择了 `Cultural Studies - US Minority`，且每次仅调用
一次 `find_courses`。两次均返回相同顺序：
`AAS 211, AAS 246, PORT 150, AFRO 224, GWS 282`。

修复后的轨迹保存在 `find_courses_trace_20260911_142430.jsonl`，最终状态摘要保存在
`find_courses_results_20260911_142430.json`。

## 后续建议

1. **已实施 Gen Ed 参数契约修复。** `gen_ed` 现在只接受表中的 15 个规范值或 `null`，
   工具 schema 会直接把这些值作为 enum 提供给模型。
2. **区分“无效类别名”和“合法类别但无课程”。** 对未知 `gen_ed` 返回可恢复的验证错误和
   合法候选，而不是普通 `[]`。这样模型能一次修正，不会把类别拼写问题误判为数据为空。
3. **再考虑语义级无进展保护。** 若同一用户条件在连续轮次中只替换 `gen_ed` 字符串且持续
   返回空结果，可要求先使用类别发现能力。不能简单设置总调用上限，否则会影响真正包含
   多个条件组的请求。
4. **让 GPA 证据随搜索结果返回。** RPC 已返回 `overall_gpa` 并据此排序，但
   `_format_results` 只保留 course code 和 credits。保留 `overall_gpa` 可减少为解释
   “GPA 高”而补查详情的需要；这不是重复搜索的直接原因。
5. **单独决定 section 默认行为。** 当前仅有的匹配 skill 面向“课程 + section + 教师 GPA”。
   如果普通课程推荐不应自动查询班次，应拆分 generic course recommendation skill，或仅在
   用户明确要求当前学期班次时加载现有 skill。该决定需要产品确认。

Planner 不应承担 Gen Ed 别名解析；它当前三次都正确保留了用户含义。把数据域的规范值放在
工具契约或专门的发现工具中更稳定，也适用于 Catalog Lookup 和 Advising 两条路径。

## 复现和验证

诊断 runner 使用 LangChain callback 旁路观察现有图，不修改提示词、skills、工具参数、
返回结果或控制流。每条 JSONL 事件包含复现编号、模型节点和轮次、callback/parent run ID、
工具名、原始参数、Pydantic 规范化参数、结果、状态和耗时；并发调用按 callback run ID 配对。
非搜索工具的大段输出只记录长度和哈希，避免写入完整 skill 内容。

```bash
.venv/bin/python Eval/diagnose_find_courses.py --runs 2
```

本次证据文件：

- `find_courses_trace_20260911_135840.jsonl`：运行 1 和运行 2 的完整轨迹。
- `find_courses_results_20260911_135840.json`：前两次最终状态摘要。
- `find_courses_trace_20260911_140106.jsonl`：差异明显后增加的运行 3 轨迹。
- `find_courses_results_20260911_140106.json`：第三次最终状态摘要。

诊断相关测试命令：

```bash
.venv/bin/python -m pytest -q \
  tests/test_find_courses_diagnostics.py \
  tests/test_react_agent.py \
  tests/test_course_search_tool.py
```

结果为 `50 passed, 10 subtests passed`。测试覆盖并发工具调用的 ID 配对、参数规范化、非搜索
ToolMessage 正文省略和循环保护事件记录。运行前的相关基线为
`56 passed, 1 failed, 10 subtests passed`；唯一
失败是工作区已有的 Router prompt 编辑删除了 profile precedence 文本，与本次诊断无关。
