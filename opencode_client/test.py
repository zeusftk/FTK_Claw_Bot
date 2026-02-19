"""
OpenAI-Compatible API 测试样例
使用 OpenAI SDK 调用本地 API 服务
"""

from tokenize import Pointfloat
from openai import OpenAI

PORT = 12312
def test_chat_completion():
    client = OpenAI(
        api_key="",
        base_url=f"http://127.0.0.1:{PORT}/v1"
    )

    response = client.chat.completions.create(
        model="glm-5-free",
        messages=[
            {"role": "system", "content": "你是一个有帮助的助手。"},
            {"role": "user", "content": "你好，请介绍一下你自己。"}
        ],
        temperature=0.7,
        max_tokens=500
    )

    print("=" * 50)
    print("非流式响应测试")
    print("=" * 50)
    print(f"模型: {response.model}")
    print(f"回复: {response.choices[0].message.content}")
    print(f"Token 使用: {response.usage}")
    print()


def test_stream_chat():
    client = OpenAI(
        api_key="",
        base_url=f"http://127.0.0.1:{PORT}/v1"
    )

    print("=" * 50)
    print("流式响应测试")
    print("=" * 50)

    stream = client.chat.completions.create(
        model="kimi-k2.5-free",
        messages=[
            {"role": "user", "content": "用一句话介绍 Python 语言。"}
        ],
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n")


def test_list_models():
    client = OpenAI(
        api_key="",
        base_url=f"http://127.0.0.1:{PORT}/v1"
    )

    print("=" * 50)
    print("模型列表测试")
    print("=" * 50)

    models = client.models.list()
    for model in models.data:
        print(f"- {model.id} (owned by: {model.owned_by})")
    print()


def test_conversation():
    client = OpenAI(
        api_key="",
        base_url=f"http://127.0.0.1:{PORT}/v1"
    )

    print("=" * 50)
    print("多轮对话测试")
    print("=" * 50)

    messages = [
        {"role": "system", "content": "你是一个简洁的助手，回答尽量简短。"},
        {"role": "user", "content": "1+1等于几？"},
    ]

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=messages
    )

    assistant_reply = response.choices[0].message.content
    print(f"用户: 1+1等于几？")
    print(f"助手: {assistant_reply}")

    messages.append({"role": "assistant", "content": assistant_reply})
    messages.append({"role": "user", "content": "那2+2呢？"})

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=messages
    )

    print(f"用户: 那2+2呢？")
    print(f"助手: {response.choices[0].message.content}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("OpenAI-Compatible API 测试")
    print("确保 router.py 服务已启动: python router.py")
    print("=" * 50 + "\n")

    try:
        test_list_models()
        test_chat_completion()
        test_stream_chat()
        test_conversation()
        print("所有测试完成!")
    except Exception as e:
        print(f"测试失败: {e}")
        print("请确保服务已启动: python router.py")
