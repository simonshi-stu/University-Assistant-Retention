# 三角色可审计开发工作流

## 目的

这套工作流把“谁提出任务、谁写第一版、谁修改、谁验收”变成仓库里的
可核验记录，而不是只靠聊天记忆。它只服务于项目开发，不是数据管道的
运行依赖；分析、模型和看板在运行时不会调用任何大模型。

## 固定角色

- **GPT-5.6 Sol**：监督者和规划者。创建任务、写清范围和验收标准，最后
  逐条判定通过或不通过。
- **DeepSeek V4.1 Flash**：第一版执行者。每个任务 ID 最多调用一次。超时、
  网络错误、空回复也算已经使用这一次机会。
- **GPT-5.6 Luna**：代码审核和直接修订者。检查 DeepSeek 的结果；发现小的
  或明确的问题时直接修改，并把修改文件的 SHA-256 写入审计记录。

## 不来回打乒乓的规则

```text
Sol 规划
   ↓
DeepSeek 执行一次
   ↓成功或失败
Luna 审核、直接修正或记录 blocked
   ↓
Sol 逐条验收 ─────拒绝──→ Sol 新建修订任务
   ↓通过
任务完成
```

同一任务不能第二次调用 DeepSeek。即使调用失败，Luna 也必须登记 `blocked`，
Sol 必须登记 `rejected`。之后才能用 `revise` 创建新的子任务。新任务有新的
唯一 ID，并记录 `parent_task_id`；旧任务保留原始事实并标记为 `superseded`。

## 一个任务包含什么

每个任务位于 `workflow/tasks/<task_id>/`：

```text
task.json                 当前状态投影
events.jsonl              追加式、SHA-256 串联事件日志
stages/sol_plan.json      Sol 计划和验收标准
stages/deepseek_request.json
stages/deepseek_response.json 或 deepseek_failure.json
stages/luna_review.json
stages/sol_acceptance.json
```

阶段文件用独占创建方式写入，不能覆盖。`events.jsonl` 中每个事件都包含前一个
事件的哈希。`verify` 会重新计算事件链、阶段文件哈希，以及 Luna 审核过的文件
哈希。它能发现事后改动，但不是数字签名，也不能防止拥有仓库写权限的人重写
全部历史；Git 提交和远端历史用于补足这一层追溯。

API 密钥只从未提交的 `.env` 或进程环境读取。密钥不进入请求记录、响应记录、
事件日志或命令输出。DeepSeek 的推理内容也不保存，只保存最终可见回复。

## 使用方法

先做离线配置检查（不会联网）：

```powershell
python scripts/agent_workflow.py doctor
```

创建任务：

```powershell
python scripts/agent_workflow.py create `
  --objective "接入 Course Explorer API" `
  --scope "只实现数据适配器和离线测试" `
  --allowed-path "src/course_retention" `
  --allowed-path "tests" `
  --criterion "API 字段映射有数据字典" `
  --criterion "离线测试通过"
```

命令会返回唯一任务 ID。随后执行且只能执行一次：

```powershell
python scripts/agent_workflow.py execute <task_id>
```

Luna 审核；若直接改了文件，要逐个登记：

```powershell
python scripts/agent_workflow.py review <task_id> `
  --verdict corrected `
  --notes "修正字段映射与测试" `
  --changed-file "src/course_retention/course_explorer.py" `
  --changed-file "tests/test_course_explorer.py"
```

Sol 必须使用任务中完全相同的验收标准逐条判定：

```powershell
python scripts/agent_workflow.py accept <task_id> `
  --decision accepted `
  --notes "离线测试与范围检查均通过" `
  --result "API 字段映射有数据字典::pass" `
  --result "离线测试通过::pass"
```

查看和验证：

```powershell
python scripts/agent_workflow.py show <task_id>
python scripts/agent_workflow.py verify <task_id>
```

失败或拒绝后，Sol 修改任务说明并创建新 ID：

```powershell
python scripts/agent_workflow.py revise <old_task_id> `
  --objective "缩小范围并明确返回格式"
```

未提供的范围、允许路径和验收标准会继承旧任务。

## 状态规则

合法主链为：

`planned → deepseek_completed → luna_reviewed → sol_accepted/sol_rejected`

DeepSeek 失败时仍要走完整闭环：
`planned → deepseek_failed → luna_reviewed(blocked) → sol_rejected`。
只有 `sol_rejected` 可以生成修订任务；生成后旧任务变为 `superseded`。

## 引导记录

工作流建立前已经发生的两次 DeepSeek 调用保存在 `workflow/bootstrap/`。
它们是迁移说明，不伪装成由新状态机自动生成的完整事件链。新工作流启用后的
任务必须进入 `workflow/tasks/` 并通过 `verify`。
