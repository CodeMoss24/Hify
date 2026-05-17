#!/usr/bin/env python3
"""测试 chat 模块导入"""
import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    print("1. Importing app.common.response...")
    from app.common.response import ApiResponse, PageResult
    print("   OK")

    print("2. Importing app.chat.schemas...")
    from app.chat.schemas import ConversationCreate, ConversationResponse
    print("   OK")

    print("3. Importing app.chat.models...")
    from app.chat.models import ConversationModel, MessageModel
    print("   OK")

    print("4. Importing app.chat.interfaces...")
    from app.chat.interfaces import IChatService
    print("   OK")

    print("5. Importing app.chat.context_manager...")
    from app.chat.context_manager import ContextManager
    print("   OK")

    print("6. Importing app.chat.service...")
    from app.chat.service import ChatService
    print("   OK")

    print("\nAll imports successful!")

except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
