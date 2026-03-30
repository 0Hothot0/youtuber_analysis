#!/usr/bin/env python3
"""
將方法論 Markdown 文件轉換為 Word 文檔
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import re

def read_markdown(file_path):
    """讀取 Markdown 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def parse_markdown_to_word(md_content):
    """將 Markdown 內容轉換為 Word 文檔"""
    doc = Document()

    # 設定預設字體
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)

    # 處理中文字體
    from docx.oxml.ns import qn
    style.element.rPr.rFonts.set(qn('w:eastAsia'), '標楷體')

    lines = md_content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # 跳過空行
        if not line:
            i += 1
            continue

        # 處理標題
        if line.startswith('# '):
            # 一級標題
            text = line[2:].strip()
            heading = doc.add_heading(text, level=1)
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

        elif line.startswith('## '):
            # 二級標題
            text = line[3:].strip()
            doc.add_heading(text, level=2)

        elif line.startswith('### '):
            # 三級標題
            text = line[4:].strip()
            doc.add_heading(text, level=3)

        elif line.startswith('#### '):
            # 四級標題
            text = line[5:].strip()
            doc.add_heading(text, level=4)

        # 處理程式碼區塊
        elif line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1

            # 加入程式碼段落（使用等寬字體）
            code_text = '\n'.join(code_lines)
            para = doc.add_paragraph(code_text)
            para.style = 'Normal'
            for run in para.runs:
                run.font.name = 'Courier New'
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(0, 0, 128)

        # 處理表格
        elif line.startswith('|') and '|' in line:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            i -= 1

            # 移除分隔線（如 |---|---|）
            table_lines = [l for l in table_lines if not re.match(r'\|[\s\-:]+\|', l)]

            if table_lines:
                # 解析表格
                rows = []
                for line in table_lines:
                    cells = [cell.strip() for cell in line.split('|')[1:-1]]
                    rows.append(cells)

                # 創建表格
                if rows:
                    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
                    table.style = 'Light Grid Accent 1'

                    for row_idx, row_data in enumerate(rows):
                        for col_idx, cell_data in enumerate(row_data):
                            cell = table.rows[row_idx].cells[col_idx]
                            cell.text = cell_data

                            # 標題行加粗
                            if row_idx == 0:
                                for paragraph in cell.paragraphs:
                                    for run in paragraph.runs:
                                        run.bold = True

        # 處理列表
        elif line.startswith('- ') or line.startswith('* '):
            text = line[2:].strip()
            doc.add_paragraph(text, style='List Bullet')

        elif re.match(r'^\d+\.\s', line):
            # 數字列表
            text = re.sub(r'^\d+\.\s', '', line).strip()
            doc.add_paragraph(text, style='List Number')

        # 處理分隔線
        elif line == '---':
            doc.add_paragraph('─' * 80)

        # 處理粗體和行內程式碼
        elif line:
            # 處理粗體文字
            para = doc.add_paragraph()

            # 簡單處理：先找所有 **text** 和 `code`
            parts = re.split(r'(\*\*.*?\*\*|`.*?`)', line)

            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    # 粗體
                    run = para.add_run(part[2:-2])
                    run.bold = True
                elif part.startswith('`') and part.endswith('`'):
                    # 行內程式碼
                    run = para.add_run(part[1:-1])
                    run.font.name = 'Courier New'
                    run.font.size = Pt(11)
                    run.font.color.rgb = RGBColor(128, 0, 0)
                else:
                    para.add_run(part)

        i += 1

    return doc

def main():
    """主程式"""
    print("="*80)
    print("將方法論 Markdown 轉換為 Word 文檔")
    print("="*80)

    input_file = 'docs/CLAUDE_CODE_METHODOLOGY.md'
    output_file = 'docs/CLAUDE_CODE_METHODOLOGY.docx'

    print(f"\n讀取: {input_file}")
    md_content = read_markdown(input_file)

    print("轉換中...")
    doc = parse_markdown_to_word(md_content)

    print(f"儲存: {output_file}")
    doc.save(output_file)

    print("\n✓ 完成！")
    print(f"Word 文檔已生成: {output_file}")
    print("="*80)

if __name__ == '__main__':
    main()
