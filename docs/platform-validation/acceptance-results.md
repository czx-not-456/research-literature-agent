# 阶段二验收状态

更新：2026-11-18。**进行中，部分取得成功证据，未完成阶段验收，不进入阶段三。**

## 当前证据与结论

| 检查 | 当前状态 | 证据范围 |
|---|---|---|
| Managed Agent创建 | 成功（用户报告+截图） | agent-tg2vc3r0可选择且在Playground运行；不把显示标识当API UUID |
| 平台内文本交互 | 成功（截图） | 11月18日11:02显示真实问题及回复；非助手新发起测试 |
| 模型供应商/环境具体配置 | 未核实 | 能运行说明当前调用配置可用，但图中无精确模型ID、供应商及环境详情 |
| 工作流/工具编排 | 未核实 | 未见配置或执行轨迹，单轮问答不代替科研任务自主执行 |
| 平台部署/发布 | 部分证据 | 已有平台执行，尚缺发布版本、对外入口或可复现部署记录 |
| 外部官方API调用 | 未取得证据 | 缺外部客户端真实请求/响应与鉴权方式，Playground不代替这一项 |
| 平台调用真实文献工具 | 未取得证据 | 缺绑定方式及同次平台/工具输入输出轨迹 |
| 本地Crossref数据源 | 先前探测成功 | 仅数据源与本地参数验证，不代表平台已调用 |
| 用量与费用 | 待核查 | 输入45877、输出11、总计45888为页面显示；范围/单位/轮次/实际计费未知 |
| 官方资料可读性 | 已有部分资料 | DeepSeek官方正文成功，部分华为官方网页此前为验证页；不伪报平台完整文档已读 |

## 本次交付记录

- [成功截图与后续验证](playground-success-and-next-validation.md)
- evidence/playground-success-review.json：图像校验值与可见事实，不保存账号/凭据或思考正文。
- [前序验收记录](history/acceptance-results-before-playground-success.md)：保留此前调查经过，旧的“全部未执行”等描述仅代表旧状态。

## 当前下一步

先只读查看智能体详情/编辑与工具/Skill配置、官方API说明入口（如有），并核对本次输入计量异常偏大的来源；不要重复相同问答或批量测试。需要执行轨迹/用量元数据，不需要完整思考正文或密钥。

之后按已核实接口接入真实文献工具，验证平台工具往返、官方API和失败处理。阶段二授权持续有效；阶段三及之后未授权。此前本地文档检查通过数不作为本轮平台通过数量。

## 当前Agent详情更新（2026-11-18）

已审查agent-huawei-cit详情图，模型deepseek-provider/deepseek-flash、环境environment-huawei-cit、内置工具0/8、Skills 0/50、提示词显示--。Agent UUID可见，访问域名截断，不拼接API。先前Playground成功属于agent-tg2vc3r0，不能自动视为新Agent已调用通过。下一步见 [操作清单](agent-huawei-cit-next-steps.md)：编辑页工具/Skill接入类型和官方API说明/完整域名。未新调用、部署或购买。


## MCP 网关运行状态（2026-11-20）

用户创建的 `research-literature-mcp-gateway` 在网关列表显示“运行中”，并提供“调用代码”入口。阶段二新增网关资源创建证据。关联 Target 状态、真实工具请求、当前 Managed Agent 工具绑定及外部官方 Agent API 仍待验证。下一次测试见 [Crossref REST Target 操作](crossref-rest-target.md)。


## Crossref 网关调试通过（2026-11-20）

用户在 AgentArts 网关控制台调试工具 `crossref-search_search_papers`。详情显示 `crossref-search` 在线，调试截图显示四个参数嵌套在 `query`。用户提供的完整响应为 `isError: false`、`structuredContent.status: ok`，含两条 DOI、题名和链接。截图与粘贴响应的 JSON-RPC ID 不同，分别记录。已通过“网关 → Crossref”一项，待验证 Managed Agent 绑定、智能体实际工具调用及对外官方 Agent API。[网关证据摘录](evidence/gateway-crossref-debug.json)


## Managed Agents 编辑页入口核查（2026-11-20）

截图 `屏幕截图 2026-11-20 183248.png` 显示环境下拉已选 `environment-huawei-cit`，带“公网访问”标记。既有创建环境页证据说明该标记用于出网配置。内置工具下拉只提供通配选项及 shell/文件相关工具，未列出 MCP、外部工具或网关。展开的下拉遮住下方区域，需收起后核对该区剩余字段。先前的 Skill 选择器显示暂无数据。当前结论限于已查看的控制台入口，Managed Agents 的其他接入方式仍待官方说明或实际界面证实。

