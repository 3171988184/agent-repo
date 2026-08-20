# agent_repl.py —— 交互版 Agent：启动后自主输入指令，它执行，可多轮对话
# 在 agent_v1.py 基础上只改了 3 处，核心循环逻辑完全一样。

import json
import sys

sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台中文不乱码

from anthropic import Anthropic

client = Anthropic(
    api_key="sk-d1b7432fc82f43c89dfad538b958ef49",
    base_url="https://api.deepseek.com/anthropic",
)

TOOLS = [{
    "name": "calculator",
    "description": "执行数学计算，支持 + - * / 和括号，如 '2+3*4'",
    "input_schema": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"]
    }
}]

def calculator(expression: str) -> str:
    return str(eval(expression, {"__builtins__": {}}, {}))


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
                    result = calculator(**call.input)
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
