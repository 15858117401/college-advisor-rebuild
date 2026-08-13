# Multi-Turn Conversation Design

**Date:** 2026-04-29  
**Status:** Approved

## Goals

两个核心场景：

1. **Clarify 后继续执行**：ClarifyNode 问了问题 → 用户回答 → 系统用回答继续执行原始任务
2. **上下文追问**：用户能用"那门课"、"上次推荐的"等指代上一轮结果

## Approach

方案 A：图外管理历史（ConversationService 封装图调用，历史通过 MainState 注入）。图结构不变。

## Data Model

### Supabase 表结构

```sql
-- 用户层（支持多用户、未来长记忆）
CREATE TABLE users (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz DEFAULT now()
);

-- 会话层（一次对话 session）
CREATE TABLE conversations (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid REFERENCES users(id),
    created_at timestamptz DEFAULT now()
);

-- 消息层（每条消息一行）
CREATE TABLE messages (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid REFERENCES conversations(id),
    role            text NOT NULL,  -- 'user' 或 'assistant'
    content         text NOT NULL,
    turn_index      int  NOT NULL,
    created_at      timestamptz DEFAULT now()
);
```

三层关系：`users → conversations → messages`。未来长记忆可加 `user_memory` 表挂在 `users` 下。

### Java 模型

```java
record ConversationMessage(String role, String content, int turnIndex)
    implements Serializable {}
```

### MainState 新增字段

```java
SCHEMA.put("conversationId",      Channels.base(() -> ""));
SCHEMA.put("userId",              Channels.base(() -> ""));
SCHEMA.put("conversationHistory", Channels.base(ArrayList::new));
```

对应 accessor：

```java
public String conversationId() { ... }
public String userId() { ... }
public List<ConversationMessage> conversationHistory() { ... }
```

## Components

### ConversationStore（接口 + Supabase 实现）

```java
public interface ConversationStore {
    List<ConversationMessage> loadHistory(String conversationId);
    void appendMessage(String conversationId, String role, String content);
    String createConversation(String userId);  // 返回新 conversationId
}

public class SupabaseConversationStore implements ConversationStore {
    // 使用现有 JdbcTemplate
}
```

### ConversationService（图的唯一入口）

```java
public class ConversationService {

    public String chat(String userId, String conversationId, String userInput) {
        // 1. 从 DB 读取历史
        List<ConversationMessage> history = store.loadHistory(conversationId);

        // 2. 调用图，历史通过 state 注入
        var result = graph.invoke(Map.of(
            "userInput",           userInput,
            "userId",              userId,
            "conversationId",      conversationId,
            "conversationHistory", history
        )).get();

        String response = ((MainState) result).response();

        // 3. 写入本轮对话
        store.appendMessage(conversationId, "user",      userInput);
        store.appendMessage(conversationId, "assistant", response);

        return response;
    }
}
```

## History Flow Into Graph

历史只注入需要上下文的节点，**不改动 ReactAgent**（执行节点接收的已是明确 goal，不需要历史）。

| 节点 | 用历史吗 | 方式 |
|------|---------|------|
| RouterNode | ✅ | 历史拼成字符串前置到 classify prompt |
| ClarifyNode | ✅ | 历史拼成字符串，避免重复提问 |
| SingleTaskNode | ✅ | 历史作为 goal 构造的上下文 |
| MultiTaskNode | ✅ | 同上 |
| ReactAgent（执行层）| ❌ | 不需要，输入已是明确 goal |

### 历史字符串格式（Router / ClarifyNode / 规划节点）

```java
String historyText = history.stream()
    .map(m -> m.role() + ": " + m.content())
    .collect(Collectors.joining("\n"));

String fullPrompt = historyText.isEmpty()
    ? userInput
    : historyText + "\n\n用户最新消息：" + userInput;
```

## Clarify 后继续执行

不需要改图结构。Clarify 回答本质是用户的下一轮消息，历史中已包含"助手问了什么"。Router 看到上下文后自然能理解是对澄清问题的回答。

**Router prompt 需要新增规则：**

> 如果对话历史中助手最后一条消息是一个问题，且用户当前消息是在回答这个问题，则将用户回答与原始任务合并后路由，不要再路由到 clarify。

**示例流程：**

```
轮 1：用户 → "帮我安排课表"
      系统 → clarify → "你希望几点前不上课？"

轮 2：用户 → "9点以前不上课"
      Router 看到历史，识别这是对澄清问题的回答
      → 路由到 build_single_plan，正常执行
```

## Out of Scope

- 传输层（HTTP / WebSocket）：调用方直接调用 `ConversationService.chat()`
- 长记忆（跨 session 的用户偏好）：预留 `users` 表，后续单独设计
- 前端 UI
