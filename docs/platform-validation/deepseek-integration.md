# DeepSeek 接入 AgentArts：条件配置与验证

日期：2026-11-17。用户确认已有DeepSeek API，已确认来自DeepSeek官方平台；MaaS是否开通未知，但不阻断本轮。
这是阶段二的接入建议，非最终模型选型或已联调结果。按用户提供的赛题要求，核心Agent必须在AgentArts构建/编排/部署；提供的大赛文本没有要求必须使用MaaS模型。可先验证已有DeepSeek，MaaS留待后续资源/成本比较，不为本步先购买。

## 本次官方资料核实

成功获取并读取：
- [官方调用入门](https://api-docs.deepseek.com/)
- [当前模型与价格](https://api-docs.deepseek.com/quick_start/pricing/)
- [工具调用](https://api-docs.deepseek.com/guides/tool_calls/)
- [思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)

本次原始HTML、正文、时间和SHA-256记录在evidence/deepseek-doc-access.json及deepseek-thinking-access.json。以下参数是本次2026-11-17读取结果，不外推到第三方服务或用户账号的实际可用模型。

官方页当前列出OpenAI兼容base_url为https://api.deepseek.com，示例完整聊天请求为https://api.deepseek.com/chat/completions；模型列为deepseek-flash、deepseek-v4-pro。
价格页Flash相对Pro较低，可作为最小验证候选；不能以旧资料中的deepseek-chat/reasoner名称替代本次已读信息，用户已在使用的精确ID仍需确认。

## 已确认官方API：本轮采用Flash配置建议

| AgentArts字段 | 建议填写 | 边界 |
|---|---|---|
| 提供商名称 | deepseek-provider | 平台自定义显示名 |
| Base_url | https://api.deepseek.com | 官方文档值；AgentArts实际如何拼接路径仍需一次真实请求核实 |
| 模型服务名称 | deepseek-probe | 平台内名称，不是上游模型ID |
| 模型名称 | deepseek-flash 可作候选 | 以用户账号实际开放/已验证的精确ID为准；若不确定先确认 |
| API接口协议 | 标准OpenAI协议 | 和截图可见选项、上游官方兼容格式匹配；不代表所有参数已兼容 |
| 模型类型 | 仅选“文本对话/图像理解”合并项 | 第一轮只验证文本，不因合并标签宣称视觉已通过 |
| API凭据 | 用户直接配置到平台实际鉴权入口 | 不放聊天、截图、Git或日志；本次不猜未显示的鉴权字段 |

不要把完整/chat/completions路径当base_url直接填写，也不无依据增加/v1后缀。如平台报路径错误，核对真实请求最终URL和官方接口，不盲目轮换地址重试。
若服务来自其他平台，使用该平台真实base_url、协议、模型ID与凭据；DeepSeek品牌相同不意味着这些参数相同。

## 兼容性要点

- 官方页描述支持Tool Calls，仍需AgentArts真实工具往返验证；模型本身不执行文献工具。
- 官方说明思考模式默认开启。第一轮若平台提供并支持额外请求参数，可按官方格式设置thinking.type=disabled，先验证普通短文本与工具调用；没有此入口时不编造字段，也不声称提示词能关闭思考模式。
- 思考模式下携带tools的后续请求需按官方协议传回reasoning_content，否则可能400。应核查AgentArts适配器是否保留必需字段；这属于协议兼容验证，不把模型思考文本作为比赛证据或用户报告内容。
- 本次先不用strict Beta或/beta端点，不把JSON输出支持等同严格Schema已验证，也不接入厂商付费搜索/OCR代替文献工具。
- 不安装DeepSeek Harness或另搭独立本地Agent；任务规划与工具编排仍由AgentArts负责。

## 最小调用与费用边界

先保存经过确认的提供商/服务配置，再使用平台实际提供的连接检查或一轮短文本请求；是否有测试按钮以实际页面为准。
测试只用于连通性，不能替代Agent创建、编排、部署、官方API和文献工具调用五项验收。限制输出长度/关闭思考模式仅在平台确有对应配置且兼容时设置；不批量论文或自动循环重试。
记录真实状态码、响应概要、耗时、usage和费用，不记录凭据，不伪造输出。

官方Flash峰时每百万token未缓存输入$0.30、输出$1.20，谷时分别$0.15/$0.60；这是美元计价、模型官方价，不是AgentArts环境/日志/网络的总费用。实际用户若通过第三方服务，须采用其实际价格。官方文档值不证明用户账号有余额或免费额度，本次未产生任何推理调用。

## 当前下一步

官方来源和Flash系列已由用户确认，无需再次询问来源。可按 [Flash具体填写单](deepseek-flash-configuration.md) 配置供应商和模型服务；官方API ID为deepseek-flash。Pro显示名与本次文档版本存在差异，本轮不用Pro，不拼接未知ID。

保存后记录真实服务列表与平台连接结果；没有测试入口时先保留实际界面。Key直接配置平台，不发聊天。本次尚未执行模型调用，五项平台验收未通过。
