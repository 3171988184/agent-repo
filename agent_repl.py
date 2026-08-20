# agent_repl.py —— 交互版 Agent：启动后自主输入指令，它执行，可多轮对话
# 在 agent_v1.py 基础上只改了 3 处，核心循环逻辑完全一样。

import json
import sys

sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台中文不乱码
# ===== 工具：网络搜索（用 duckduckgo，免费无需 key） =====
from duckduckgo_search import DDGS
from anthropic import Anthropic
# ===== 工具：抓取网页正文（清洗掉脚本/样式/导航） =====
import requests
from bs4 import BeautifulSoup
client = Anthropic(
    api_key="sk-d1b7432fc82f43c89dfad538b958ef49",
    base_url="https://api.deepseek.com/anthropic",
)


# 强化版系统提示词（这就是"规划"的开关）
SYSTEM_PROMPT = """你是"小助手"，一个能自己干活的研究助理。

工作方法（重要）：
1. 接到任务后，先在心里拆解步骤：需要查什么 → 用什么工具 → 每步产出什么
2. 把计划简要说出来（输出 1. 2. 3.），然后开始执行
3. 一步一步做：每步只调用一个（或少数）工具，观察结果再走下一步
4. 信息不足时主动补充搜索，不要猜
5. 全部步骤完成后，用最终回复总结结果（要完整、有条理）
6. 最终回复后不要再调用工具"""

TOOLS = [{
    "name": "calculator",
    "description": "执行数学计算，支持 + - * / 和括号，如 '2+3*4'",
    "input_schema": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"]
        }   
    },
    {
        "name": "web_search",
        "description": "在互联网上搜索信息，返回标题/链接/摘要",
        "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer"}
        },
        "required": ["query"]
        }
    },
    {
        "name": "web_fetch",
        "description": "抓取指定网页的正文内容",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"]
        }
    }
]


def web_fetch(url: str) -> str:
    """抓取网页正文文本（最多 4000 字）"""
    resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)[:4000]

def web_search(query: str, max_results: int = 5) -> str:
    """搜索并返回结果列表（标题/链接/摘要）"""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return "\n".join(
        f"[{r['title']}] {r['href']}\n{r['body'][:200]}"
        for r in results
    )

def calculator(expression: str) -> str:
    # 把 ^ 翻译成 Python 的 **（乘方）——说明书里写了支持 ^，实现必须一致
    expr = expression.replace("^", "**")
    return str(eval(expr, {"__builtins__": {}}, {}))

# ===== ④ 工具注册表：名字 → 函数（教程第 5 节）=====
# 循环里按 call.name 查表执行，加新工具只需：写函数 + 加 schema + 注册一行，循环零改动
TOOL_IMPLS = {
    "calculator": calculator,
    "web_search": web_search,
    "web_fetch": web_fetch,
}
# 加一个 "提交计划" 工具，强制模型先规划再执行（对复杂任务很有用）
TOOLS.append({
    "name": "submit_plan",
    "description": "开始执行前，提交你的完整执行计划（步骤列表）",
    "input_schema": {
        "type": "object",
        "properties": {
            "steps": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["steps"]
    }
})

def submit_plan(steps):
    print("📋 执行计划:")
    for i, s in enumerate(steps, 1):
        print(f"   {i}. {s}")
    return "计划已记录，请按计划开始执行。"

def chat_loop():
    # 改动 ①：对话历史提到最外层 —— 跨轮次保留，Agent 才记得你说过的话
    messages = []

    while True:
        # 改动 ②：指令从终端输入，不再写死在代码里
        task = input("\n👤 你> ").strip()
        # Windows 管道/重定向输入中文时可能出现 surrogate 乱码，清除掉（手动打字不受影响）
        task = task.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        if task in ("exit", "quit", "退出"):   # 改动 ③：退出指令
            print("👋 再见！")
            break
        if not task:
            continue

        messages.append({"role": "user", "content": task})

        # ===== 内部 Agent 循环（和 v1 完全一样）=====
        for step in range(20):
            resp = client.messages.create(
                model="deepseek-chat",
                system=SYSTEM_PROMPT,     # ← 这里
                max_tokens=1024,
                tools=TOOLS,
                messages=messages,
            )

            tool_calls = [b for b in resp.content if b.type == "tool_use"]

            if not tool_calls:
                final = "".join(b.text for b in resp.content if b.type == "text")
                print(f"💬 完成（{step+1} 步）: {final}")
                # 关键：模型回答也要存进历史，下一轮它才记得自己说过啥
                messages.append({"role": "assistant", "content": resp.content})
                break

            messages.append({"role": "assistant", "content": resp.content})

            results = []
            for call in tool_calls:
                print(f"🔧 第 {step+1} 步: 调用 {call.name}({call.input})")
                try:
                    impl = TOOL_IMPLS[call.name]           # 按名字查注册表
                    result = impl(**call.input)            # 动态调用对应函数
                except Exception as e:
                    result = f"工具报错: {e}"
                results.append({
                    "type": "tool_result",
                    "tool_use_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            messages.append({"role": "user", "content": results})
        else:
            print("⚠️ 超过最大步数，停止。")


if __name__ == "__main__":
    print("🛠️ 小助手已启动：输入指令让它干活，输入 exit 退出")
    chat_loop()
