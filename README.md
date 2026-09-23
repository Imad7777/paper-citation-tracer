# paper-citation-tracer

**给论文写作用的引文溯源工具：给一段引文，自动在 PDF 原文里定位对应句子并标黄——核验"这句引文到底出不出自这篇文献"，证据摆在你眼前，判断由你做。**
Trace any quote back to its exact source in the PDF — and highlight it.

> 不是查重、不是自动判真伪：是把每条引文的**原始证据**从 PDF 里翻出来摆在你面前。

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-%3E%3D1.24-green.svg)

![before/after preview](examples/preview.png)

## 为什么需要它 / Why

用 AI 辅助写论文时，它插入的引用经常「看着像那么回事」：句子通顺、作者年份都对，
但翻出原文一对——定义被转述走了样、关键结论张冠李戴、甚至整句查无出处。
**核验 AI 给的引用是否站得住，是作者自己的责任**；而逐条人工翻 PDF，
绝大多数人坚持不了三条就放弃了。

## 经典用法 / Classic Workflow（三件套）

1. **一段带引用的论文正文**——你刚让 AI 写完或润色的部分，中英文都行；
2. **对应的参考文献 PDF**——被引文献的原文文件；
3. 调用本 skill——它从引文中提取要害短语，在 PDF 全文中定位对应段落并标黄。

对照高亮读一遍：高亮内容撑得起你的引用 → 放行；定位不到、或高亮讲的和引用
不是一回事 → 这条引用需要换证据或改写。**判断永远由人做，工具只负责把原始
证据从 PDF 里翻出来。**

它的本质能力其实只有一句话：**在任意 PDF 里定位一段文字的原始出处并高亮**。
核验 AI 引用是它最常见的用途；不用 AI、纯手写综述时想确认「这句话到底出自
哪篇文献的哪一段」，同样适用。

## 怎么用：复制这段提示词 / Prompt Template

在 WorkBuddy 等 agent 里，把下面这段话连同 PDF 一起发出去即可：

```text
请核验下面这段文字里 AI 插入的引用是否合理。

正文（引自我的论文草稿）：
"After 2000 there was an increase in the number and variety of card decks
produced … The best known example is Methods [30] …"

被引文献 PDF：Methods.pdf
请在 PDF 中定位被引内容的原文位置并高亮，然后逐条告诉我：
每条引用能不能对上原文、有没有转述走样。
```

agent 会自动完成：从引文中提取要害短语 → 在 PDF 全文定位标黄 → 逐条报告
命中页码。**一次核一条引用最清楚**：一段里有 5 条引用，就把正文拆成 5 次
分别发；不要把整段原文都当短语喂进去，否则高亮会铺满整页（工具没坏，是
输入太宽——短语越短越独特，定位越准）。

### 为什么不能只靠 Ctrl+F？

因为 PDF 文本提取有三个经典陷阱——搜不到真不是你的错：

| 陷阱 | 例子 | 为什么 Ctrl+F 失效 |
|---|---|---|
| 智能引号 | `customer's` 存成 `customer’s` | 字符根本不同 |
| 连字 | `definition` 存成 `deﬁnition`（ﬁ 是一个字符） | 单字符 ≠ 双字符 |
| 跨行断句 | `holistic in\nnature and` | 短语被换行切开 |

本工具把这三个陷阱全部处理掉，并且把**匹配结果验证**也做成了流程的一部分。

---

## 安装 / Install

```bash
pip install pymupdf
```

## 命令行使用 / CLI Quick Start

```bash
# 基本用法：可重复 -q 传入关键短语
python highlight_citations.py paper.pdf \
    -q "holistic in nature and involves" \
    -q "cognitive, affective, emotional, social and physical"

# 限定页码范围、限制每个短语最多标注次数、保存后验证
python highlight_citations.py paper.pdf \
    -q "a customer's internal and subjective response" \
    --pages 1-8 --max-n 2 --verify

# 只看会命中哪里，不写文件（dry run）
python highlight_citations.py paper.pdf --quotes-file quotes.txt --dry-run
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `-q / --quote` | — | 关键短语，可重复；建议 8–25 字符的独特短语 |
| `--quotes-file` | — | 每行一个短语的文本文件（`#` 开头为注释） |
| `-o / --output` | `*_highlighted.pdf` | 输出路径（**永远不会覆盖原 PDF**） |
| `--pages` | `all` | 页码范围，如 `1-8`、`3-`、`-5` |
| `--max-n` | `3` | 每个短语最多标注次数（防止整页变黄） |
| `--color` | `yellow` | `yellow/green/blue/red` 或 `r,g,b`（0–1） |
| `--keep-references` | 关 | 默认扫到 References/Bibliography 就停 |
| `--dry-run` | 关 | 只报告命中位置，不写文件 |
| `--verify` | 关 | 保存后把每处高亮下的文本打印出来，人工核对 |

> **短语怎么选？** 用"动词 + 宾语 + 限定词"的独特短语，不要含标点/年份，
> 不要用全文出现 30+ 次的通用词。同一概念给 2–3 个不同短语做冗余匹配。
> See `--help` for the full option list.

## 作为 Agent Skill 使用 / Use as an Agent Skill

仓库根目录的 [`SKILL.md`](SKILL.md) 是一份完整的 agent skill（WorkBuddy /
Claude Code 等 agent-skill 格式）：把整个文件夹放进你的 skills 目录，agent
就能在你写综述时自动完成"读引文 → 选关键词 → 标注 → 验证"的全流程，
包括"第一篇引文对不上经典出处"这类需要判断力的场景。

在 **WorkBuddy** 中：`安装技能 → 从文件夹导入`，或直接把本目录复制到
`~/.workbuddy/skills/`。

## 目录结构 / Repository Layout

```
paper-citation-tracer/
├── SKILL.md                  # agent skill 定义（工作流 + 已知陷阱，核心文档）
├── highlight_citations.py    # 独立 CLI（无 agent 环境也能用）
├── requirements.txt
├── LICENSE                   # MIT
└── examples/
    ├── make_demo.py          # 生成含三大陷阱的示例 PDF
    ├── make_preview.py       # 生成 README 对比图
    ├── sample_paper.pdf      # 示例输入
    └── sample_paper_highlighted.pdf  # 示例输出
```

## 设计要点 / Design Notes

- **两级匹配策略**：先用 PyMuPDF 内置 `search_for`（归一化引号/连字后）；
  失败则退到词级重建文本的宽松匹配，把命中词映射回逐行矩形——跨行短语
  会得到逐行高亮，而不是一个巨大方框。
- **参考文献区自动跳过**：检测到 References/Bibliography 标题即停止扫描，
  可用 `--keep-references` 关闭。
- **验证内建**：`--verify` 把每处高亮下的实际文本打印出来。关键词"命中"
  但位置错了（同名术语在别处出现）只有靠人工核验才能发现。
- **Xref 警告不致命**：老 PDF 的 xref 表损坏时 MuPDF 会报警告，文件仍能
  正常保存和打开。

## 已知陷阱 / Known Pitfalls

完整的实战经验清单（扫描版 OCR 文档、`max_n` 失控、xref 警告、"第一篇引文
对不上出处"）见 [SKILL.md 的「已知陷阱」章节](SKILL.md#已知陷阱)。

## License

[MIT](LICENSE)
