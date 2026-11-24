# 在线学术检索与导入

## 使用方法

在课题页打开「在线检索」，选择 Crossref 或 arXiv，组合关键词、作者、年份和研究领域。勾选结果后点击「导入所选记录」，从课题页的「在线文献记录」查看书目信息和来源链接。也可用课题原有搜索框查找在线记录。

每页 10 条，首版支持前 50 页。Crossref 按出版日期筛选，关键词、作者和领域使用来源服务的相关性匹配。arXiv 以作者字段、首次提交日期和学科分类检索。中文和英文覆盖取决于来源收录。

记录按课题、来源及来源标识去重，arXiv 保留版本。同一论文在不同来源可以各有一条记录。同课题已有相同 DOI 的 PDF 时，详情可打开对应原件。获取其他 PDF 后可回课题上传用于问答与引用核验。

## 使用限制

- Crossref 公开 REST 池免注册。列表请求按每秒最多一次、单并发处理，短期缓存并按 429 退避。Metadata Plus 为收费服务。本应用保存书目事实字段，摘要可能受独立许可保护。[限流与费用](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication) · [数据许可](https://www.crossref.org/documentation/retrieve-metadata)
- arXiv 公开 Atom API 按至少三秒一次和单并发处理。描述性元数据为 CC0，论文全文使用各篇许可。[API 手册](https://info.arxiv.org/help/api/user-manual.html) · [使用条款](https://info.arxiv.org/help/api/tou.html)

## 验收

29 项自动化测试通过，覆盖分页参数、限流、去重、跨课题拦截、原始链接与本地同 DOI 关联。三组真实在线查询通过应用网页路由检索并导入临时库，重开数据库后复核记录。

| 来源 | 条件 | 保存记录 |
|---|---|---|
| Crossref | 英文主题、作者 Lewis、2020、自然语言处理 | 10.12927/hcq.2020.26334 |
| Crossref | 中文关键词「深度学习」 | 10.26549/jxffcxysj.v3i10.5413 |
| arXiv | retrieval、2023、cs.CL | 2304.11095v1 |

Chrome 在 1280 和 412 像素窗口加载了导入后的课题记录。用户截图确认一次网页版 AgentArts 问答成功，平台自主调用外部学术工具仍待验收。
