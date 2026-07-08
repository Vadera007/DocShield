import os
import re
import pdfplumber

def make_markdown_table(grid):
    if not grid:
        return ""
    # Clean cells: replace newlines inside cell with space, handle None
    cleaned_grid = []
    for row in grid:
        cleaned_row = []
        for cell in row:
            val = str(cell or "").strip().replace("\n", " ")
            cleaned_row.append(val)
        cleaned_grid.append(cleaned_row)
        
    headers = cleaned_grid[0]
    # Check if headers is empty or all elements are empty
    if not headers or all(x == "" for x in headers):
        # assign generic headers
        headers = [f"Col {i+1}" for i in range(len(headers))]
        cleaned_grid[0] = headers
        
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in cleaned_grid[1:]:
        # Ensure row length matches headers length by padding/trimming
        if len(row) < len(headers):
            row += [""] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = row[:len(headers)]
        markdown += "| " + " | ".join(row) + " |\n"
    return markdown

def parse_pdf(pdf_path: str) -> list[dict]:
    chunks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            
            # Find tables
            tables = page.find_tables()
            table_bboxes = [t.bbox for t in tables] # (x0, top, x1, bottom)
            
            # Extract tables as markdown grids
            for t_idx, table in enumerate(tables):
                grid = table.extract()
                if grid:
                    md_table = make_markdown_table(grid)
                    chunks.append({
                        "id": f"p{page_num}_table_{t_idx}",
                        "page": page_num,
                        "type": "table",
                        "content": md_table
                    })
            
            # Extract words and filter out those in tables
            words = page.extract_words()
            non_table_words = []
            for w in words:
                x0, top, x1, bottom = w["x0"], w["top"], w["x1"], w["bottom"]
                # Check if word falls in any table bbox
                in_table = False
                for tx0, ttop, tx1, tbottom in table_bboxes:
                    # check overlap with tolerance
                    if (x0 >= tx0 - 2 and x1 <= tx1 + 2 and 
                        top >= ttop - 2 and bottom <= tbottom + 2):
                        in_table = True
                        break
                if not in_table:
                    non_table_words.append(w)
            
            # Reconstruct lines of text by grouping words with similar 'top'
            lines = []
            if non_table_words:
                # Sort words by top position, then by x0
                non_table_words.sort(key=lambda w: (w["top"], w["x0"]))
                
                current_line = [non_table_words[0]]
                for w in non_table_words[1:]:
                    # If this word's top is close to the previous word's top, it's on the same line
                    if abs(w["top"] - current_line[-1]["top"]) < 3:
                        current_line.append(w)
                    else:
                        # Finish previous line
                        current_line.sort(key=lambda w: w["x0"])
                        lines.append(" ".join([item["text"] for item in current_line]))
                        current_line = [w]
                # Add final line
                if current_line:
                    current_line.sort(key=lambda w: w["x0"])
                    lines.append(" ".join([item["text"] for item in current_line]))
            
            page_text = "\n".join(lines).strip()
            if not page_text:
                continue
                
            # If consecutive double-newlines are absent, segment content by capitalized section headers
            has_double_newlines = "\n\n" in page_text
            
            if has_double_newlines:
                raw_segments = page_text.split("\n\n")
                for s_idx, seg in enumerate(raw_segments):
                    seg = seg.strip()
                    if seg:
                        chunks.append({
                            "id": f"p{page_num}_text_{s_idx}",
                            "page": page_num,
                            "type": "text",
                            "content": seg
                        })
            else:
                # Segment by capitalized section headers (e.g. "EXPERIENCE", "EDUCATION")
                lines_split = page_text.split("\n")
                segments = []
                current_segment_lines = []
                
                header_pattern = re.compile(r'^[A-Z\s\d\-\&]{3,40}$')
                
                for line in lines_split:
                    line_strip = line.strip()
                    # Check if line looks like a capitalized header
                    is_header = bool(header_pattern.match(line_strip)) and any(c.isalpha() for c in line_strip)
                    
                    if is_header and current_segment_lines:
                        # Store previous segment
                        segments.append("\n".join(current_segment_lines).strip())
                        current_segment_lines = [line]
                    else:
                        current_segment_lines.append(line)
                        
                if current_segment_lines:
                    segments.append("\n".join(current_segment_lines).strip())
                    
                for s_idx, seg in enumerate(segments):
                    if seg:
                        chunks.append({
                            "id": f"p{page_num}_text_{s_idx}",
                            "page": page_num,
                            "type": "text",
                            "content": seg
                        })
                        
    return chunks
