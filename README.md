# freebuff2api

Codebuff Freebuff 的 OpenAI-compatible API 适配服务。部署后可以像调用 OpenAI Chat Completions 一样调用 Freebuff 模型。

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/t479842598/freebuff2api-vercel&env=FREEBUFF_TOKEN,FREEBUFF_API_KEY&envDescription=FREEBUFF_TOKEN%20%E5%A1%AB%E5%86%99%20Freebuff%20token%EF%BC%8CFREEBUFF_API_KEY%20%E5%A1%AB%E5%86%99%E4%BD%A0%E8%87%AA%E5%B7%B1%E7%9A%84%E8%AE%BF%E9%97%AE%E5%AF%86%E9%92%A5&envLink=https://github.com/t479842598/freebuff2api-vercel#%E7%8E%AF%E5%A2%83%E5%8F%98%E9%87%8F&project-name=freebuff2api-vercel&repository-name=freebuff2api-vercel)

## 接口

- `GET /healthz`
- `GET /v1/models`
- `POST /v1/chat/completions`

## 快速开始

### 1. 获取 Freebuff Token

无需安装 Freebuff / Codebuff CLI，可以直接打开公开页面自动获取 token：

```text
https://freebuff.071129.xyz/
```

操作流程：

1. 打开上面的地址。
2. 选择 `Freebuff`。
3. 点击“开始认证”，在跳转页面完成授权。
4. 回到页面复制展示的 token。
5. 本地运行时写入 `.env`；部署 Vercel 时写入 Vercel 的 Environment Variables。

示例：

```dotenv
FREEBUFF_TOKEN=你的 Freebuff Bearer token
```

多账号可用英文逗号分隔。并发请求会优先分配到空闲账号，避免单个 Freebuff 账号的全局 active free session 被并发切模型请求互相覆盖：

```dotenv
FREEBUFF_TOKEN=token-a,token-b,token-c
```

### 2. 本地配置

新建 `.env` 文件并填写：

```dotenv
FREEBUFF_TOKEN=你的 Freebuff Bearer token
FREEBUFF_API_KEY=你的本地 API key
FREEBUFF_API_BASE_URL=https://www.codebuff.com
FREEBUFF_AD_PROVIDERS=gravity,zeroclick
FREEBUFF_TIMEOUT=60
FREEBUFF_PROXY_ENABLED=false
FREEBUFF_PROXY_URL=
FREEBUFF_DEBUG=false
FREEBUFF_LOG_LEVEL=INFO
FREEBUFF_LOG_BODY_CHARS=2000
FREEBUFF_LOG_COLOR=true
FREEBUFF_HOST=0.0.0.0
FREEBUFF_PORT=8000
FREEBUFF_TIMEZONE=Asia/Shanghai
FREEBUFF_LOCALE=zh-CN
FREEBUFF_OS=windows
FREEBUFF_BROWSER_UA=
```

`FREEBUFF_API_KEY` 是你自己给这个 API 服务设置的访问密钥。设置后，请求时需要带上：

```http
Authorization: Bearer 你的本地 API key
```

如果 `FREEBUFF_API_KEY` 留空，接口将不校验本地访问密钥。公开部署时不建议留空。

### 3. 本地运行

推荐使用 `uv`：

```powershell
uv sync
uv run freebuff2api
```

也可以使用 `pip`：

```powershell
python -m pip install -r requirements.txt
python main.py
```

启动后访问：

```text
http://127.0.0.1:8000/healthz
```

## 部署到 Vercel

### 一键部署

点击文档顶部的 `Deploy with Vercel` 按钮，按页面提示导入仓库并填写环境变量即可。

### 从 GitHub 导入部署

1. 将项目推送到 GitHub。
2. 打开 Vercel，选择 `Add New` -> `Project`。
3. 选择你的 GitHub 仓库并点击 `Import`。
4. 配置项目参数。
5. 添加环境变量。
6. 点击 `Deploy`。

Vercel 页面推荐填写：

| 配置项 | 推荐值 |
| --- | --- |
| Application Preset | `FastAPI` |
| Root Directory | `./` |
| Build Command | 留空 / `None` |
| Output Directory | 留空 / `N/A` |
| Install Command | `pip install -r requirements.txt` |

项目已经包含 Vercel 入口文件和路由配置：

- `api/index.py`：导出 FastAPI `app`。
- `vercel.json`：把所有请求转发到 `/api/index.py`。
- `requirements.txt`：给 Vercel 安装 Python 依赖。

### 环境变量

在 Vercel 项目页面进入 `Settings` -> `Environment Variables`，至少填写：

```dotenv
FREEBUFF_TOKEN=你的 Freebuff Bearer token
FREEBUFF_API_KEY=你自己设置的访问密钥
```

推荐同时填写：

