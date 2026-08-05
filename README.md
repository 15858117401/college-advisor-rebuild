# College Advisor Rebuild

Python 重建项目。原 Java 项目位于 `college_advisor/`，只作为本地参考，不会由外层 Git 仓库跟踪。

## DeepSeek 与 LangGraph 配置

真实 API Key 只写入根目录的 `.env`：

```dotenv
DEEPSEEK_API_KEY=你的真实_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

安装依赖并运行测试：

```bash
uv sync
uv run pytest
```

启动 LangGraph 本地开发服务：

```bash
uv run langgraph dev
```

目前的 graph 只完成 DeepSeek LLM client 绑定。后续业务节点可以从 `app/graph.py` 继续扩展。
