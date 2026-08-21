# 🤖 agent-repo — 手写 Agent 小助手学习仓库

> 从零手写一个会查资料、会调工具、会自己规划步骤的 AI 小助手。
> 全程使用官方 SDK，**不依赖任何 Agent 框架**（LangChain / LangGraph 等）。
> 理解 Claude Code 这类工具的核心原理：**工具注册表 + 循环调度 + 错误回填**。

---

## 📦 这是什么

这是一个 **Agent 学习项目**，包含从简单到复杂的 4 个 Python 脚本：

| 文件 | 版本 | 能力 |
|---|---|---|
| `chat.py` | v0 · 基础聊天 | 验证 SDK 通了：问一句，答一句 |
| `agent_v1.py` | v1 · ReAct 循环 | **核心**：循环 + 计算器工具（`17^5 - 233` × 0.618） |
| `agent_repl.py` | v2+ · 交互版 | 持续对话 + 搜索 / 抓网页 / 规划（`web_search` / `web_fetch` / `submit_plan`） |
| `code_agent.py` | v3+ · 代码助手 | 针对 Android 工程的问答：搜文件 / 搜代码 / 读文件，给出 `文件:行号` 引用 |

**核心原理（面试可用）：**
- 🔄 **ReAct 循环**：问 LLM → LLM 返回 tool_use 声明 → 执行工具 → 结果回填 → 再问…直到完成
- 🧰 **工具注册表**：`TOOL_IMPLS = {名字: 函数}`，加新工具只需注册一行，循环零改动
- 🛡 **错误回填**：工具报错也回填给模型，让它自己调整思路（Agent 的"自我修复"）
- ✂️ **上下文裁剪**：工具结果截断（4000/8000 字），防止撑爆上下文

---

## 🚀 怎么跑（Windows）

### 0. 环境要求

- **Python 3.11+**（python.org 下载，安装时勾选 *Add Python to PATH*）
- **Git**（可选，用于拉取代码）

### 1. 克隆仓库

```bash
git clone https://github.com/3171988184/agent-repo.git
cd agent-repo
```

### 2. 建虚拟环境 + 装依赖

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows 激活（Linux/Mac: source .venv/bin/activate）
pip install anthropic duckduckgo-search requests beautifulsoup4
```

### 3. 配置环境变量（API Key）

所有脚本从环境变量 `DEEPSEEK_API_KEY` 读取 key（**代码里没有硬编码**）。

**Windows（PowerShell，单行粘贴）：**

```powershell
[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY','你的key','User')
```

**Linux/Mac（bash）：**

```bash
echo 'export DEEPSEEK_API_KEY="你的key"' >> ~/.bashrc && source ~/.bashrc
```

> ⚠️ **重要**：设置环境变量后**必须新开终端**才生效。
> 验证：`echo $env:DEEPSEEK_API_KEY`（PowerShell）或 `echo $DEEPSEEK_API_KEY`（bash），能输出 key 即成功。

### 4. 运行

```bash
# 基础聊天（验证 SDK）
python chat.py

# ReAct 循环 + 计算器（教程 v1）
python agent_v1.py

# 交互版小助手（可多轮对话）
python agent_repl.py

# 代码助手（问 Android 工程代码问题）
python code_agent.py
```

`code_agent.py` 还支持命令行直接提问：

```bash
python code_agent.py "PlaybackPlugin 是什么？"
```

---

## 🖥 进阶：命令行入口 `codeagent`

想在任意终端敲 `codeagent` 直接调起代码助手（像 `claude` 一样）：

1. 新建 `C:\Users\<你的用户名>\bin\codeagent.bat`：

```bat
@echo off
set "PY=C:\path\to\agent-repo\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "C:\path\to\agent-repo\code_agent.py" %*
```

2. 把 `bin` 目录加入用户 PATH：

```powershell
[Environment]::SetEnvironmentVariable('Path',[Environment]::GetEnvironmentVariable('Path','User')+';C:\Users\<你的用户名>\bin','User')
```

3. 新开终端，使用：

```powershell
codeagent                      # 交互模式
codeagent "PlaybackPlugin 是什么？"   # 单次问答
```

---

## 🗄 换电脑 5 分钟恢复指南

| 步骤 | 命令 |
|---|---|
| ① 装 Python 3.11+ 和 Git | 官网下载安装 |
| ② 克隆 | `git clone https://github.com/3171988184/agent-repo.git && cd agent-repo` |
| ③ 虚拟环境 | `python -m venv .venv && .venv\Scripts\activate` |
| ④ 装依赖 | `pip install anthropic duckduckgo-search requests beautifulsoup4` |
| ⑤ 配环境变量 | `[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY','你的key','User')` |
| ⑥ 新开终端运行 | `python code_agent.py` |

> 💡 如果代码里 `PROJECT_ROOT`（`code_agent.py` 顶部）指向的工程路径变了，改那一行即可。
> 之后日常：改代码 → `git add . && git commit -m "说明" && git push`；换设备 → `git pull`。

---

## 🔑 API Key 安全须知

- ⚠️ **不要把 key 写进代码提交到 GitHub**（会被爬虫扫描盗刷）
- 统一走环境变量 `DEEPSEEK_API_KEY`（已适配所有脚本）
- 如果不慎泄露：立即去 DeepSeek 开放平台**删除/重置该 key**，重新生成

---

## 📚 学习资料

- 教程 HTML（本仓库内）：`第四步-交互版Agent怎么做.html`
- 官方文档：[Anthropic Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)（Agent 设计圣经）
- 模型：DeepSeek（`https://api.deepseek.com/anthropic`，Anthropic 兼容端点）

---

## 🎯 一句话总结（面试用）

> "我用官方 SDK 手写了一个 ReAct Agent：工具注册表 + 循环调度 + 错误回填 + 上下文裁剪，
> 不依赖任何 Agent 框架，约 300 行。它能自己搜索资料、抓网页、拆解任务、把报告写进文件——
> 我理解了 Claude Code 这类工具的核心原理。"
