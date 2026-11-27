# 本地元数据与文献矩阵质量复测

本轮在用户确认后优化本地 PDF 元数据和矩阵候选。评测使用真实 Flask 导入和矩阵表单、临时 SQLite 数据库及四篇公开出版 PDF。修改前以 Git 提交 cd51541 中的解析和矩阵代码为基线，两组使用同一标注和 SHA-256 锁定的原件。四篇的元数据以出版方书目为准，矩阵标注按 PDF 物理页与连续引文核对。测试环境为 Windows 11、Python 3.12.4。[标注与复现脚本](check_quality.py)

## 同一标注的前后对照

| 指标 | 修改前 | 修改后 |
| --- | --- | --- |
| 题名、作者、年份、DOI 共 16 项 | 8 项匹配，8 项留空 | 14 项匹配，2 项留空 |
| 9 个指定矩阵字段的页码和引文锚点 | 3 项匹配，5 项选中不同候选，1 项留空 | 9 项匹配 |
| 原有系统回归加本轮回归 | 47 项通过 | 49 项通过 |

| 样本 | 数据集候选修复后物理页 | 其他核对字段 |
| --- | --- | --- |
| BERT | 第 5 页，BooksCorpus 和 English Wikipedia | 指标第 1 页。 [ACL 出版页](https://aclanthology.org/N19-1423/) |
| 中文机器阅读理解综述 | 第 6 页，BookTest 和数据集统计表 | 指标第 7 页。 [期刊原文](https://html.rhhz.net/tis/html/202107024.htm) |
| ChineseBERT | 第 4 页，CommonCrawl 预训练数据 | 方法第 2 页、指标第 6 页。 [ACL 出版页](https://aclanthology.org/2021.acl-long.161/) |
| 中文语义角色标注 | 第 5 页，清华大学依存句法树库 | 指标第 6 页。 [期刊原文](https://html.rhhz.net/tis/html/201910012.htm) |

元数据改进补齐了四篇样本的年份和两篇中文论文的作者。年份来源为明确的会议页范围与日期、自身引用格式或明示出版字段。无标签中文作者仅在与文件题名相邻且有署名上下文时提取。DOI 从 PDF 属性或前置信息取得。两篇英文样本的 DOI 在出版方网页上可核对，但 PDF 没有可用的本篇 DOI 证据，因此留空。回归验证了封面推荐文章和参考文献中的其他 DOI 不会作为本篇 DOI。

数据集优先选取说明实际数据来源的章节，其次采用明确描述试验或训练数据使用的段落。评价指标优先指标章节、明确报告的指标或带数值的指标描述。引文继续使用原页连续文本。两组评测统计的是指定字段和证据位置的匹配数。样本规模和标注字段有限，矩阵全字段准确率待更大样本验证。

## 复现与范围

```powershell
.\.venv-library\Scripts\python.exe -B -X utf8 -m unittest discover -q
.\.venv-library\Scripts\python.exe -B -X utf8 docs/system-testing/check_quality.py
```

复现脚本可接收包含样本 PDF 的目录，也可从出版方下载到内存。回跑上一轮真实文献验证，PDF 原件与页码、矩阵 CSV、扫描页回退、报告编辑和 Word/Markdown 导出通过。[端到端复现脚本](check_library.py)

新规则应用于新导入的文献和新增矩阵候选。既有文献现可通过批量更新入口预览并应用。[存量更新验收](../design/library-refresh.md)AgentArts 云端验收继续按约定暂缓。
