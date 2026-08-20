# chat.py —— 同时兼容 OpenAI 协议（DeepSeek 等）和 Anthropic 协议（Claude）
#
# 用法：
#   python chat.py              → OpenAI 协议（默认，走 api.deepseek.com）
#   python chat.py anthropic    → Anthropic 协议（走 DeepSeek 的 /anthropic 端点）
import sys

sys.stdout.reconfigure(encoding="utf-8")

USE_ANTHROPIC = len(sys.argv) > 1 and sys.argv[1] == "anthropic"

if USE_ANTHROPIC:
    from anthropic import Anthropic

    client = Anthropic(
        api_key="sk-d1b7432fc82f43c89dfad538b958ef49",   # 你的 DeepSeek key
        # DeepSeek 的 Anthropic 兼容端点；若用官方 Claude，删掉这行即可
        base_url="https://api.deepseek.com/anthropic",
    )

    resp = client.messages.create(
        model="deepseek-chat",        # 官方 Claude 可换 claude-sonnet-4-6 等
        max_tokens=1024,
        system="你是一个研究小助手，回答要简洁、有条理。",
        messages=[{"role": "user", "content": "什么是 Agent？用一句话说"}],
    )
    print(resp.content[0].text)
else:
    from openai import OpenAI

    client = OpenAI(
        api_key="sk-d1b7432fc82f43c89dfad538b958ef49",   # 你的 DeepSeek key
        base_url="https://api.deepseek.com",
    )

    resp = client.chat.completions.create(
        model="deepseek-chat",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": "你是一个研究小助手，回答要简洁、有条理。"},
            {"role": "user", "content": "什么是 Agent？用一句话说"},
        ],
    )
    print(resp.choices[0].message.content)
