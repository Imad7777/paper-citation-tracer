---
name: pdf-citation-highlighter
description: |
  为学术文献综述任务，定位 PDF 全文中与用户引文（中文段落）对应的英文原文段落，
  用 PyMuPDF 添加高亮注释（黄色），输出标注后的 PDF 文件。
  适用于：用户在论文/综述写作中提供"引文原文"和"参考文献 PDF 路径"，要求把 PDF 中
  对应的定义段、关键术语、引用位置都标黄，方便后续写文献综述时直接对照原文。
  触发词：高亮文献、高亮 PDF、文献段落标注、标黄引文、PDF 标注、
  highlight citations in PDF、mark up PDF with quotes、cite-source highlight。
---

# PDF Citation Highlighter

为用户的引文（中文或英文段落）在指定的 PDF 全文中找对应的原文段，并添加高亮注释。

> 本仓库同时提供独立 CLI `highlight_citations.py`：没有 agent 环境时，
> 也可以直接在命令行完成同样的标注（见 README）。

## 适用场景

- 用户正在写文献综述/学术论文，给出一段引文 + 一组 PDF 路径
- 需要把 PDF 中真正对应引文定义的原文段标黄
- 输出：保留原 PDF 所有内容，仅在原文位置加 highlight 注释（不修改文字、不删页）

## 工作流

### 1. 通读 PDF，定位关键页

```python
import fitz  # PyMuPDF, pip install pymupdf
doc = fitz.open(pdf_path)
for pno in range(len(doc)):
    text = doc[pno].get_text()
    # 用引文的核心术语作为搜索关键词
    # 例如"holistic in nature"、"multidimensional construct"
    if "holistic in nature" in text.lower():
        print(f"Page {pno+1} matched")
        print(text[:1500])
```

**关键**：
- 优先看 abstract（第 1 页）和 introduction（前 3-4 页）
- 用 `len(doc)` 确认总页数，只在前 30% 找定义段，避免误中高频词
- 排除参考文献区：参考文献通常在第 N-3 页之后（看是否有 "References" 标题 + 大量作者-年份格式）

### 2. 提取精确短片段作为高亮关键词

**避免问题**：
- ❌ 长句（>50 字符）容易因换行/智能引号匹配失败
- ❌ 智能引号 `\u2019` 需归一化为 ASCII `'` 才能用 `search_for`
- ❌ 通用词（如"servicescape"）全文出现 30+ 次，要用 `max_n=2~3` 限制

**经验**：
- ✅ 用 8-25 字符的独特短语（动词+宾语+限定词）
- ✅ 不含标点/数字/年份（容易在版式里被打断）
- ✅ 同一概念用 2-3 个不同片段作冗余匹配

```python
# 关键短片段示例
key_quotes = [
    "holistic in nature and involves",
    "cognitive, affective, emotional, social and physical",
    "Verhoef et al. (2009, p. 32) explicitly",
]
```

### 3. 添加高亮注释

```python
import fitz
import os

def add_hl(page, needle, color=(1.0, 0.9, 0.3), opacity=1.0, max_n=3):
    n = 0
    for r in page.search_for(needle)[:max_n]:
        annot = page.add_highlight_annot(r)
        annot.set_colors(stroke=color)
        annot.set_opacity(opacity)
        annot.update()
        n += 1
    return n

doc = fitz.open(pdf_path)
n = 0
for pno in range(min(5, len(doc))):  # 限定页码
    page = doc[pno]
    for kw in key_quotes:
        n += add_hl(page, kw, color=(1.0, 0.9, 0.3), max_n=2)
doc.save(out_path, garbage=4, deflate=True, clean=True)
doc.close()
```

### 4. 验证高亮覆盖

```python
# 必须验证：抽几个高亮 rect 出来，确认文本确实是引文对应的原文
doc = fitz.open(out_path)
for pno in range(len(doc)):
    page = doc[pno]
    for a in list(page.annots())[:5]:
        t = page.get_text("text", clip=a.rect).strip()[:100]
        if t:
            print(f"  | {t}")
doc.close()
```

如果验证发现关键词"命中"但匹配到错误位置（如同名术语在别处出现），缩小关键词或限定 max_n。

## 关键技术点

### 智能引号与换行

PyMuPDF 的 `page.search_for(needle)` 是字符级搜索，对以下情况不鲁棒：
- 智能引号 `\u2019` (curly apostrophe) vs ASCII `'`
- 连字 `fi` (\ufb01) vs "fi"
- 跨行换行：PDF 提取的文本中 `holistic in nature and` 可能被分成
  `holistic in\nnature and`，导致 search_for 失败

**解法**：
- 关键词只用 ASCII 字符，不带撇号
- 关键词不超过一行长度（避免跨换行）
- 对极特殊情况可用 `get_text("words")` 拼接 rect，再对每个 word 单独匹配

### 高亮颜色

- 黄色 `(1.0, 0.9, 0.3)` 是最常用的"荧光笔"色
- 设置 `set_opacity(1.0)` 表示完全不透明
- 如果 PDF 有彩色插图，可用半透明（0.5）让原图透出

### 排除参考文献

```python
text = page.get_text()
# 参考文献页通常以 "References" 标题开头 + 大量 "Author (Year)" 格式
if 'References' in text[:200] and 'Aaker' in text:  # 改用具体作者名
    continue
```

或更严格：只看页面前 30% 的页码（参考文献通常在最后 1/3）。

### 输出路径规范

- 输出文件加 `_highlighted` 后缀：`xxx_highlighted.pdf`
- 输出到当前工作目录或用户指定的位置
- 不要覆盖原 PDF

## 已知陷阱

1. **scan OCR 文档**：扫描版书刊的 PDF 提取文本常有空格错位、单字成行。
   关键词要短（5-10 字符）且不依赖完整短语。

2. **max_n 失控**：通用词如"servicescape"、"customer experience"全文 30+ 处，
   一定要用 `max_n=2~3` 限制每关键词匹配次数，避免整页变黄。

3. **MuPDF xref warning**：某些老 PDF 的 xref 表损坏，添加注释时可能报
   `MuPDF error: format error: cannot find object in xref`——这是非致命警告，
   文件仍能保存，PDF 阅读器可正常打开。

4. **第一篇常对不上**：用户给的引文对应的"经典出处"和实际 PDF 不一致的情况
   经常发生（如 Shostack 1984 服务蓝图 vs Surprenant 1987 服务接触）。发现第一篇
   对应不上时，立即告诉用户并提供正确引用建议。

5. **注释"not bound to any page"**：`doc[pno].add_highlight_annot(rect)` 把注释
   绑在临时 Page 对象上，下一次循环重建 `doc[pno]` 时临时对象被回收，注释随之
   失效——保存的 PDF 里一处高亮都没有，或循环中途报
   `FzErrorArgument: annotation not bound to any page`。
   **解法**：先 `page = doc[pno]` 存入变量，在同一次迭代里完成 add + set_colors +
   update。本仓库 CLI 已按此写法实现。

## 与其他 skill 的关系

- 不需要联网，纯本地 PDF 处理
- 与 `paper-finder` 互补：finder 找 PDF，本 skill 标注 PDF
- 与 `citation-manager` 互补：manager 写参考文献，本 skill 标引文出处
