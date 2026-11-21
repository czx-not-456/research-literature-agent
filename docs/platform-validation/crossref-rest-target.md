# AgentArts 阶段二 Crossref REST Target

2026-11-19，西南-贵阳一（`cn-southwest-2`）。`创建target.png` 和 `创建target（续）.png` 显示，创建网关时可以为 MCP 协议添加 REST API Target，通过自定义 OAS 配置现有 API。页面也提供已有 MCP Server、APIG、云服务等类型。当前先走 REST API 路线，由网关向 Crossref 发起 HTTPS 请求，无需为本轮托管 MCP 服务。

| 控制台字段 | 填写 |
| --- | --- |
| Target 名称 | `crossref-search` |
| 描述 | `阶段二验证用的 Crossref 期刊文章元数据检索` |
| Target 协议 | MCP |
| 类型 | REST API |
| OAS 文件导入 | 自定义。按实际页面选择导入本目录的 JSON 文件或粘贴完整内容 |
| 出站身份认证 | 无认证。Crossref 公共接口无需密钥 |

导入 [crossref-search.openapi.json](crossref-search.openapi.json)。确认预览（若有）只列出 `GET /works`，且主机为 `https://api.crossref.org`。Target 点“确定”后检查网关表单的关联列表与创建费用。网关保持已确认的 `defaultgw` 入网配置、IAM 入站、公共网络出站、语义检索关闭和会话保持关闭。若提交页仍显示创建限时免费且未要求订购，可提交本轮验证网关。网关版本沿用当前页面选定的 `2025-03-26`。此价格提示仅覆盖页面明确显示的创建费用，其他费用仍待核对。IAM 用于调用 MCP 网关，Target 的无认证仅用于网关调用 Crossref。

如果网关提供调试，先在网关执行一次检索。参数为 `query.bibliographic=retrieval augmented generation`、`rows=2`、`filter=type:journal-article` 和 `select=DOI,title,author,published,URL,type`。以预览返回的实际工具名为准，记录输入、`message.items` 中的标题与 DOI，及请求 ID（如提供）。若没有调试入口，保留 Target 状态和后续可见的关联入口。网关成功出站后，再验证当前 Managed Agent 能否绑定该工具，并在同一次执行轨迹中核对工具入参、原始返回与最终回答。

同样参数直接访问 Crossref 已返回 `status=ok` 和两条 `journal-article` 元数据。观察到 DOI `10.21275/sr251104092705` 及 `10.36085/jsai.v9i1.9897`，结果顺序和内容可随上游索引变化。Crossref 返回的是登记元数据。本轮仅核对返回字段和链接，保留缺失字段，并把论文是否相关与引用原文证据留给独立核验。实际 OAS 导入、网关调用、当前 Agent 绑定及官方 Agent API 调用仍待实测。

参考 [Crossref REST API 官方文档](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)。


## 2026-11-20 网关运行状态与下一次检索

网关列表截图显示 `research-literature-mcp-gateway` 在西南-贵阳一处于“运行中”，创建时间为 2026-11-20 17:07:04。列表提供“调用代码”，未展示关联 Target 的状态或请求结果。

1. 点击网关名称，查找 `crossref-search` 和可用的调试、测试入口。若可调试，按上面的四个参数运行一次，以工具列表实际显示的名称为准。
2. 若无调试入口，打开网关列表同一行的“调用代码”。保留官方示例的语言、端点路径、鉴权方式和请求结构供后续复现，移除实际 AK/SK、API Key、Token 或签名。
3. 网关出站结果须能看到本次工具调用返回的 `message.items`，核对题名、DOI 和来源链接。网关工具验证通过后，再验证 Managed Agent 绑定和执行轨迹，随后验证官方 Agent API。


## 实测工具名和参数结构

控制台生成的完整工具名为 `crossref-search_search_papers`。网关工具参数把四个查询键包装在 `query` 对象下。

```json
{
  "query": {
    "filter": "type:journal-article",
    "query.bibliographic": "retrieval augmented generation",
    "rows": 2,
    "select": "DOI,title,author,published,URL,type"
  }
}
```