编辑页的“入站身份认证”标为 IAM，属于调用该智能体的身份校验。该页面尚未给出 API 请求路径与请求体，也未显示从智能体到 Crossref MCP 网关的绑定配置。网关已通过独立工具调试，智能体工具调用仍待验证。


## 当前 Managed Agents 表单确认

用户确认收起下拉后，“工具与 Skill”至“权限与访问控制”之间只有“选择 Skill”，该选择器此前显示“暂无数据”。当前账号与区域的该编辑表单没有直接绑定 MCP 网关的入口。平台内其他入口或接口的适用性仍待核实。保留网关调试通过的结果，不计为智能体调用通过。

替代候选是用官方 SDK 将最小智能体部署到 AgentArts 云端运行时，并接入已验证的网关。官方文档证实 SDK 支持 Docker/SWR 云端部署及对部署实例发起调用。网关数据面认证、实际资源权限/费用，以及该路线对赛题平台编排要求的适用性仍需确认。下一步读取当前网关“调用代码”的脱敏示例，验证鉴权与传输方案，再决定是否试部署。

- [AgentArts 云端部署指南](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/toolkit_user_guide/deploy.md)
- [AgentArts Runtime SDK 指南](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/sdk_user_guide/runtime_user_guide.md)
- [AgentArts invoke 指南](https://github.com/huaweicloud/agentarts-sdk-python/blob/cba0fd67859941f5c7449b189dd96b57111f4079/docs/cn/toolkit_user_guide/invoke.md)


## 外部客户端 IAM 工具发现通过

用户在本机以 V11-HMAC-SHA256 通过既有 MCP 网关的 IAM 校验，完成初始化并列出 `crossref-search_search_papers`。此前网关控制台已实测 Crossref 工具执行。本次命令没有 `--query`，外部客户端的 `tools/call`、云端运行时身份、智能体执行轨迹与对外智能体 API 分别待测。[V11 工具发现证据](evidence/gateway-v11-tools-list.json)


## 外部客户端真实 Crossref 检索通过

用户本机以 V11 完成 MCP 会话后发起 `tools/call`，网关返回两条 Crossref 学术元数据，DOI 和链接与网关控制台实测一致。至此已验证两条工具路径，分别是“网关调试 → Crossref”和“本机 IAM 客户端 → 网关 → Crossref”。两者均是文献登记元数据证据。云端智能体工具选择、运行时身份、部署和官方 Agent API 仍待验证。[实测输出](evidence/gateway-v11-crossref-search.json)


## 已有云端运行时详情确认

列表显示 `managed-agent-huawei-cit` 状态正常，详情显示 v2、SWR 镜像、运行时委托、IAM 入站及现有规格。新增已有运行时部署配置证据。当前运行时对外调用和独立 Crossref 网关的智能体调用仍未取得实测证据。待从“托管智能体”入口核对创建权限、实际表单和计费。[截图审查证据](evidence/runtime-console-review.json)


## 自定义运行时创建表单与镜像准备

截图确认此控制台支持配置容器镜像、HTTP/IAM、监听端口、路由和运行时委托。已准备云端身份与检索连通性探针的源码和镜像定义。当前未建立云端验证实例，SWR、费用、委托权限、实际 STS 凭据签名与 Agent 业务编排待核对。[表单证据](evidence/runtime-host-form.json)


## 自定义验证镜像已构建并在本机通过检查

用户已将 WSL 更新到 3.0.5.0，确认 Docker Server 29.9.3 与 Linux amd64 引擎。使用已核对摘要的 ECR Public Docker 官方 Python 镜像构建 `literature-runtime-probe:0.1.0`。容器内真实 AgentArts SDK 的 `GET /ping` 返回 HTTP 200，`POST /invocations` 对空查询返回 `invalid_query`，对无平台身份的有效查询返回 `workload_token_missing`。下一步确认同区域 SWR 目标及运行时委托，在云端验证临时凭据与网关连通。[本地容器实测证据](evidence/runtime-local-container-smoke.json)


## 验证镜像已推送并核验 SWR 版本

已使用本机 Docker 现有登录状态将已通过容器检查的镜像推送至西南-贵阳一 SWR。远端标签 `0.1.0` 与推送摘要的配置及层一致。云端智能体运行时尚未创建，运行时临时凭据、模型编排及官方 Agent 调用仍待验证。[镜像推送证据](evidence/runtime-swr-push.json)


## 运行时委托版镜像已推送

出站身份暂缺可选信任委托。验证探针默认通过官方 SDK 的 `MetadataProvider` 获取运行时委托临时凭据，并保留显式 STS 路径。0.1.1 通过离线分支测试和隔离网络的真实容器检查，推送至同一私有 SWR，远端清单与构建产物一致。尚未托管或验证云端委托、网关响应及智能体工具编排。[验证记录](evidence/runtime-metadata-swr.json)
