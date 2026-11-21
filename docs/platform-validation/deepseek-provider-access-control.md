# DeepSeek模型供应商：权限与访问控制填写单

日期：2026-11-18。依据：161220截图与已读取的DeepSeek官方Authorization示例。只作填写说明，未代用户保存或调用。

| 字段 | 应填/选择 |
|---|---|
| 出站身份认证 | API Key认证 |
| 出站身份下拉 | deepseek-api-key（截图已选中） |
| 位置 | 标头 |
| 参数名称（可选） | Authorization；虽截图提示默认为此，建议显式填写 |
| 前缀（可选） | Bearer，不加引号；原始Key仍保存在出站身份里 |
| 出网网络配置 | 公网访问，匹配DeepSeek公共API |
| 高级配置：标签（可选） | 当前最小验证可不添加 |

预期最终HTTP鉴权结构：Authorization: Bearer <DEEPSEEK_API_KEY>。这里占位符是说明，不是可直接使用的Key。Bearer与Key之间应有一个空格；按截图前缀框的示例填Bearer，最终实际组装仍需调用记录核实。

不选“参数查询”，不把Key放URL、参数名称或前缀框。参数名称只填Authorization，前缀只填Bearer。此前“原始密钥不加Bearer”指身份里的Key值，前缀在本页单独配置。

截图直接确认了API Key认证和该身份可选择，并非证明供应商已保存、身份权限全部正确或本次调用已成功。填好后可完成供应商保存；若报错提供脱敏文本，不发含Key的请求头或完整HAR。已有Playground成功证据不改变本次配置仍待核验的事实。
