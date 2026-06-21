"""Worksheet mode: LLM-driven, structure-aware in-place answering.

For real worksheets that do not follow the simple "1. ____" pattern
(lettered sub-parts (a)(b)(c), written-answer paragraphs, tick-box
True/False tables), we:

1. extract the document structure (paragraphs incl. blanks + tables),
2. ask the model to return a list of in-place edit operations,
3. apply them, writing only into blank answer paragraphs / answer cells,
   so the original layout and formatting are preserved.

Only DOCX is supported in worksheet mode for now.
"""
from __future__ import annotations

import json
import re
from typing import List

from .formats import detect_format
from .llm import LLMClient
from .models import DocFormat, EditResult

_SYSTEM = (
    "你是一个考卷自动作答引擎。给你一份文档的结构（段落 paragraphs 和表格 tables，"
    "都带索引），你要返回一组“原地编辑操作”的 JSON 数组来完成作答。\n"
    "可用操作：\n"
    '- {"op":"set_paragraph","index":N,"text":"..."}：把答案写入一个【空白段落】（text 为空的段落）。\n'
    '- {"op":"fill_blank","index":N,"occurrence":K,"text":"..."}：把第 N 段中第 K 个下划线空（____）替换为答案，保留该段其余文字；K 从 1 开始，默认 1。\n'
    '- {"op":"append_paragraph","index":N,"text":"..."}：在第 N 段末尾追加文字（用于在题干或所选选项行后做标注）。\n'
    '- {"op":"set_cell","table":T,"row":R,"col":C,"text":"..."}：写入表格单元格（打勾用 "✓"）。\n'
    '- {"op":"append_cell","table":T,"row":R,"col":C,"text":"..."}：在单元格已有内容后追加。\n'
    "各题型作答规范：\n"
    "1) 填空题：题干内有 ____，用 fill_blank 按 occurrence 填对应空；多个空分别填。\n"
    "2) 单选题：把所选选项字母（如 A/B/C/D）写进答题空（fill_blank 或空白段落 set_paragraph）；"
    "若无答题空，用 append_paragraph 在题干段或所选选项段末尾加 “✓(答案:X)”，不要覆盖选项文字。\n"
    "3) 多选题：同上，答案写成多个字母（如 ABD）。\n"
    "4) 判断题：表格形式用 set_cell 在 True/False(或对/错)列打 “✓”；行内形式用 fill_blank 写 “对/错” 或 “T/F”。\n"
    "5) 简答/解释/论述题：用 set_paragraph 把答案写进题目后最近的空白段落。\n"
    "6) 匹配/连线题：把匹配到的字母或序号用 fill_blank/set_cell/set_paragraph 写进对应答题位置。\n"
    "7) 排序题：把顺序（如 “3-1-2-4”）写进答题空白处。\n"
    "8) 计算题：把最终答案（必要时含简要步骤）写进空白段落。\n"
    "硬性规则：绝不修改或覆盖题目文字与选项文字；只往空白段落、下划线空、答题单元格写入；"
    "只输出 JSON 数组，不要任何解释或代码块标记。"
)


def _build_prompt(structure: dict) -> str:
    return (
        "文档结构如下（paragraphs 含空白段落，blank 段落即可作为答题位置）：\n\n"
        + json.dumps(structure, ensure_ascii=False, indent=1)
        + "\n\n请输出完成作答所需的操作 JSON 数组。"
    )


def extract_json_array(text: str) -> List[dict]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if not m:
            raise ValueError(f"无法从模型响应中解析操作数组：{text[:200]!r}")
        data = json.loads(m.group(0))
    if isinstance(data, dict) and "operations" in data:
        data = data["operations"]
    if not isinstance(data, list):
        raise ValueError("模型返回的操作不是数组")
    return data


def answer_worksheet(path: str, client: LLMClient, output: str = None) -> EditResult:
    fmt = detect_format(path)
    if fmt != DocFormat.docx:
        raise NotImplementedError("worksheet 模式目前仅支持 docx")
    from .backends import docx_backend

    structure = docx_backend.extract_structure(path)
    raw = client.complete(_SYSTEM, _build_prompt(structure))
    ops = extract_json_array(raw)
    return docx_backend.apply_ops(path, ops, output=output)
