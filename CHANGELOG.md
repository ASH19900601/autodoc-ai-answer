# Changelog

本项目遵循语义化版本。以下为各版本的变更说明。

## 0.2.1 - 2026-06-21

### 变更
- 在线 Demo（Hugging Face Space）内置测试模型（DeepSeek）：网页端直接点“自动答题”即可使用，
  Base URL / Model / API Key 三项改为可选，留空走内置测试模型，填写则使用用户自己的 OpenAI 兼容接口。
- 取消在线 Demo 的访问令牌要求，便于直接体验。
- 网页文案说明“留空=内置测试模型，填写=用自己的 API”。

## 0.2.0 - 2026-06-21

### 新增
- worksheet 模式新增编辑操作：`fill_blank`（按序号替换段落内第 N 个下划线空，保留其余文字）、
  `append_cell`（在表格单元格已有内容后追加），覆盖更多答题位置。
- 全题型支持：填空（含多空/完形）、单选、多选、判断（行内与 True/False 打勾表格）、
  简答、论述、匹配（表格）、排序、计算。worksheet 提示词按题型给出明确作答规范。
- 自动判定（auto）新增对选择题选项行（A. B. C. …）的识别，含选项的文档自动走 worksheet 模式。
- 新增示例：`examples/make_sample_quiz.py` 与 `examples/sample-all-types.docx`，覆盖全部题型。

### 改进
- 同一段落多个 `fill_blank` 按 occurrence 从大到小应用，避免先填的空导致后续序号错位。

## 0.1.0 - 2026-06-21

### 新增
- 首个版本：读取文档题目、调用任意 OpenAI 兼容模型作答、原地写回并保持原排版。
- 支持格式：DOCX、PDF（表单填充 + 文本插入）、XLSX、PPTX、TXT、Markdown。
- 两种答题策略：`simple`（编号填空/简答）与 `worksheet`（LLM 结构感知，docx）；`auto` 自动选择。
- CLI（事实来源）、FastAPI + 响应式网页（CLI=GUI 等价）、可选 MCP 服务。
- 云化与加固：`PORT` 适配、访问令牌鉴权、上传大小限制、临时文件清理；Docker 与 Hugging Face Spaces 部署。