实测成功时可从 `result.structuredContent.message.items` 读取候选文献。两条结果与直接检索中观察到的 DOI 一致。后续先核对 Managed Agents 的实际工具接入入口，并以该版本的 Playground 工具轨迹验收。网关“基本信息”栏可复制完整 MCP 调用 URL，网关使用 IAM 入站。Managed Agent 到网关的授权方式需根据平台实际配置核对。网关 MCP URL 与 Managed Agent 对外调用契约分别记录。


## 外部 MCP 客户端验证

“调用代码”提供了完整 `/mcp` URL 和 JSON-RPC `tools/list` 请求。示例的 `Authorization`、`X-Sdk-Date`、`mcp-session-id` 是待生成的值。探针尝试用华为官方 Python SDK 的 SDK-HMAC-SHA256 签名，随后按 MCP 2025-03-26 规范初始化。若服务端返回会话 ID，就在后续请求复用。当前网关是否接受该签名方案需要一次真实 IAM 请求确认。

在项目根目录运行。若当前 Python 已安装 `huaweicloudsdkcore`，可跳过安装步骤。

```powershell
py -3 -m venv .venv-gateway-probe
.\.venv-gateway-probe\Scripts\python.exe -m pip install huaweicloudsdkcore
.\.venv-gateway-probe\Scripts\python.exe docs/platform-validation/scripts/probe_gateway_mcp.py
```

脚本在本机终端隐藏输入 AK/SK，也可从当前进程的 `HUAWEICLOUD_SDK_AK`、`HUAWEICLOUD_SDK_SK` 读取。使用已获网关调用授权的身份，临时凭据还需通过 `HUAWEICLOUD_SDK_SECURITY_TOKEN` 提供 Security Token。请勿将凭据或签名写入项目或聊天。默认只列出工具。通过后可加 `--query "retrieval augmented generation"` 执行一次真实查询。脚本只打印工具名、题名、DOI、来源链接或错误状态。若失败，记录失败步骤及 HTTP/JSON-RPC 状态。

此测试目标为外部客户端到网关。AgentArts Runtime 到网关的运行时身份和外部客户端到智能体的 API 调用须独立验证。

