# Task Plan

Goal: 将本地 coding agent 项目整理为适合公开仓库的新名称，保留内部 Python 包目录 `firstcoder/`，更新公开文档品牌，并上传到 GitHub 组织 `explore-ai-dev`。

## Phases
- [in_progress] Phase 1: 调查项目、Git 状态、公开名称引用与敏感文件
- [pending] Phase 2: 选择项目名称并更新公开文档/展示资源
- [pending] Phase 3: 检查密钥与构建文件，初始化 Git 并提交
- [pending] Phase 4: 创建或确认 GitHub 仓库并推送
- [pending] Phase 5: 验证远程内容与项目可运行性

## Decisions
- 候选公开名称：`AgentLens`，突出“可观察 coding agent 内部机制”的项目特点。
- 保留 Python import/package、CLI 命令和配置键 `firstcoder`，避免无必要的兼容性破坏；仅替换 README/文档中的产品展示名称及对应链接/图片 alt 文本。

## Errors Encountered
| Error | Attempt | Resolution |
|---|---|---|
| 当前目录不是 Git 仓库 | `git -C ... status` | 项目需要初始化 Git |
| `gh` 未安装 | `gh auth status` | 需使用现有 Git 凭据/HTTPS 推送，或用户安装并认证 `gh` |
| 认证探测命令被自动权限策略拦截 | 读取环境变量、credential helper、SSH 目录 | 不再系统性探测；仅使用 Git 实际连接结果判断 |

## Notes
- `.env` 已被 `.gitignore` 忽略，公开前仍需检查是否有其他 token/key 残留。
- 不删除或修改内部 `firstcoder/` 子目录。
