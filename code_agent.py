# code_agent.py —— 可持续对话的代码助手（交互版）
# 在单次问答版基础上改造成 chat_loop：messages 提到外层 + while True + input()

import os, json, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台中文不乱码

from anthropic import Anthropic

PROJECT_ROOT = r"C:\Code\Android"        # ← 改成你的工程路径

# ===== 0. 客户端（API key 从环境变量读，别硬编码进代码） =====
# 换电脑/换 key 只需设置环境变量 DEEPSEEK_API_KEY，不用改代码
client = Anthropic(
    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),   # ← 从环境变量读，不留默认值
    base_url="https://api.deepseek.com/anthropic",
)
# ===== ① 工具实现 =====

def glob_files(pattern: str, root: str = PROJECT_ROOT) -> str:
    """按文件名模式找文件（如 '**/PlaybackPlugin.kt'）"""
    out = subprocess.run(
        ["git", "-C", root, "ls-files", pattern],   # 用 git ls-files 比 os.walk 快且忽略 .git
        capture_output=True, text=True, timeout=15,
    ).stdout
    return out[:4000] if out.strip() else "(无匹配文件)"

def grep_code(pattern: str, root: str = PROJECT_ROOT) -> str:
    """在代码里搜内容（如 'shouldFinish'），返回 文件:行号 列表"""
    out = subprocess.run(
        ["rg", "-n", "--max-count", "5", pattern, root, "-g", "*.kt", "-g", "*.java"],
        capture_output=True, text=True, timeout=20,
    ).stdout
    return out[:4000] if out.strip() else "(无匹配)"

def read_file(path: str, root: str = PROJECT_ROOT) -> str:
    """读取工程内文件（必须解析到工程内，防越界）"""
    full = os.path.abspath(os.path.join(root, path))
    if not full.startswith(os.path.abspath(root)):
        return f"错误: 路径越界 {path}"
    with open(full, encoding="utf-8", errors="replace") as f:
        return f.read()[:8000]

# 注册表
TOOL_IMPLS = {"glob_files": glob_files, "grep_code": grep_code, "read_file": read_file}

# ===== ② 工具 schema（给模型的说明书） =====
TOOLS = [
    {"name": "glob_files", "description": "按文件名模式查找项目文件，如 '**/*ViewModel.kt'",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "grep_code", "description": "在 Kotlin/Java 源码中按关键字搜索，返回 文件:行号",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "read_file", "description": "读取项目内文件的完整内容（路径相对工程根目录）",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
]

SYSTEM = """你是项目代码助手。工作方法：
1. 用 glob_files 找到可能相关的文件 → 用 grep_code 定位关键字 → 用 read_file 读具体文件
2. 不要凭记忆编造代码，一切以读到的为准
3. 回答时给出 文件:行号 引用，并简要说明逻辑"""

# ===== ③ 交互版循环 =====
def chat_loop():
    # 改动 ①：对话历史提到最外层 —— 跨轮次保留，它才记得之前聊过什么
    messages = []

    while True:
        # 改动 ②：从终端输入问题
        question = input("\n👤 你> ").strip()
        # Windows 管道输入中文的 surrogate 乱码防御（手动打字不受影响）
        question = question.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        if question in ("exit", "quit", "退出"):
            print("👋 再见！")
            break
        if not question:
            continue

        messages.append({"role": "user", "content": question})

        # ===== 内部 Agent 循环（和原来完全一样）=====
        for step in range(15):
            resp = client.messages.create(
                model="deepseek-chat",
                max_tokens=1024,
                system=SYSTEM, tools=TOOLS, messages=messages,
            )
            tool_calls = [b for b in resp.content if b.type == "tool_use"]
            if not tool_calls:
                answer = "".join(b.text for b in resp.content if b.type == "text")
                print(f"💬 完成（{step+1} 步）: {answer}")
                # 改动 ③：模型回答也存进历史，下一轮它才记得自己说过啥
                messages.append({"role": "assistant", "content": resp.content})
                break
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for call in tool_calls:
                print(f"🔧 {call.name}({call.input})")
                try:
                    result = TOOL_IMPLS[call.name](**call.input)
                except Exception as e:
                    result = f"工具报错: {e}"
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
            messages.append({"role": "user", "content": results})
        else:
            print("⚠️ 超过最大步数，停止。")

def ask_once(question: str):
    """单次问答（命令行参数版用）：问一个问题，答完即退出"""
    messages = [{"role": "user", "content": question}]
    for step in range(15):
        resp = client.messages.create(
            model="deepseek-chat",
            max_tokens=1024,
            system=SYSTEM, tools=TOOLS, messages=messages,
        )
        tool_calls = [b for b in resp.content if b.type == "tool_use"]
        if not tool_calls:
            answer = "".join(b.text for b in resp.content if b.type == "text")
            print(f"💬 完成（{step+1} 步）: {answer}")
            return
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for call in tool_calls:
            print(f"🔧 {call.name}({call.input})")
            try:
                result = TOOL_IMPLS[call.name](**call.input)
            except Exception as e:
                result = f"工具报错: {e}"
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
        messages.append({"role": "user", "content": results})
    print("⚠️ 超过最大步数，停止。")

if __name__ == "__main__":
    # 命令行入口：codeagent "问题" → 单次问答；codeagent → 交互模式
    if len(sys.argv) > 1:
        ask_once(" ".join(sys.argv[1:]))
    else:
        print("🛠️ 代码助手已启动：问它关于 C:\\Code\\Android 的问题，输入 exit 退出")
        chat_loop()
