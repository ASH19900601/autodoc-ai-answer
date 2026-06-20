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
    "你是一个考卷自动作答引擎。给你一份文档的结构（段落和表格），"
    "你要返回一组“原地编辑操作”的 JSON 数组来完成作答。规则："
    "1) 只把答案写进空白段落（text 为空）或表格的答题单元格，绝不修改题目文字；"
    "2) 简答/解释题：找到题目后面最近的空白段落，用 set_paragraph 写入简洁正确的答案；"
    "3) True/False 打勾表格：在正确的那一列单元格用 set_cell 写入字符 \"✓\"；"
    "4) 表格首行通常是表头（如 True / False），数据行从第 1 行开始；"
    "5) 只输出 JSON 数组，不要任何解释或代码块标记。"
    "操作格式："
    '{"op":"set_paragraph","index":N,"text":"..."} 或 '
    '{"op":"set_cell","table":T,"row":R,"col":C,"text":"✓"}。'
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