参考 [华为云 Python 签名指导](https://support.huaweicloud.com/devg-apisign/api-sign-sdk-python.html) 与 [MCP 2025-03-26 传输规范](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)。


### 初始化返回 HTTP 401

网关控制台调试已通过，外部探针的 `initialize` 返回 401。先确认系统时间已同步、AK 与 SK 属于同一组启用的华为云访问密钥。若使用临时凭据，需同时提供对应的 Security Token。用现有虚拟环境重跑一次脚本，保留输出中的 `code`、`request_id` 和 `hint`，如有。只有 HTTP 状态时，通过原请求发生时间与服务侧日志或工单核对 IAM 签名格式和调用权限。探针不会打印原始响应、登录凭据或签名头。


### 对照验证 AgentArts 数据面 V11 签名

SDK-HMAC-SHA256 复测结果为 `initialize: HTTP 401; code=401; hint=authentication.`，服务端未提供可打印的请求 ID，无法据此确定根因。官方 AgentArts Runtime IAM 数据面使用 V11 签名。控制台的 MCP 示例未明示算法，V11 是对照验证方案，接收情况以真实请求为准。

沿用当前虚拟环境，运行一次 `.\.venv-gateway-probe\Scripts\python.exe docs/platform-validation/scripts/probe_gateway_mcp.py --signing v11`。端点、凭据输入方式、MCP 请求和权限保持相同。看到 `crossref-search_search_papers` 即通过外部 MCP 工具发现。若仍收到 401，记录输出及请求时间和时区，请华为云核对当前 MCP 网关 IAM 签名规范及调用主体权限。

参考 [官方 V11 签名实现](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/src/agentarts/sdk/utils/signer_v11.py) 和 [Runtime IAM 调用实现](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/src/agentarts/toolkit/operations/runtime/invoke.py)。


### V11 实网结果与下一项验证

用户的外部探针已返回 `status: ok`，工具列表为 `crossref-search_search_papers`，本轮实测使用 V11。沿用同一虚拟环境、网关与身份，追加 `--query "retrieval augmented generation"` 即可用同一会话验证 `tools/call` 到 Crossref。验收依据为实际返回的题名、DOI 和链接，并保留空结果或错误原样。[V11 工具发现证据](evidence/gateway-v11-tools-list.json)

云端候选路径是在 AgentArts Runtime 通过工作负载身份与已授权的委托取得 STS 临时凭据，以 V11 调用现有网关。官方身份指南记录了 STS 临时 AK/SK/Security Token 的获取机制。账号内的凭据提供商、委托权限、运行时出网、模型凭据来源和计费须按实际配置核对。部署资源准备参考 SDK 的容器和 SWR 说明。赛题要求的平台编排适用性独立确认。

- [Agent Identity 指南](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/sdk_user_guide/agent_identity_guide.md#sts-token-流程)
- [官方云端部署说明](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/toolkit_user_guide/deploy.md)


### 外部检索通过后的云端部署核查

外部 V11 `tools/call` 已返回两条带 DOI 的 Crossref 文献，结果见 [外部检索证据](evidence/gateway-v11-crossref-search.json)。本机验证已完成。

下一步查看当前区域的“智能体运行时”创建页，先核对下列实际字段和费用。云端部署使用单独的验证实例，复用现有网关和检索 Target。

| 待核对项 | 核对目的 |
| --- | --- |
| 创建方式与产物类型 | 确认当前账号提供源码、镜像或模板哪些入口。若只能用镜像，按官方 SDK 流程核对 SWR 与镜像权限。已有 Docker 客户端，但上次本机只读检查未连上引擎。 |
| 运行规格、费用与停用方式 | 获取实际计费或试用说明，确认最小规格及运行、存储和日志费用，决定是否提交。 |
| 委托、运行时身份与出网 | 核对可用工作负载身份、委托和凭据提供商。在运行时以平台提供的临时凭据签名，再验证它能否访问已通过的网关。 |
| 端点与调用认证 | 以官方 API/SDK 和实际部署记录确定入口，验证一次外部请求能触发该实例。 |
| 模型凭据与任务编排 | 核对现有 DeepSeek 配置能否供这一部署模式使用，随后验证模型实际选择工具。 |

官方 Runtime SDK 从请求上下文读取工作负载访问令牌，身份 SDK 提供 STS 临时 AK/SK/Security Token。SDK 会在缺少上下文令牌时尝试本地身份流程。验证实例应显式检查平台身份是否注入，并在缺少它时报告失败。本次成功使用的是用户本机 IAM 身份，尚未验证云端临时凭据或网关授权。部署前还需确认该方案符合赛题要求的平台编排口径。

验收顺序：运行时身份拿到临时凭据 → 运行时以 V11 调用已上线的 Crossref 工具 → 短任务中取得模型工具选择和结果 → 由外部客户端走官方 Agent API 复现 → 记录受控失败及用量。

- [Agent Identity SDK 指南](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/sdk_user_guide/agent_identity_guide.md)
- [运行时身份读取源码](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/src/agentarts/sdk/runtime/app.py#L234-L246)
- [AgentArts 云端部署指南](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/toolkit_user_guide/deploy.md)


### 智能体运行时列表与现有实例详情

两张新增截图分别为运行时列表与已有 `managed-agent-huawei-cit` 详情。列表的右上角按钮“托管智能体”是控制台可见的下一入口。列表标题显示 `1/1`，需通过问号、页面提示或打开入口确认其含义。若提示配额不足，保留原文以便检视可用路径。

现有 v2 详情在“基本信息”显示 SWR 镜像，在“权限与访问控制”显示 `DefaultAgentArtsRuntimeAgency`、`defaultgw` 与 IAM 入站，在“高级配置”显示 `2000mCPU | 8192MiB`、公网出站和监听端口 `18092`。现有配置仅用于了解实例，不能据此填到新部署中。新实例规格、身份权限与费用尚待核实。下一步打开“托管智能体”后查看表单或拦截提示。[截图审查证据](evidence/runtime-console-review.json)


### 托管智能体表单及自定义运行时镜像

已核对“托管智能体”三张截图。来源方式要求容器镜像。候选验证部署名为 `literature-runtime-probe`，保留 HTTP 入栈、IAM 入站、现有入网配置 `defaultgw`、公网出网、端口 `8080`、严格匹配与日志关闭。严格匹配的表单提示为 `/runtimes/{runtime_name}/invocations`，对外调用以平台生成的地址为准。默认规格为 `2000mCPU | 8192MiB`，未核对是否有更小规格。创建费标签“限时免费”与运行、SWR、日志实际费用分别核对。

验证源码在 [runtime_gateway_probe.py](scripts/runtime_gateway_probe.py)，镜像定义在 [Dockerfile.runtime-probe](scripts/Dockerfile.runtime-probe)。构建机有可用 Docker 后，可在仓库根目录构建本地镜像。此命令只构建镜像，不部署云资源。

```powershell
docker build -f docs/platform-validation/scripts/Dockerfile.runtime-probe -t literature-runtime-probe:0.1.0 docs/platform-validation/scripts
```

部署前核对当前区域 SWR 组织和镜像读写权限、可用运行时配额、运行价及委托权限。“选择镜像”用于查看账号当前可用的镜像来源。表单里的默认委托可用于核对当前权限，其 STS 换取权限及网关访问权待实测。使用非秘密的凭据提供商名称配置 `GATEWAY_STS_PROVIDER`，由运行时提供的工作负载令牌换取临时 IAM 凭据。调用体为 `{"query":"retrieval augmented generation"}`。已有 Managed Agents 资源继续保留。

本镜像只验证运行时到网关的连接、身份和真实文献检索。模型工具自主选择与赛题要求的编排验收需独立验证。SDK 已核对 PyPI 的 `0.1.11` 发布版，容器构建、推送与云端运行仍待实测。

- [运行时 SDK](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/sdk_user_guide/runtime_user_guide.md)
- [控制台表单证据](evidence/runtime-host-form.json)


### 本地镜像实测与 SWR 准备

本机标签 `literature-runtime-probe:0.1.0` 已实际构建并启动，端点和身份缺失处理通过，临时容器已停止。Docker Hub 认证服务超时，本次通过构建参数 `RUNTIME_BASE_IMAGE` 指向 ECR Public 的 Docker 官方 Python 镜像，固定为 `sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177` 的 Linux amd64 产物。Dockerfile 的默认基础镜像仍为 `python:3.12-slim`。

后续在华为云控制台核对“容器镜像服务 SWR”西南-贵阳一可写组织、目标私有仓库、配额和计费，并使用控制台给出的实际上传地址。如果没有可用组织，先确认开通/付费提示。确认后用 SWR 控制台的登录命令在本机认证，给已验证镜像打标签并推送。已在本地验证的临时 IAM 流程只到缺少运行时上下文这一关，部署后继续核对 STS 提供商、委托和实际请求。 [SWR 官方推送指南](https://support.huaweicloud.com/usermanual-swr/swr_01_0011.html)


### SWR 基础版组织与推送准备

截图显示西南-贵阳一的“组织管理”暂无数据，“我的镜像 → 自有镜像”暂无匹配记录。华为云官方说明基础版当前免费提供存储空间和流量。验证使用一个单独的 SWR 组织，建议名称 `research-literature-agent`。若界面有额外费用或权限提示，先核对提示。镜像推送后默认私有。

已在本机按建议组织准备 `swr.cn-southwest-2.myhuaweicloud.com/research-literature-agent/literature-runtime-probe:0.1.0` 标签，核对其 Docker 镜像 ID 与容器测试证据一致。待用户在控制台创建组织，并使用“登录指令”中当前区域的用户名和临时密码在本机完成 Docker 登录。如果实际组织名或登录指令中的仓库域名不同，则以控制台实际值重新打标签。当前镜像使用现代 Docker 的 OCI 产物，SWR 官方页面上传说明不支持 OCI 规范，验证选择 Docker 客户端推送。单平台推送命令如下。

```powershell
docker image push --platform linux/amd64 swr.cn-southwest-2.myhuaweicloud.com/research-literature-agent/literature-runtime-probe:0.1.0
```

- [SWR 基础版收费说明](https://support.huaweicloud.com/productdesc-swr/swr_03_0001.html)
- [SWR 组织管理](https://support.huaweicloud.com/usermanual-swr/swr_01_0014.html)
- [SWR 客户端推送](https://support.huaweicloud.com/usermanual-swr/swr_01_0011.html)
- [页面上传限制](https://support.huaweicloud.com/usermanual-swr/swr_01_0012.html)


### SWR 镜像地址与运行时提交前核对

已推送并核对的镜像地址为 `swr.cn-southwest-2.myhuaweicloud.com/research-literature-agent/literature-runtime-probe:0.1.0`，平台为 Linux amd64。可在“托管智能体”表单中使用以下候选配置。

| 字段 | 验证用设置 |
| --- | --- |
| 名称 | `literature-runtime-probe` |
| 镜像 | `swr.cn-southwest-2.myhuaweicloud.com/research-literature-agent/literature-runtime-probe:0.1.0` |
| 入网配置与协议 | `defaultgw`，HTTP 入栈，IAM 入站 |
| 出网、端口与路由 | 公网访问，`8080`，严格匹配 |
| 日志、存储与文件上传 | 优先保持关闭 |
| 环境变量 | `GATEWAY_STS_PROVIDER` 取实际获授权的 STS 凭据提供商名称 |
| 运行时委托 | 核对现有 `DefaultAgentArtsRuntimeAgency` 的委托配置和权限后选择 |

先核对“治理与安全”下的 Agent Identity/凭据提供商里是否已有 STS 类型，以及该提供商绑定委托的网关调用权限。托管表单的运行时委托与 STS 提供商的委托分别核对，名称相似不能代替权限确认。如果列表为空，待确定界面可选类型和创建条件后再配置。使用运行时工作负载身份换取临时凭据，无需把本机 AK/SK 或 SWR 登录密码填入容器环境变量。提交托管前核对当前区域规格及费用。[Agent Identity SDK 指南](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/sdk_user_guide/agent_identity_guide.md#sts-token-流程)


### Agent Identity 中 STS 对应的控制台入口

2026-11-21 截图显示当前选中“凭证库”，列表里有 `default`。这页只确认默认凭证库存在。官方运行时指南说明，STS 临时凭据对应的控制台类型为“出站身份”下的“IAM 委托”。下一步查看“出站身份”列表。如果已有 IAM 委托类型，核对其名称和关联的信任委托。如果没有，打开“创建出站身份”，选择“IAM 委托”，核对候选信任委托及所需权限后再创建。填入运行时环境变量 `GATEWAY_STS_PROVIDER` 的值为实际创建或现有的出站身份名称，且需验证它能换取具备目标 MCP 网关调用权限的临时凭据。

华为云还文档化了通过运行时用户委托和 MetadataProvider 直接取得临时凭据。该路径可在 IAM 委托型出站身份不可用时评估，当前 SWR 验证镜像使用的是 STS 凭据提供商路径。

- [使用 Identity 出站认证](https://support.huaweicloud.com/highcode-agentarts/agentarts_10_280.html)
- [运行时委托说明](https://support.huaweicloud.com/highcode-agentarts/agentarts_10_226.html)


### 默认运行时委托路线（镜像 0.1.1）

用户报告出站身份只有 `deepseek-api-key`，IAM 信任委托无可选项。截图确认出站身份表单要求提供信任委托。华为官方文档支持用运行时委托与 `MetadataProvider` 直接获取临时凭据。MCP 调用 API 文档写明该接口本身无需额外身份策略权限，现有网关仍需 IAM 签名，运行时身份是否被本账号网关接受待实测。因此本轮先选已有的运行时委托，跳过单独的出站身份和信任委托。

托管当前验证用独立运行时 `literature-runtime-probe` 时，镜像选 `swr.cn-southwest-2.myhuaweicloud.com/research-literature-agent/literature-runtime-probe:0.1.1`，运行时委托选 `DefaultAgentArtsRuntimeAgency`，环境变量 `GATEWAY_STS_PROVIDER` 留空。保留 HTTP、IAM 入站、`defaultgw`、`8080`、严格匹配和公网出站。提交前根据控制台核对配额及费用提示。验证调用体为 `{"query":"retrieval augmented generation"}`。若返回 `metadata_credentials_unavailable`，查运行时委托和元数据注入。若是网关 401/403，查运行时临时身份、签名和目标网关配置。独立的 STS 路径仍可通过填写已获授权的提供商名称启用。

- [委托与运行时临时凭据](https://support.huaweicloud.com/highcode-agentarts/agentarts_10_226.html)
- [MCP 网关调用与认证](https://support.huaweicloud.com/api-agentarts/InvokeMcpGateway.html)
- [新版镜像和验证记录](evidence/runtime-metadata-swr.json)
