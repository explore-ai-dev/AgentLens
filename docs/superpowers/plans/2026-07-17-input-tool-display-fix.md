# AgentLens 输入与工具显示修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Windows 终端中中文输入无法进入 Textual 输入框的问题，并让工具调用/任务提示在 provider 未触发实时事件时仍能清晰诊断和显示。

**Architecture:** 保留现有 Textual TUI、AgentChatRunner 和 AgentLoop 边界。输入修复只调整 `ComposerTextArea` 的事件处理和测试；工具显示修复集中在 TUI/runtime 的可观测性与历史兜底，不改变工具执行、权限或 task boundary 的核心语义。所有显示均以真实 provider tool call 或真实 tool event 为依据，不把模型普通文本误判为工具调用。

**Tech Stack:** Python 3.11+, Textual 8.2.8, pytest, Rich, existing OpenAI-compatible provider adapters.

## Global Constraints

- 不修改 AgentLoop 的工具执行顺序、权限判断或 session 事件格式。
- 保留 `Enter` 提交、`Shift+Enter` 换行行为。
- `task_boundary` 继续作为内部控制工具隐藏，不在普通工具列表中显示。
- Todo 面板只在真实 `todo` 工具成功返回合法 todos 数据时显示。
- 不记录或输出 API key；诊断信息只能包含 provider 名称、模型名称、tool-call 能力和调用数量。
- 中文输入验证必须覆盖“输入框文本可见”和“提交给 runner 的文本正确”两个结果。
- 本项目当前目录不是 Git 仓库，不能执行 commit；完成后报告未提交原因。

---

### Task 1: 为中文输入建立可复现测试

**Files:**
- Modify: `tests/test_app_tui.py`（在现有 `ComposerTextArea`/输入测试附近添加）
- Inspect: `firstcoder/app/tui.py:97-114`

**Interfaces:**
- Consumes: `AgentLensApp`, `ComposerTextArea`, `FakeAsyncChatRunner` 现有测试夹具。
- Produces: 一个稳定的回归测试，证明 Unicode 中文文本可以进入输入框并被 runner 接收。

- [ ] **Step 1: 添加输入框 Unicode 回归测试**

