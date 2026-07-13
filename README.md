# Captivity Simulator

一个本地优先、纯规则驱动的 30 天成人向囚禁角色扮演模拟器。规则引擎负责数值、行动、夜间、监控、逃跑、物品、事件回顾和结局；具体事件经过可以由外部 AI 适配器填写。

> **18+ 内容预警**：本项目面向成年人之间自愿进行的虚构 BDSM / 囚禁角色扮演。默认内容包含性、支配与臣服、羞耻、束缚、监控、惩戒和逃跑失败等成人主题。请根据所在地法律和个人边界自行使用与修改。

## 开源版边界

- 源码只使用 `{user}` 与 `{assistant}` 占位符，不包含开发者的私人角色名。
- 双路线分别是“被 `{assistant}` 囚禁”和“囚禁 `{assistant}`”。
- 本地存档默认写入 `data/saves/`，整个 `data/` 已加入 `.gitignore`。
- 私有配置写入 `config/local.json`，该文件不会进入 Git。
- 不包含任何私人聊天网关、R2、互动时间、记忆层或特定消息平台接入。
- AI 适配器默认关闭；不开启 AI 也可以使用规则引擎、命令接口和手动提示词。

## 功能

- 两种玩家身份与独立交互流程
- 每天一次安排三个白天行动
- 健康、体力、清洁、羞耻、依赖和自选心情
- 调教内容、道具、喂食、附加性行为和过程事件
- 宠物线以深度物化、口头服从、性服务与违令后的性惩戒为核心；建立宠物身份后，这些规则会持续进入后续事件素材
- 夜间自由行动、渐进物品痕迹、每次播放预录台词的语音铃、监控与延迟处理
- 逃跑诱导、抓回、新规矩与后续处理
- 自动事件存档、按日回顾和 30 天固定结局
- OpenAI-compatible AI 接口与可替换提示词
- 完整 Web UI 与可选 MCP stdio 连接

## 快速开始

要求：Python 3.11+、Node.js 20.19+。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

cp config/example.local.json config/local.json
cd web
npm install
npm run build
cd ..

captivity-simulator
```

打开 <http://127.0.0.1:5058>。

开发前端时分别运行：

```bash
captivity-simulator
cd web && npm run dev
```

开发地址为 <http://127.0.0.1:5176>，Vite 会把 `/api` 代理到本地 Python 服务。

## 返回、继续与重开

- 左上角箭头用于退出囚禁模拟器，不会删除当前存档。
- 右上角 `IDENTITY: ...` 用于返回身份选择页，本身不会立刻删除存档。
- 从身份选择页再次选择任一身份会执行 `new_game`，开始新游戏并覆盖当前进度。
- 如果返回身份选择页后直接退出，下次进入时，有效的既有进度仍会自动读取并继续。

## 仓库结构

```text
src/captivity_simulator/  规则引擎、HTTP 服务、AI 与 MCP 适配
web/                      完整 React UI、字体与页面素材
config/                   可提交的默认配置与本地配置示例
tests/                    规则、HTTP 与 MCP 测试
data/                     被 Git 忽略的本地存档目录
```

`web/src/CaptivitySimulator.tsx` 是完整的双路线游戏界面，不是规则引擎的简化演示页。

## 配置角色名

复制示例配置：

```bash
cp config/example.local.json config/local.json
```

然后修改：

```json
{
  "actors": {
    "user": "你的名字",
    "assistant": "AI 角色名"
  }
}
```

Python 接口会在响应时替换占位符；前端在构建时读取同一份配置，所以修改名字后需要重新运行 `npm run build`。

## 接入 AI

默认适配 OpenAI-compatible `/chat/completions`：

```json
{
  "ai": {
    "enabled": true,
    "base_url": "https://example.com/v1",
    "api_key_env": "CAPTIVITY_AI_API_KEY",
    "model": "your-model-name"
  }
}
```

密钥只放环境变量：

```bash
export CAPTIVITY_AI_API_KEY="..."
```

需要接入其他 AI、聊天机器人或本地模型时，替换 `src/captivity_simulator/adapter.py` 的 `request_assistant()` 即可。适配器接收已经包含游戏状态、当前事件和 menu 协议的完整提示词，返回以 `【...】` 指令开头的文本。

## 二改提示词

提示词不写死在规则引擎。可在 `config/local.json` 覆盖：

```json
{
  "prompt": {
    "route_openings": {
      "captured_by_assistant": "被 {assistant} 囚禁路线的开场设定",
      "capture_assistant": "囚禁 {assistant} 路线的开场设定"
    },
    "process_style": "详细经过的写作要求",
    "extra_rules": [
      "其他希望每次注入的规则"
    ]
  }
}
```

状态数值与事件判定仍由规则引擎处理；提示词只负责给外部 AI 提供叙事素材与结构化指令格式。

## HTTP 接口

### 执行规则命令

```http
POST /api/game/command
Content-Type: application/json

{"save_id":"default","command":"status"}
```

### 让 AI 处理当前 pending

```http
POST /api/game/sync-assistant
Content-Type: application/json

{"save_id":"default","message":"可选的局内台词"}
```

AI 未配置时接口返回 `409`，不会访问任何网络模型。HTTP 响应只返回当前玩家可见的状态，不返回助手提示词、另一方私有视图或原始引擎命令。

## MCP stdio 连接

MCP 和 Web UI 共用同一套规则引擎与 `data/saves/` 本地存档，不会生成第二份游戏状态，也不需要安装额外的 MCP Python 包。

安装项目后可直接启动：

```bash
captivity-simulator-mcp
```

MCP 客户端配置示例：

```json
{
  "mcpServers": {
    "captivity-simulator": {
      "command": "/absolute/path/to/captivity-simulator/.venv/bin/captivity-simulator-mcp",
      "cwd": "/absolute/path/to/captivity-simulator",
      "env": {
        "CAPTIVITY_CONFIG": "/absolute/path/to/captivity-simulator/config/local.json",
        "CAPTIVITY_DATA_DIR": "/absolute/path/to/captivity-simulator/data"
      }
    }
  }
}
```

MCP server 暴露：

- 工具 `captivity_simulator`：参数为 `command` 和可选 `save_id`。
- 资源 `captivity-simulator://save/default`：读取默认存档当前状态。
- 工具结果的 `content` 是可读文本，`structuredContent` 只包含当前助手身份可见的结构、pending 与可执行命令；不会返回玩家一侧的私有视图。

调用示例：

```json
{
  "name": "captivity_simulator",
  "arguments": {
    "command": "status",
    "save_id": "default"
  }
}
```

建议 MCP 宿主先调用 `status`，再根据返回的 `pending_event` 和命令提示提交一次对应命令。stdio 模式下 stdout 只写 MCP JSON-RPC 消息，日志应写 stderr。

## 测试与开源审计

```bash
make test
make audit
cd web && npm run build
```

`make audit` 会扫描源码和文档，阻止私人角色名、旧身份 ID、私有同步路由与 R2 依赖进入仓库。

## License

代码与项目视觉素材使用 [MIT](LICENSE)。`web/src/assets/cookie-regular.ttf` 为 Cookie 字体，使用 [SIL Open Font License 1.1](web/src/assets/OFL.txt)。详情见 [ASSETS.md](ASSETS.md)。
