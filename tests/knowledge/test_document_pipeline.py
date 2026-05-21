"""测试 DocumentPipeline — 文档分块和 Token 估算

覆盖：_estimate_tokens / _split_chunks / _split_paragraph / _split_by_chars
"""
import pytest
from app.knowledge.pipeline import DocumentPipeline


class TestEstimateTokens:
    """测试 _estimate_tokens() — Token 数量估算

    这是一个纯函数，公式是：
      int(中文字符 × 1.5 + 英文单词 × 1.0 + 其他字符 × 0.5) + 1

    写这类测试的关键技巧：
    1. 自己在纸/脑里算好期望值，硬编码进测试
    2. 每种「输入特征」选一个代表性用例
    3. 如果公式有隐含的 double-counting 问题，测试能把它暴露出来
    """

    # ── 场景 1：纯中文 ──────────────────────────────────
    # 4 个中文字符，没有英文单词，没有其他字符
    # 期望：4 × 1.5 = 6.0 → int=6，+1 = 7

    async def test_should_estimate_chinese_text_by_char_count(self):
        """
        Given: 纯中文文本 "你好世界"
        When:  调用 _estimate_tokens
        Then:  返回 7（4个中文 × 1.5 + 1）
        """
        pipeline = DocumentPipeline()

        result = pipeline._estimate_tokens("你好世界")

        assert result == 7
        # 验证一下计算过程，确认我们的理解是对的：
        # 中文字符 4 个 → 4 × 1.5 = 6
        # 英文单词 0 个 → 0 × 1.0 = 0
        # 其他字符 0 个 → 0 × 0.5 = 0
        # int(6 + 0 + 0) + 1 = 7 ✓

    # ── 场景 2：纯英文 ──────────────────────────────────
    # 10 个英文字母 + 1 个空格 = 11 个字符，都不是中文
    # 英文单词 = 2 个（"hello" 和 "world"）
    # other_chars = 11 - 0 = 11（包含空格和所有英文字母）
    # 注意：英文字母被双重计入！一次作为单词（×1.0），一次作为 other_chars（×0.5）
    # 期望：2 × 1.0 + 11 × 0.5 = 7.5 → int=7，+1 = 8

    async def test_should_estimate_english_text_by_word_and_char_count(self):
        """
        Given: 纯英文文本 "hello world"
        When:  调用 _estimate_tokens
        Then:  返回 8（2个单词 + 11个other_chars × 0.5 + 1）
        """
        pipeline = DocumentPipeline()

        result = pipeline._estimate_tokens("hello world")

        assert result == 8
        # 计算过程：
        # 中文字符 0 个 → 0 × 1.5 = 0
        # 英文单词 2 个 → 2 × 1.0 = 2
        # other_chars = 11（所有 11 个字符都不是中文）
        # → 11 × 0.5 = 5.5
        # int(0 + 2 + 5.5) + 1 = int(7.5) + 1 = 7 + 1 = 8

    # ── 场景 3：空字符串 ────────────────────────────────
    # 边界条件。空字符串在方法开头就有 early return 0。
    # 如果没有这个判断，后面的正则和计算可能出错。

    async def test_should_return_zero_when_text_is_empty(self):
        """
        Given: 空字符串
        When:  调用 _estimate_tokens
        Then:  返回 0（early return，不走到后面的计算公式）
        """
        pipeline = DocumentPipeline()

        result = pipeline._estimate_tokens("")

        assert result == 0


class TestSplitChunks:
    """测试 _split_chunks() — 文本分块主流程"""

    def test_should_merge_short_paragraphs_into_one_chunk(self):
        pipeline = DocumentPipeline()
        text = "第一段内容。\n\n第二段内容。"
        chunks = pipeline._split_chunks(text)
        assert len(chunks) == 1
        assert "第一段" in chunks[0]["content"]
        assert "第二段" in chunks[0]["content"]

    def test_should_return_empty_list_when_text_is_empty(self):
        pipeline = DocumentPipeline()
        chunks = pipeline._split_chunks("")
        assert chunks == []


class TestSplitParagraph:
    """测试 _split_paragraph() — 按句子边界分割超长段落"""

    def test_should_split_by_sentence_punctuation(self):
        pipeline = DocumentPipeline()
        # "这是一个测试句子。" ≈ 13.5 tokens，50 句 ≈ 675 tokens > CHUNK_SIZE(512)
        long_text = "这是一个测试句子。" * 50
        chunks = pipeline._split_paragraph(long_text)
        assert len(chunks) >= 1
        assert all(len(c) > 0 for c in chunks)


class TestSplitByChars:
    """测试 _split_by_chars() — 字符级截断兜底"""

    def test_should_produce_at_least_one_chunk(self):
        pipeline = DocumentPipeline()
        chunks = pipeline._split_by_chars("测")
        assert len(chunks) == 1
        assert len(chunks[0]) > 0