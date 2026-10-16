#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flight Radar 2.0 - Executive Architecture & Roadmap PDF Generator
Creates an editorial, publication-quality PDF report from the markdown roadmap.
"""

import os
import re
import sys
from fpdf import FPDF

MD_PATH = "/data/data/com.termux/files/home/.gemini/antigravity-cli/brain/8263420e-5b67-41f1-87f5-316d2b72a45b/flight_radar_future_roadmap.md"
OUTPUT_PDF_SDCARD = "/sdcard/Download/Flight_Radar_2.0_Raporu.pdf"
OUTPUT_PDF_LOCAL = "/data/data/com.termux/files/home/Flight_Radar_2.0_Raporu.pdf"

FONT_REGULAR = "/system/fonts/Roboto-Regular.ttf"
FONT_BOLD = "/system/fonts/DroidSans-Bold.ttf"
FONT_MONO = "/system/fonts/DroidSansMono.ttf"

class PDFReport(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=18, top=18, right=18)
        
        # Fonts
        self.add_font('Roboto', '', FONT_REGULAR)
        self.add_font('RobotoBold', '', FONT_BOLD)
        self.add_font('RobotoMono', '', FONT_MONO)
        
        self.doc_title = "FLIGHT RADAR 2.0"

    def header(self):
        if self.page_no() == 1:
            return  # First page has custom cover header
        self.set_font('RobotoBold', size=8)
        self.set_text_color(100, 116, 139) # slate-500
        self.cell(w=0, h=6, text="FLIGHT RADAR 2.0 | TEKNIK MIMARI & YOL HARITASI RAPORU", align='L')
        self.set_font('Roboto', size=8)
        self.cell(w=0, h=6, text="Antigravity & Claude Haiku", align='R', new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(18, 14, 192, 14)
        self.ln(4)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(18, 283, 192, 283)
        self.set_font('Roboto', size=8)
        self.set_text_color(148, 163, 184)
        self.cell(w=0, h=8, text=f"Sayfa {self.page_no()} / {{nb}}", align='C')

def clean_text_for_pdf(text):
    """Replaces emojis and problematic symbols with clean editorial symbols."""
    # Common emojis to clean representation
    replacements = [
        ("✈️", "[UÇUŞ]"),
        ("📌", "[ÖZET]"),
        ("🔍", "[ANALİZ]"),
        ("🔴", "[KRİTİK]"),
        ("⚡", "[PERFORMANS]"),
        ("🥊", "[MÜNAZARA]"),
        ("🚀", "[GELİŞTİRME]"),
        ("🗄️", "[DB]"),
        ("🤖", "[BOT]"),
        ("💱", "[KUR]"),
        ("🏙️", "[HUB]"),
        ("🎯", "[HEDEF]"),
        ("🛠️", "[YOL HARİTASI]"),
        ("💡", "[SONUÇ]"),
        ("✅", "[✓]"),
        ("❌", "[✗]"),
        ("🔥", "[SICAK]"),
        ("⏳", "[BEKLE]"),
        ("🚨", "[ALARM]"),
        ("📉", "[DÜŞÜŞ]"),
        ("🔗", "[LİNK]"),
        ("🇹🇷", "TR"),
        ("🇩🇪", "DE"),
        ("🇺🇸", "US"),
        ("⭐", "*")
    ]
    for emoji_str, clean_str in replacements:
        text = text.replace(emoji_str, clean_str)
    
    # Strip any remaining unmapped surrogate or high unicode characters
    # Keep Turkish Latin chars, ASCII and basic punctuation
    cleaned = []
    for ch in text:
        code = ord(ch)
        if code < 0x2500 or (0x0100 <= code <= 0x024F) or code in (0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026):
            cleaned.append(ch)
        else:
            cleaned.append(' ')
    return "".join(cleaned)

def render_markdown_to_pdf(md_text, output_path):
    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Cover Banner
    pdf.set_fill_color(15, 23, 42) # Slate 900
    pdf.rect(18, 18, 174, 34, style='F')

    pdf.set_xy(24, 23)
    pdf.set_font('RobotoBold', size=16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(w=0, h=8, text="FLIGHT RADAR 2.0", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(24)
    pdf.set_font('Roboto', size=10)
    pdf.set_text_color(203, 213, 225) # Slate 300
    pdf.cell(w=0, h=6, text="Mimari Analiz, Guvenlik Denetimi ve 10x Gelistirme Raporu", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(24)
    pdf.set_font('Roboto', size=8)
    pdf.set_text_color(148, 163, 184) # Slate 400
    pdf.cell(w=0, h=5, text="Antigravity (Sistem Mimari) & Claude Haiku (Guvenlik/QA Mufettisi) Ortak Istisare Raporu", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(58)

    lines = md_text.splitlines()
    in_code_block = False
    code_lines = []
    in_mermaid = False

    for raw_line in lines:
        line = raw_line.strip()

        # Handle mermaid blocks
        if line.startswith('```mermaid'):
            in_mermaid = True
            continue
        if in_mermaid:
            if line.startswith('```'):
                in_mermaid = False
            continue

        # Handle Code blocks
        if line.startswith('```'):
            if in_code_block:
                # Flush code block
                in_code_block = False
                pdf.set_fill_color(241, 245, 249) # slate-100
                pdf.set_draw_color(203, 213, 225)
                pdf.set_line_width(0.2)
                pdf.set_font('RobotoMono', size=8)
                pdf.set_text_color(15, 23, 42)
                
                block_text = "\n".join(code_lines)
                cleaned_block = clean_text_for_pdf(block_text)
                pdf.multi_cell(w=0, h=4.2, text=cleaned_block, border=1, fill=True, align='L')
                pdf.ln(3)
                code_lines = []
            else:
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(raw_line)
            continue

        # Skip main title (already in banner)
        if line.startswith('# '):
            continue

        # Horizontal rule
        if line.startswith('---'):
            pdf.ln(2)
            pdf.set_draw_color(226, 232, 240)
            pdf.set_line_width(0.3)
            y = pdf.get_y()
            pdf.line(18, y, 192, y)
            pdf.ln(3)
            continue

        # Headings H2
        if line.startswith('## '):
            heading_text = clean_text_for_pdf(line[3:].strip())
            pdf.ln(4)
            pdf.set_font('RobotoBold', size=13)
            pdf.set_text_color(180, 52, 30) # Terra-cotta / Dark Red
            pdf.multi_cell(w=0, h=7, text=heading_text)
            
            # Sub-rule under H2
            y = pdf.get_y()
            pdf.set_draw_color(180, 52, 30)
            pdf.set_line_width(0.5)
            pdf.line(18, y, 70, y)
            pdf.ln(3)
            continue

        # Headings H3
        if line.startswith('### '):
            heading_text = clean_text_for_pdf(line[4:].strip())
            pdf.ln(2)
            pdf.set_font('RobotoBold', size=11)
            pdf.set_text_color(15, 23, 42) # Slate-900
            pdf.multi_cell(w=0, h=6, text=heading_text)
            pdf.ln(1)
            continue

        # Blockquote / Alert
        if line.startswith('> '):
            quote_text = clean_text_for_pdf(line[2:].strip())
            pdf.ln(1)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(180, 52, 30)
            pdf.set_line_width(0.8)
            
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.set_font('Roboto', size=9)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(w=0, h=4.8, text=quote_text, fill=True)
            # Left accent bar
            new_y = pdf.get_y()
            pdf.line(18, y, 18, new_y)
            pdf.ln(2)
            continue

        # List items
        if line.startswith('- ') or line.startswith('* ') or re.match(r'^\d+\.\s', line):
            item_text = clean_text_for_pdf(re.sub(r'^(-|\*|\d+\.)\s+', '', line))
            # Format bold inside list
            pdf.set_font('Roboto', size=9.5)
            pdf.set_text_color(30, 41, 59)
            
            # Print bullet
            pdf.cell(w=5, h=5, text="•", align='R')
            pdf.multi_cell(w=0, h=5, text=" " + item_text)
            pdf.ln(0.8)
            continue

        # Empty line
        if not line:
            pdf.ln(2)
            continue

        # Standard paragraph
        para_text = clean_text_for_pdf(line)
        # Remove bold markers for clean reading
        para_text = re.sub(r'\*\*(.*?)\*\*', r'\1', para_text)
        para_text = re.sub(r'`(.*?)`', r'\1', para_text)
        
        pdf.set_font('Roboto', size=9.5)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(w=0, h=5, text=para_text)
        pdf.ln(1.5)

    # Output
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")

def main():
    if not os.path.exists(MD_PATH):
        print(f"Error: Markdown file not found at {MD_PATH}")
        sys.exit(1)

    with open(MD_PATH, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Generate in Downloads and local
    render_markdown_to_pdf(md_content, OUTPUT_PDF_SDCARD)
    render_markdown_to_pdf(md_content, OUTPUT_PDF_LOCAL)

    print("Success! Opening PDF via termux-open...")
    os.system(f"termux-open {OUTPUT_PDF_SDCARD}")

if __name__ == '__main__':
    main()
