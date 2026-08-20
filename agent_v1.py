# agent_v1.py —— 会调用计算器工具的 Agent（ReAct 循环）
# 对应教程第 4 节：v1 · ReAct 循环 + 计算器工具（项目的心脏）
#
# 一句话原理：LLM 不会真的执行工具，它只"声明"要调哪个工具、传什么参数；
# 真正执行的是下面的 calculator()，执行结果再回填给 LLM，让它继续决策。
# 这就是"大脑声明 + 手脚执行 + 循环回填"的 Agent 骨架。

import json
import sys

sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台中文不乱码

from anthropic import Anthropic

# ===== 0. 客户端 =====
# 用 DeepSeek 的 Anthropic 兼容端点（国内可直连）；
# 若用官方 Claude，删掉 base_url 并把模型名换成 claude-sonnet-4-6 即可。
client = Anthropic(
    api_key="sk-d1b7432fc82f43c89dfad538b958ef49",
    base_url="https://api.deepseek.com/anthropic",
)

# ===== ① 工具定义：给模型的"说明书" =====
# 模型靠 description 理解工具用途，靠 input_schema 知道怎么传参。
# 注意：这只是给 LLM 看的 JSON，不执行任何代码。
TOOLS = [{
    "name": "calculator",
    "description": "执行数学计算，支持 + - * / ^ 和括号，如 '2+3*4'",
    "input_schema": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"]
    }
}]

# ===== ② 工具实现：真正干活的代码（名字和 schema 对应） =====
def calculator(expression: str) -> str:
    # 把 ^ 翻译成 Python 的 **（乘方）——说明书里写了支持 ^，实现必须一致
    expr = expression.replace("^", "**")
    # 演示用 eval；生产请用 ast 安全解析（教程第 8 节 8.4）
    return str(eval(expr, {"__builtins__": {}}, {}))

# ===== ③ Agent 循环（本文件的核心） =====
# 流程：问 LLM（带工具清单）→ LLM 返回 tool_use 声明 → 你执行工具 →
#       结果回填 messages → 再问 LLM…直到 LLM 不再要求调用工具（= 任务完成）
def run(task: str):
    # messages 是对话历史：循环就是不断往这个数组里追加内容
    messages = [{"role": "user", "content": task}]

    # 最大 20 步：防失控的终止条件（模型可能陷入死循环，必须兜底）
    for step in range(20):
        # 每次调用都把完整历史 + 工具清单发给模型
        resp = client.messages.create(
            model="deepseek-chat",
            max_tokens=1024,
            tools=TOOLS,          # 把工具清单传给模型，它才知道"我能用啥"
            messages=messages,
        )

        # 从响应里挑出 tool_use 块（模型"声明"要调用的工具）
        tool_calls = [b for b in resp.content if b.type == "tool_use"]

        # 没有 tool_use = 任务完成，把纯文本部分拼出来输出
        if not tool_calls:
            final = "".join(b.text for b in resp.content if b.type == "text")
            print(f"\n💬 完成（{step+1} 步）: {final}")
            return

        # 记录"模型决定调工具"——整段 resp.content 必须原样存（text + tool_use 一起），
        # 模型要看到"自己刚才说要调工具"，上下文才连贯
        messages.append({"role": "assistant", "content": resp.content})

        # 执行所有声明的工具（一次可能有多个 tool_use → 全部执行）
        results = []
        for call in tool_calls:
            print(f"🔧 第 {step+1} 步: 调用 {call.name}({call.input})")
            try:
                result = calculator(**call.input)
            except Exception as e:
                result = f"工具报错: {e}"   # 错误也回填——模型会自己调整思路

            results.append({
                "type": "tool_result",
                "tool_use_id": call.id,      # 必须回传对应 id，模型才能对上号
                "content": json.dumps(result, ensure_ascii=False),
            })

        # 结果喂回（全部放同一条 user 消息），进入下一轮循环
        messages.append({"role": "user", "content": results})

    print("⚠️ 超过最大步数，停止。")

if __name__ == "__main__":
    run("帮我算一下 17 的 5 次方减去 233，然后再乘以 0.618")
