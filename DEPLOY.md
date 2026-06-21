# 部署到 Hugging Face Spaces（Docker SDK）

本项目可作为 **Docker Space** 部署到 Hugging Face，免费、长期在线、任意设备浏览器可用。

## 工作原理

- Space 是一个 Git 仓库，根目录含 `Dockerfile` 与带 front-matter 的 `README.md`。
- HF 读取 `README.md` 顶部的 `sdk: docker` 与 `app_port: 7860`，构建镜像并把流量路由到容器的 7860 端口。
- 本项目的 `Dockerfile` 以 `autodoc serve --port ${PORT}` 启动，`PORT` 默认 7860，正好匹配。

## 一、准备（在 Hugging Face 网站完成）

1. 注册 / 登录 <https://huggingface.co>。
2. 打开 <https://huggingface.co/settings/tokens>，创建一个 **Write** 权限的 Access Token。
3. （强烈建议）给 Space 设置访问保护：在 Space 的 *Settings → Variables and secrets* 添加
   - Secret `AUTODOC_TOKEN` = 你的访问口令（设置后，网页/接口都需要它才能调用）
   - 可选 Secret `ANTHROPIC_BASE_URL`、`ANTHROPIC_AUTH_TOKEN`、`AUTODOC_MODEL`（把模型 key 收口到服务端，前端就不必填）

## 二、方式 A：脚本一键部署（推荐）

```bash
pip install huggingface_hub
# Windows PowerShell:
$env:HF_TOKEN="hf_xxx"          # 你的 Write token
python scripts/deploy_hf.py --owner <你的HF用户名> --space autodoc-ai-answer
```

脚本会：创建（或复用）名为 `<owner>/autodoc-ai-answer` 的 Docker Space，并上传
`Dockerfile`、`README.md`、`pyproject.toml`、`autodoc/`。上传后 HF 会自动开始构建，
1–3 分钟后访问：`https://huggingface.co/spaces/<owner>/autodoc-ai-answer`。

## 三、方式 B：手动 git 推送

```bash
# 1. 在网站上 New Space -> SDK 选 Docker -> 创建空 Space
# 2. 克隆 Space 仓库
git clone https://huggingface.co/spaces/<owner>/autodoc-ai-answer hf-space
cd hf-space
# 3. 复制本项目文件进去（至少：Dockerfile、README.md、pyproject.toml、autodoc/）
# 4. 提交推送（推送时用 HF 用户名 + Write token 作为密码）
git add .
git commit -m "Deploy autodoc"
git push
```

## 四、部署后验证

- 打开 Space 页面，等待状态变为 **Running**。
- 若设置了 `AUTODOC_TOKEN`，网页会出现“访问令牌”输入框；填入后即可解析/答题。
- 自动答题：填入 OpenAI 兼容端点（如 DeepSeek `https://api.deepseek.com` + `deepseek-v4-flash`）
  与 API Key（或已在服务端用 Secret 配好）。

## 安全建议

- 公开 Space 务必设置 `AUTODOC_TOKEN`，否则任何人都能消耗你的模型额度。
- 优先用 Space Secret 配置模型 key（服务端），不要在公开演示里让访客填你的 key。
- 上传大小默认上限 25 MiB，可用 `AUTODOC_MAX_UPLOAD_BYTES` 调整。

## 其他平台

同一个 `Dockerfile` 也适用于 Render（Web Service, Docker）、Google Cloud Run、Fly.io 等——
它们通过 `$PORT` 注入端口，本项目已适配。
