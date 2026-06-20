# autodoc · AI 文档答题 / AI Document Auto-Answer

> Read questions from a document, let any AI answer them, and write the answers
> back **into the original file in-place, preserving the original formatting**.
> Supports Word (DOCX), PDF, Excel (XLSX), PowerPoint (PPTX), TXT, Markdown.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](pyproject.toml)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](docker-compose.yml)

📄 项目主页 / Landing page: <https://ash19900601.github.io/autodoc-ai-answer/>

读取文档中的题目，调用任意 AI 模型生成答案，并**原地写回原文件、保持原始排版**。
支持 Word(DOCX)、PDF、Excel(XLSX)、PowerPoint(PPTX)、TXT、Markdown。



## 架构

```
浏览器（桌面 / 手机，响应式）
        │ HTTPS / REST
后端服务（Docker, Linux）
  ├─ autodoc serve  → FastAPI + 响应式网页
  ├─ autodoc CLI    → parse / edit / answer / formats
  └─ core: parse / edit / agent（python-docx, PyMuPDF, openpyxl, python-pptx）
```

## 开发与本地运行

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .\.venv\Scripts\activate
pip install -e ".[dev]"

autodoc --version
autodoc formats
autodoc serve                   # 打开 http://127.0.0.1:8000
```

## CLI 用法

```bash
# 解析题目
autodoc parse quiz.docx --json

# 用现成答案原地写回（确定性，无需模型）
echo '{"q1":"北京","q2":"H2O"}' > answers.json
autodoc edit quiz.docx --answers answers.json

# 让任意 AI 自动答题并原地写回（默认 auto：自动判定题型/版式）
autodoc answer quiz.docx \
  --base-url https://api.deepseek.com \
  --model deepseek-v4-flash \
  --api-key sk-xxx
# 可显式指定 --mode simple / worksheet；默认 auto 会自动选择
# 也可用环境变量 ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / AUTODOC_MODEL
```

`--output PATH` 可写到新文件；默认**原地编辑**原文件。

## Docker 部署（一键起，跨平台、不依赖 Windows）

```bash
docker compose up --build
# 浏览器访问 http://localhost:8000
```



```bash
pip install -e ".[mcp]"     # 需要 Python >= 3.10
autodoc-mcp                  # stdio 方式运行
```

注册示例见 `examples/mcp.json`。暴露三个工具：`parse_document`、`edit_document`、
`answer_document`。该模块不被 CLI/网页引用，启用与否都不影响主程序。

## 接入任意模型（示例：DeepSeek）

```bash
autodoc answer quiz.docx \
  --base-url https://api.deepseek.com \
  --model deepseek-v4-flash \
  --api-key sk-xxx
```

接口错误会以简洁信息提示（例如余额不足返回 `402 Insufficient Balance`）。

## 支持格式与边界

| 格式 | 解析 | 写回策略 | 格式保持 |
|------|------|----------|----------|
| DOCX | ✅ | 替换空白 / 段尾追加，复制 run 格式 | 样式/主题/页边距字节级保持 |
| XLSX | ✅ | 替换单元格空白 / 写入右侧单元格 | 字体/列宽保持 |
| PPTX | ✅ | 替换空白 / 段尾追加 | 版式/样式保持 |
| TXT/MD | ✅ | 替换空白 / 行尾追加 | 其余行字节不变 |
| PDF（表单） | ✅ | 填充 AcroForm 文本字段 | 页面/几何不变 |
| PDF（文本） | ✅ | 在题目旁插入答案（内置 CJK 字体） | 页数/几何/原文不变，仅新增内容 |

**不支持**：任意扫描件 / 复杂排版 PDF 的真正重排编辑（会如实报告而非破坏排版）。

## 答题模式（默认 auto，自动判定）

`autodoc answer` 有三种模式，默认 `auto`：

- **simple**：编号填空题（`1. ... ____` / 简答），直接定位空白或行尾追加。
- **worksheet**（仅 docx）：LLM 结构感知模式，处理真实考卷——字母编号小题 (a)(b)(c)、
  答案写进题后空白段落、True/False 打勾表格。
- **auto**：检查文档自动选择。有表格、或出现字母编号小题/分值标注 `[n]`、或 simple
  匹配不到题目时，走 worksheet；否则走 simple。结果中的 `mode` 字段标明实际采用的模式。

> 真实 Word 文档经原地编辑后：样式定义、节属性（页面尺寸/页边距）、编号语义均保留，
> 题目文字不变，仅把答案写入空白段落/答题单元格；包内 XML 会被 python-docx 重新序列化
> （非逐字节相同），并会清理 Word 残留的 `[trash]` 孤儿部件。视觉排版保持不变。

## 验收标准与如何复现

全部自动化，`pytest` 一条命令跑完：

```bash
python -m playwright install chromium   # 浏览器级测试用
pytest -q
```

覆盖的验收项：
- **CLI 基础**：`--version`、`--help` 列全部子命令、`formats` 输出。
- **解析**：各格式题目数量/题号/题型正确。
- **原地编辑**：答案写入正确；`in_place=True` 且输出路径==输入路径。
- **格式保持（严格）**：DOCX 解压后 `styles.xml`/`theme`/`settings`/节属性字节级一致，
  仅 `document.xml` 变化；PDF 页数与几何不变、原文保留。
- **任意 AI**：用 mock 的 OpenAI 兼容响应跑通 parse→答题→写回，无需真实付费 API。
- **CLI==GUI**：同一输入下，子进程 `autodoc edit` 与网页 `/api/edit` 产出文档文本完全一致；
  静态检查保证 `api.py`/`cli.py` 不含任何文档库导入。
- **GUI（浏览器级）**：Playwright 在桌面(1280×900)与移动(390×844)两种视口驱动真实网页，
  完成上传→解析→写入→下载，校验答案写入且标题等原内容保留。



## 许可证 / License

[MIT](LICENSE) © 2026 ASH19900601

本项目为独立实现，使用的第三方库（python-docx、PyMuPDF、openpyxl、python-pptx、
FastAPI 等）遵循各自的开源许可证。
