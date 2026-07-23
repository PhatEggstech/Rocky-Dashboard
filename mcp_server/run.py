# -*- coding: utf-8 -*-
"""Entry point for Rocky Dashboard MCP Server."""
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "executive_dashboard", ".env.pg"))


def run_mcp():
    """Run as MCP server."""
    from .server import mcp
    import sys
    if "--sse" in sys.argv:
        print("Starting FastMCP in SSE mode on port 8000...")
        mcp.run("sse")
    else:
        mcp.run()


def run_chat():
    """Run interactive chat mode."""
    from .ai_chat import chat
    from .config import AI_PROVIDER, AI_MODEL, AI_BASE_URL, OPENROUTER_API_KEY

    if AI_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set!")
        print("  1. Go to https://openrouter.ai/keys")
        print("  2. Create a new key")
        print("  3. Set: $env:OPENROUTER_API_KEY = 'sk-or-...'")
        sys.exit(1)

    print("=" * 60)
    print("Rocky Dashboard AI Assistant")
    print(f"  Provider: {AI_PROVIDER} | Model: {AI_MODEL}")
    print(f"  Server: {AI_BASE_URL}")
    print("=" * 60)
    print("Hoi bat ky cau hoi nao ve doanh thu, don hang, cong no,")
    print("nhan vien, ton kho, khach hang...")
    print("Go 'quit' de thoat.")
    print("=" * 60)

    history = []
    while True:
        try:
            user_input = input("\n🔍 Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        try:
            response = chat(user_input, history)
            print(f"\n🤖 AI: {response}")

            # Keep history (last 10 messages)
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response})
            if len(history) > 20:
                history = history[-20:]
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    if "--mcp" in sys.argv:
        run_mcp()
    else:
        run_chat()
