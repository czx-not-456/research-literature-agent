# 在线学术文献 API 比较

> 2026-11-17 计划修订：当前阶段顺序及职责以 [开发计划](../../DEVELOPMENT_PLAN.md) 为准。新增阶段二先验证 AgentArts 平台工作流，详细设计/核心开发/完整联调/系统测试/正式部署分别为阶段三至七。平台必须完成核心智能体的构建、编排和部署；本报告原始调研事实保留 2026-11-16 日期，本次没有新增平台实测结论。

日期：2026-11-16；未注册账户、未申请 Key、未调用付费搜索。官方正文、探测响应及失败记录在 evidence/。价格/限额会变，不能以历史常识替代本次资料。

## 推荐组合（待确认）

Crossref 用于 DOI/元数据匹配，arXiv 用于相关领域开放预印本发现；OpenAlex 作为跨学科补充，先由用户确认免费账户及预算；Semantic Scholar 先解决 Key 与数据许可适用范围再启用。不是把四家一开始无差别并发查询。

中文 PDF 上传能力与中文在线检索覆盖是两个问题。这四源含中文或接受中文字符串，不代表能覆盖知网、万方等中文数据库。对中文检索可用性必须以真实中文主题、作者和 DOI 样本验证；如覆盖不达标，应明确展示来源限制或评估合法授权接口，不能抓取受限平台补齐。

## 官方条件比较

| 服务 | 功能、元数据与过滤 | 费用/认证/限流（本次资料） | 许可与限制 | 本次实测 |
|---|---|---|---|---|
| OpenAlex | 跨学科 works、作者、年份/概念或主题等；来源、DOI、OA 链接；摘要可能缺失或为 inverted index | 认证页：无需 key 可基础使用；免费 key 提高日预算 10 倍并支持后续 cursor 页；无 key 10 RPS、免费 key/预付 30、年付 50，特定复杂查询更低；免费账号日预算 $1 | 完整价格页/CC0 原始许可页面本次 403/404；不能据此批准全文再分发，也不能声称免费无限调用 | 单次 GET 返回 429；未取得可用结果，不判为成功 |
| Semantic Scholar | 论文、作者、年份、引用网络、部分摘要与 openAccessPdf；具体端点过滤不同 | 官网：无鉴权共享 1000 RPS 池，绝非单用户额度；新 API key 初始 1 RPS；部分端点须 key；没有本次核实的统一付费报价 | API 协议、S2 数据许可及原论文许可分别适用；提及 CC BY-NC/ODC-BY 等，需来源署名；不能把全部数据当 CC0 或默认允许商用 | 单次 GET 返回 429；Key 未申请 |
| Crossref | 关键词/书目检索、DOI 元数据核对、作者与时间条件；摘要、领域标签并不完整 | 公共 REST 无注册；2025-12-01 起 public：单条5 RPS/列表1 RPS，并发1；polite：单条10/列表3 RPS，并发3；加合法 mailto；Metadata Plus 为付费另服务 | 官方：绝大部分元数据不受版权限制，可任意用途；部分摘要仍有作者/出版商版权；落地全文许可独立 | GET 200，返回 JSON；响应头 1 请求/1s，符合公共列表池 |
| arXiv | Atom API，关键词、作者、学科与日期等检索，摘要和版本/链接；领域偏理工与预印本 | 官方 API 条款：免费；legacy API 同一控制范围所有机器合计每3秒最多1请求、单连接；高量需联系，不得多机绕限 | 描述性元数据可用，全文依每篇许可；arXiv 非独占许可不等于可任意再分发；缓存与归属应遵循条款 | GET 200，成功解析到 Atom entry；不代表 PDF 下载与业务导入已完成 |

OpenAlex 的旧版“每天固定十万次/免费”说法不能直接沿用。当前认证文档明确按预算与请求类型计量，并提示新账户首 $1 消耗的节奏约束：每5分钟最多 $0.10；实际返回 Retry-After 时应遵守。没有 key 的预算具体金额和逐类查询单价本次未核实，不外推。

Semantic Scholar API 无统一“全部内容可自由商用”的结论。必须分 API 使用授权、数据集许可证、摘要/全文第三方版权、商标署名四层核查。若后续商业化或公开导出数据，应再核验用途是否需要额外书面授权。

## 官方证据

- OpenAlex 旧文档实际重定向到 [当前认证页](https://help.openalex.org/api/authentication/)，正文含最新规则（2026-11-16 更新）；[价格](https://help.openalex.org/access/pricing/) 和 [费用示例](https://help.openalex.org/access/example-costs/) 本次 403，不能补造收费表。
- [Semantic Scholar API](https://www.semanticscholar.org/product/api)；[API License Agreement](https://www.semanticscholar.org/product/api/license)，协议页面 last updated 2023-05-17，本次仍为官网返回版本。
- [Crossref REST 文档](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)；[官方限流调整公告](https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/)，2025-11-05 公告，2025-12-01 生效。不要误用公告页面底部网站 CC BY 许可作为 API 数据整体许可。
- [arXiv API 条款](https://info.arxiv.org/help/api/tou.html)；查询语法、排序和最大分页等参数实施时按当时官方手册再核对，不推定能绕过最大返回量。

## 真实 GET 探测

具体 URL 见 evidence/official-access-extra.json，保存原始成功响应：
- Crossref：works，query.bibliographic=retrieval augmented generation，rows=1。
- arXiv：search_query=all:retrieval，max_results=1。
- OpenAlex：works，search=retrieval augmented generation，per-page=1；429。
- S2：paper/search，query=retrieval，limit=1，fields=title,year,url,externalIds；429。

每源只做一次小请求，不轮换 IP、不追加并发、未把错误伪装为空结果。429 只说明本次请求受限，无法单凭状态码区分共享网络、预算或其他限制；不能推断 API 永久不可用。成功响应还应验证业务 schema、是否存在原文及其许可。本阶段未开发导入功能。

## 导入与费用控制建议

1. 保存 provider、原始 ID/URL、查询条件、获取时间、原始字段、许可状态；DOI 标准化后匹配，arXiv 保留版本，不能把不同版本粗暴删并。
2. 先导入元数据，全文显示“可获取/无合法可获取全文/待用户上传/下载失败”。无全文不能生成页码和原文证据。
3. 各源独立限速、并发、缓存与短期请求合并；429 尊重 Retry-After，超时/5xx 有界退避；Key 无效与配额耗尽分别提示。
4. 按实际端点能力映射作者、年份、领域过滤；不支持的筛选应明确说明，不用前端选项冒充服务端已过滤。
5. 保持来源与原始链接；模型补全值保留为待核实，不能覆盖权威字段。
6. 禁止未经确认注册账户、发送邮件、超出免费额度或购买 Metadata Plus；本次均未发生。
7. 中文回归样本应包含同名作者、多种中文期刊、英文题名中文作者、无 DOI 论文；以人工参考集合评估召回和误配。

进入阶段二前确认是否接受此组合与中文覆盖边界。运行期动态读取额度/响应头的建议需设计落地，当前尚未实现。

## 探测结果的内容质量限制

Crossref此次第一条返回type=other，标题为Master Retrieval-Augmented Generation (RAG) Systems，出版商Packt。响应有真实DOI并不意味着它是符合要求的学术论文；此请求仅证明搜索与JSON结构可达。后续需要显式类型筛选、用户查看类型，以及主题/作者/年份匹配验证，不能把任意DOI结果自动纳入科研论文矩阵。
