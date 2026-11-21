# Official SDK excerpts (read-only)
Retrieved: 2026-11-17
These are selected documentation excerpts, not account verification or adopted code.

Source: https://github.com/huaweicloud/agentarts-sdk-python/blob/main/docs/cn/sdk_user_guide/environment_variables.md

### 区域配置

SDK 支持多种区域配置方式，按以下优先级顺序读取：

| 优先级 | 环境变量 | 说明 |
|--------|----------|------|
| 1 | `HUAWEICLOUD_SDK_REGION` | 华为云 SDK 标准区域变量（推荐） |
| 2 | `HUAWEICLOUD_REGION` | 华为云区域变量 |
| 3 | `OS_REGION_NAME` | OpenStack 兼容区域变量 |

**默认区域：** 如果未配置任何区域变量，SDK 默认使用 `cn-southwest-2`。

**配置示例：**

```bash
export HUAWEICLOUD_SDK_REGION="cn-north-4"
```



Source: https://github.com/huaweicloud/agentarts-sdk-python/blob/main/docs/cn/toolkit_user_guide/deploy.md

# deploy/launch 命令使用文档

## 命令用途

`deploy` 和 `launch` 命令用于将 Agent 部署到华为云 AgentArts 平台。该命令会构建 Docker 镜像、上传到 SWR（容器镜像服务），并创建或更新 Agent 实例。

> **注意**: `launch` 是 `deploy` 命令的别名，两者功能完全相同。

## 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称 | 使用默认 Agent |
| `--mode` | `-m` | 部署模式（local/cloud） | `cloud` |
| `--tag` | `-t` | Docker 镜像标签 | `latest` |
| `--local-port` | `-l` | 本地端口映射（本地模式） | 从配置文件读取 |
| `--swr-org` | 无 | SWR 组织（覆盖配置） | 从配置文件读取 |
| `--swr-repo` | 无 | SWR 仓库（覆盖配置） | 从配置文件读取 |
| `--description` | `-d` | Agent 描述（覆盖配置） | 从配置文件读取 |
| `--skip-build` | 无 | 跳过构建推送，使用配置文件 URL 创建 Agent | `false` |
| `--skip-ssl-verification` | `-k` | 跳过 SSL 证书验证 | `false` |

### 部署模式说明

| 模式 | 说明 |
|------|------|
| `cloud` | 构建镜像、推送至 SWR、创建 AgentArts 运行时（默认） |
| `local` | 构建镜像并在本地 Docker 中运行 |



Interpretation: SDK region defaults and deployment descriptions do not prove regional coverage, visual workflow support, account permissions, actual endpoint or fees.