```dotenv
FREEBUFF_API_BASE_URL=https://www.codebuff.com
FREEBUFF_AD_PROVIDERS=gravity,zeroclick
FREEBUFF_TIMEOUT=60
FREEBUFF_PROXY_ENABLED=false
FREEBUFF_DEBUG=false
FREEBUFF_LOG_LEVEL=INFO
FREEBUFF_LOG_BODY_CHARS=2000
FREEBUFF_LOG_COLOR=false
FREEBUFF_TIMEZONE=Asia/Shanghai
FREEBUFF_LOCALE=zh-CN
FREEBUFF_OS=windows
```

Vercel 上不要填写本机代理地址，例如：

```dotenv
FREEBUFF_PROXY_URL=socks5://127.0.0.1:7890
```

`127.0.0.1` 在 Vercel 云端代表 Vercel 自己的运行环境，不是你的电脑。

`FREEBUFF_HOST` 和 `FREEBUFF_PORT` 主要用于本地运行，Vercel 部署时不需要填写。

### 更新 Token 或环境变量

如果只是修改了 Vercel 后台的 `FREEBUFF_TOKEN`、`FREEBUFF_API_KEY` 等环境变量，需要在 Vercel 的 `Deployments` 页面点击 `Redeploy`，让新环境变量进入新的部署。

如果是修改代码并推送到 GitHub，Vercel 会自动重新部署绑定分支。通常推送到 `main` 分支会更新生产环境：

```powershell
git add .
git commit -m "Update project"
git push
```

## 调用示例

把下面的地址替换成你的本地地址或 Vercel 域名：

```text
http://127.0.0.1:8000
https://你的项目名.vercel.app
```

### 查看健康状态

```powershell
curl https://你的项目名.vercel.app/healthz `
  -H "Authorization: Bearer $env:FREEBUFF_API_KEY"
```

### 查看模型列表

```powershell
curl https://你的项目名.vercel.app/v1/models `
  -H "Authorization: Bearer $env:FREEBUFF_API_KEY"
```

### 非流式对话

```powershell
curl https://你的项目名.vercel.app/v1/chat/completions `
  -H "Authorization: Bearer $env:FREEBUFF_API_KEY" `
  -H "Content-Type: application/json" `
  -d '{
    "model": "deepseek/deepseek-v4-flash",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": false
  }'
```

### 流式对话

```powershell
curl -N https://你的项目名.vercel.app/v1/chat/completions `
  -H "Authorization: Bearer $env:FREEBUFF_API_KEY" `
  -H "Content-Type: application/json" `
  -d '{
    "model": "deepseek/deepseek-v4-flash",
    "messages": [{"role": "user", "content": "写一个 Python 快排"}],
    "stream": true
  }'
```

## 模型

当前内置 Freebuff 模型：

- `deepseek/deepseek-v4-flash`
- `deepseek/deepseek-v4-pro`
- `moonshotai/kimi-k2.6`
- `minimax/minimax-m2.7`

当前内置 Gemini free agent 组合：

- `google/gemini-2.5-flash-lite` -> `base2-free-deepseek-flash` 父 agent + `file-picker` 子 agent
- `google/gemini-3.1-flash-lite-preview` -> `base2-free-deepseek-flash` 父 agent + `file-picker-max` 子 agent
- `google/gemini-3.1-pro-preview` -> `base2-free-kimi` 父 agent + `thinker-with-files-gemini` 子 agent

调用 Gemini 时无需手动传 agent。项目会把 OpenAI 请求中的 `model` 解析为上游允许的 `agentId + model` 组合，并继续在 `codebuff_metadata.cost_mode=free` 下请求。Gemini free agents 会自动作为 active Freebuff session root 的子 agent 运行；未知模型不会自动兜底到 Gemini。

## 代理与调试

默认不启用代理，所有上游请求直连，且不会读取系统 `HTTP_PROXY` / `HTTPS_PROXY`。

本地需要让所有上游请求经过代理时，在 `.env` 中开启：

```dotenv
FREEBUFF_PROXY_ENABLED=true
FREEBUFF_PROXY_URL=http://127.0.0.1:7890
```

支持 HTTP 和 SOCKS 代理，例如：

```dotenv
FREEBUFF_PROXY_URL=http://127.0.0.1:7890
FREEBUFF_PROXY_URL=socks5://127.0.0.1:1080
FREEBUFF_PROXY_URL=socks5h://127.0.0.1:1080
```

调试空返回或上游异常时：

```dotenv
FREEBUFF_DEBUG=true
FREEBUFF_LOG_LEVEL=DEBUG
FREEBUFF_LOG_BODY_CHARS=0
```

## 注意事项

- 不要把 `.env` 提交到 GitHub。
- 公开部署时建议一定设置 `FREEBUFF_API_KEY`。
- Vercel 免费计划的 Serverless Function 有执行时长限制，长时间流式请求可能受到平台限制。
- 修改 Vercel 环境变量后需要手动 `Redeploy`；修改代码并推送到绑定分支后会自动部署。

## 感谢

> [FreeBuff](https://freebuff.com)