使用 Textual pilot 直接向输入组件发送 Unicode 文本，然后断言输入框仍保留文本；再提交并断言 runner 收到原文。测试形态应与现有 [tests/test_app_tui.py:477-496](tests/test_app_tui.py#L477-L496) 一致：

```python
@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_firstcoder_app_submits_unicode_text_from_composer() -> None:
    runner = FakeAsyncChatRunner()
    app = AgentLensApp(chat_runner=runner)

    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.click("#input")
        input_widget = app.query_one("#input", TextArea)
        input_widget.load_text("请读取 README.md 并说明项目结构")
        assert input_widget.text == "请读取 README.md 并说明项目结构"
        await pilot.press("enter")
        await pilot.pause()

    assert runner.inputs == ["请读取 README.md 并说明项目结构"]
```

- [ ] **Step 2: 运行测试确认当前行为**

运行：

```bash
cd "d:/桌面/实习/AgentLens"
.venv/Scripts/python.exe -m pytest tests/test_app_tui.py::test_firstcoder_app_submits_unicode_text_from_composer -q
```

预期：测试应作为基线运行；如果 `load_text` 路径通过而真实键盘路径失败，记录这是 Textual Windows IME 事件层问题，不把测试误认为已覆盖 IME。

- [ ] **Step 3: 添加可测试的 Unicode 插入辅助路径**

在 `ComposerTextArea` 中增加一个只负责插入文本的方法，保持提交事件逻辑独立：

```python
def insert_text_from_input_method(self, text: str) -> None:
    if not text:
        return
    self.insert(text)
```

测试该方法不会丢弃中文，并且不触发提交事件。不要在该步骤修改 Enter/Shift+Enter 行为。

- [ ] **Step 4: 运行输入相关测试**

运行：

```bash
.venv/Scripts/python.exe -m pytest tests/test_app_tui.py -q
```

预期：现有 TUI 测试全部通过，新增中文测试通过。

- [ ] **Step 5: 记录终端限制并验证真实启动路径**

使用 Windows Terminal 启动：

```bat
cd /d d:\桌面\实习\AgentLens
启动AgentLens.cmd
```

验证中文候选词确认后是否进入输入框。若 Textual 8.2.8 仍没有产生可消费的输入事件，不能伪称 Python 层已修复；在最终报告中明确指出需要升级 Textual/Windows Terminal 或改用支持 IME 的 GUI 输入层，并保留 `load_text`/辅助方法作为程序内 Unicode 兜底。

---

### Task 2: 为工具调用和任务提示增加可观测性测试

**Files:**
- Modify: `firstcoder/app/tui.py:743-774, 896-927`
- Modify: `firstcoder/app/runtime.py:319-366`
- Test: `tests/test_app_tui.py`（工具事件和响应测试附近）
- Test: `tests/test_app_runtime.py`（display line 测试附近）

**Interfaces:**
- Consumes: `ToolExecutionEvent`, `ChatResponse`, `AgentMessage`, `last_display_lines`。
- Produces: 非敏感的工具调用诊断状态，以及在实时事件缺失时保留历史 tool call/result 摘要的显示行为。

- [ ] **Step 1: 添加历史工具摘要测试**

在 `tests/test_app_runtime.py` 添加测试，构造 assistant tool_call 和 tool result 消息，确认 `_display_lines_from_messages` 生成：

```python
[
    "Tool call: view {\"path\": \"README.md\"}",
    "Tool result: view success: README content",
]
```

同时确认 `task_boundary` 仍不出现在结果中。测试必须使用 `ensure_ascii=False` 的中文 tool result，验证摘要不会破坏 Unicode。

- [ ] **Step 2: 添加 TUI 实时工具事件显示测试**

构造假的 chat runner，触发 started/finished 两个 `ToolExecutionEvent`，然后断言 transcript 中存在 tool entry，且状态分别为 `running` 和 `success`。复用 `tests/test_app_tui.py` 已有 fake runner 和 tool event 测试模式，不直接调用真实 provider。

- [ ] **Step 3: 添加实时事件缺失时的显示测试**

构造 runner：

- `tool_event_handler` 不触发任何事件；
- `last_display_lines` 返回 `Tool call: view ...`、`Tool result: view success: ...` 和最终回答；
- 运行 `_write_chat_response`。

断言两个工具摘要和最终回答都出现在 transcript 中。该测试锁定的规则是：只有确实收到实时事件时才过滤历史工具行；没有实时事件时不能静默丢失历史工具行。

- [ ] **Step 4: 增加非敏感诊断字段**

在 `AgentChatRunner` 增加只读状态字段：

```python
last_tool_call_count: int = 0
last_tool_result_count: int = 0
```

每轮开始时清零；在 `_display_lines_from_messages` 或其调用点统计本轮新增 assistant tool_call 和 tool_result。不要保存 arguments 原文、API key 或完整工具输出到诊断字段。

- [ ] **Step 5: 在工具不可用时显示明确状态**

在 `_write_chat_response` 的最终显示逻辑中，仅当以下条件同时满足时添加一条系统提示：

```python
response_has_no_tool_calls
provider_capabilities.supports_tools is False
```

提示应明确说明当前 provider/model 未启用 tool calling，而不是说“工具执行失败”。如果 provider 支持 tools 但模型本轮没有调用工具，不添加误导性错误，只显示最终回答。

- [ ] **Step 6: 运行工具显示测试**

运行：

```bash
.venv/Scripts/python.exe -m pytest tests/test_app_runtime.py tests/test_app_tui.py -q
```

预期：所有已有和新增测试通过；实时工具事件、历史兜底、task_boundary 隐藏、todo 面板测试均不回归。

---

### Task 3: 运行完整验证并检查实际配置

**Files:**
- Inspect only: `.env`, `firstcoder/config/settings.py`, `firstcoder/app/factory.py:224-230`
- No source changes unless Task 1/2 tests identify a concrete regression.

**Interfaces:**
- Consumes: completed input and display changes.
- Produces: reproducible verification report explaining whether the configured provider returns native tool calls.

- [ ] **Step 1: 检查有效配置，不打印密钥**

运行：

```bash
cd "d:/桌面/实习/AgentLens"
.venv/Scripts/python.exe -m firstcoder.cli config show
```

预期只核对 provider、model、base URL、配置文件路径和 streaming/parallel tool calls 状态；输出中不得出现 API key。

- [ ] **Step 2: 运行完整测试套件**

运行：

```bash
.venv/Scripts/python.exe -m pytest -q
```

记录通过数、失败数和首个失败堆栈；如果失败来自环境依赖，不能报告为全部通过。

- [ ] **Step 3: 实际 TUI 验证中文输入**

在 Windows Terminal 中运行启动脚本，确认：

1. 英文输入仍可见；
2. 中文候选词确认后是否可见；
3. Enter 后 runner 是否收到完整中文；
4. Shift+Enter 仍能换行。

- [ ] **Step 4: 实际验证工具链**

发送一个明确需要读取项目文件的任务，例如“读取 README.md，概括项目结构”。观察：

1. provider 是否返回 native tool call；
2. UI 是否出现工具开始/完成状态；
3. 是否显示最终回答；
4. 如果没有 tool call，UI 是否给出 provider 能力提示；
5. 只有模型真实调用 `todo` 时才显示 Todo 面板。

- [ ] **Step 5: 汇总结果**

最终报告必须分别说明：

- 代码级测试是否通过；
- Windows Terminal 实际中文 IME 是否通过；
- 当前 `dasuapi` provider/model 是否返回 tool calls；
- 工具调用没显示时究竟是 UI 事件链断裂、provider 不支持，还是模型没有选择工具；
- 若仍受 Textual Windows IME 限制，给出明确可行的运行方式，不声称已完全修复。

---

## 自审清单

- 中文输入、工具事件、历史兜底、provider 能力提示和实际验证均有对应任务。
- 没有修改 AgentLoop 核心执行逻辑，也没有把普通模型文本误判成工具调用。
- 所有新增诊断字段均不包含密钥、完整参数或敏感工具输出。
- `task_boundary` 隐藏规则和 Todo 面板真实调用规则保持不变。
- 当前目录不是 Git 仓库，因此不安排 commit 步骤；实现结束后报告文件变更和测试结果。
