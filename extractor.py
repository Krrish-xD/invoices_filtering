import re

def split_into_blocks(text):
    """
    Splits the raw text into logical blocks based on headers.
    Returns a dictionary of block_name -> content.
    """
    blocks = {}
    
    # Define primary markers for block starts
    # Pattern: (block_name, regex_for_start_of_block)
    # relaxed to allow optional leading whitespace
    primary_markers = [
        ('recent_activity', r'^\s*Recent activity'),
        ('summary', r'^\s*Summary\s*$'),
        ('description', r'^\s*Description\s*\n\s*Qty'),
        ('payments', r'^\s*Payments'),
        ('logs', r'^\s*Logs'),
        ('events', r'^\s*Events'),
        ('details', r'^\s*Details\s*\n\s*ID'),
        ('metadata', r'^\s*Metadata'),
    ]
    
    # Collect all marker positions and their names
    positions_with_names = []
    for name, pattern in primary_markers:
        # Use finditer to find all occurrences if a pattern might repeat
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            positions_with_names.append((match.start(), name))
            
    # Sort markers by their starting position
    positions_with_names.sort(key=lambda x: x[0])
    
    # Add a pseudo-marker for the very beginning of the text
    full_markers_list = [(0, 'header')] + positions_with_names
    
    # Iterate through the sorted markers to define block boundaries
    for i in range(len(full_markers_list)):
        start_idx, block_name = full_markers_list[i]
        
        # The end of the current block is the start of the next block, or end of text
        if i + 1 < len(full_markers_list):
            end_idx = full_markers_list[i+1][0]
        else:
            end_idx = len(text) # Last block goes to the end
            
        blocks[block_name] = text[start_idx:end_idx].strip()
        
    # --- Refine Details block ending ---
    details_start_match = re.search(r'Details\s*\n\s*ID', text, re.IGNORECASE | re.DOTALL)
    if details_start_match:
        potential_details_block = text[details_start_match.start():].strip()
        
        # Find next major header after 'Details' within this potential block
        next_header_match = re.search(r'\n(Kastle AI|Developers|Metadata)', potential_details_block, re.IGNORECASE)
        if next_header_match:
            blocks['details'] = potential_details_block[:next_header_match.start()].strip()
        else:
            blocks['details'] = potential_details_block.strip()
            
    return blocks


def parse_invoice_text(text):
    """
    Parses the raw text from a Stripe invoice page (Ctrl+A copy) using block-based extraction
    with global fallbacks.
    """
    blocks = split_into_blocks(text)
    data = {}
    
    # --- Helper: extract with fallback ---
    
    # --- Helper: extract with fallback ---
    def extract_field(regex, block_name, global_fallback=True):
        # 1. Try block
        block_content = blocks.get(block_name, '')
        match = re.search(regex, block_content, re.IGNORECASE)
        if match:
            return match
            
        # 2. Try global if requested
        if global_fallback:
            match = re.search(regex, text, re.IGNORECASE)
            if match:
                return match
        return None

    # --- 1. Global Fields ---
    status_match = re.search(r'\b(Void|Open|Paid|Draft|Uncollectible)\b', text, re.IGNORECASE)
    data['status'] = status_match.group(1).title() if status_match else "Unknown"
    
    total_match = re.search(r'Total\s*\n\s*(\$[\d,]+\.\d{2})', text, re.MULTILINE)
    data['total_amount'] = total_match.group(1) if total_match else "N/A"
    
    # Payment Page Link (extracted for internal logic if needed, but not output to CSV)
    link_match = re.search(r'(https://invoice\.stripe\.com/i/[^\s]+)', text)
    data['payment_page'] = link_match.group(1) if link_match else "N/A"

    # --- 2. Summary Fields (with Global Fallback) ---
    
    # Invoice Number
    inv_match = extract_field(r'Invoice number\s*[\r\n]+([A-Z0-9-]+)', 'summary')
    data['invoice_number'] = inv_match.group(1) if inv_match else "N/A"
    
    # Due Date
    due_match = extract_field(r'Due date\n(.+)', 'summary')
    if due_match:
        data['due_date'] = due_match.group(1).strip().replace(',', ' ')
    else:
        data['due_date'] = "N/A"
        
    # Billed To Email (Global search is usually safer for emails)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    data['billed_to_email'] = email_match.group(0) if email_match else "N/A"
    
    # Billed To Name
    # This is tricky globally because "Billed to" might appear multiple times or be ambiguous.
    # We stick to block first, then try global "Billed to\nName" pattern.
    billed_match = extract_field(r'Billed to\s*\n(.+)', 'summary')
    data['billed_to_name'] = billed_match.group(1).strip() if billed_match else "N/A"
    
    # Currency
    curr_match = extract_field(r'Currency\n(.+)', 'summary')
    data['currency'] = curr_match.group(1).strip() if curr_match else "N/A"

    # --- 3. Details Fields (with Global Fallback) ---
    
    # Internal ID
    id_match = extract_field(r'ID\n(in_[a-zA-Z0-9]+)', 'details')
    data['internal_id'] = id_match.group(1) if id_match else "N/A"
    
    # Dates
    dates = {}
    target_dates = ['Created', 'Finalized', 'Voided']
    
    for key in target_dates:
        # Try finding "Key\nValue" pattern
        date_match = extract_field(rf'{key}\n(.+)', 'details')
        if date_match:
            raw_date = date_match.group(1).strip()
            dates[key] = raw_date.replace(',', ' ')
            
    if data['due_date'] != 'N/A':
        dates['Due'] = data['due_date']
        
    data['dates'] = dates

    # --- 4. Description Block (Line Items) ---
    # We strictly use the description block to avoid false positives from other tables
    desc_text = blocks.get('description', '')
    if not desc_text:
        # Fallback: try finding the header globally if block failed
        start_marker = re.search(r'Description\s*\n\s*Qty\s*\n\s*Unit price\s*\n\s*Amount', text, re.IGNORECASE)
        end_marker = re.search(r'\nSubtotal', text, re.IGNORECASE)
        if start_marker and end_marker:
             desc_text = text[start_marker.end():end_marker.start()]
    
    items = []
    # If we have text (either from block or fallback), parse it
    if desc_text:
        # Basic parsing logic assuming 5 lines per item
        # We need to be careful about not including the header itself if we grabbed it raw
        # The block logic usually excludes the start marker, but let's be safe
        
        # Clean up lines
        lines = [line.strip() for line in desc_text.split('\n') if line.strip()]
        
        # Filter out header row if present (Description, Qty...)
        if lines and lines[0].lower() == 'description':
             # Skip the 4 header lines: Description, Qty, Unit price, Amount
             lines = lines[4:] if len(lines) >= 4 else []

        chunk_size = 5
        for i in range(0, len(lines), chunk_size):
            chunk = lines[i:i+chunk_size]
            if len(chunk) == 5:
                # Basic validation: Qty should be a number or resemble one
                # to avoid parsing garbage
                items.append({
                    'description': chunk[0],
                    'period': chunk[1],
                    'qty': chunk[2],
                    'unit_price': chunk[3],
                    'amount': chunk[4]
                })
    
    data['line_items'] = items
    
    return data

def format_to_csv_block(data):
    """
    Formats the extracted dictionary into the specific multi-line CSV block string.
    """
    lines = []
    lines.append("INVOICE REPORT")
    lines.append("-" * 50)
    
    # Row 1: Basic Info
    lines.append(f"Invoice Number, {data['invoice_number']}, Status, {data['status']}")
    
    # Row 2: Billed To
    lines.append(f"Billed To, {data['billed_to_name']}, Email, {data['billed_to_email']}")
    
    # Row 3: Financials
    lines.append(f"Total Amount, {data['total_amount']}, Currency, {data['currency']}")
    
    # Row 4: IDs (Payment Link REMOVED)
    lines.append(f"Internal ID, {data['internal_id']}")
    
    lines.append("")
    lines.append("IMPORTANT DATES")
    
    # Dynamic Date Table
    if data['dates']:
        preferred_order = ['Created', 'Finalized', 'Sent', 'Due', 'Voided']
        sorted_keys = sorted(data['dates'].keys(), key=lambda k: preferred_order.index(k) if k in preferred_order else 99)
        
        header_row = ", ".join(sorted_keys)
        value_row = ", ".join([data['dates'][k] for k in sorted_keys])
        
        lines.append(header_row)
        lines.append(value_row)
    else:
        lines.append("No dates found")
        
    lines.append("")
    lines.append("LINE ITEMS")
    lines.append("Description, Period, Qty, Unit Price, Amount")
    
    if not data['line_items']:
        lines.append("No items found or parsing failed")
    else:
        for item in data['line_items']:
            desc = item['description'].replace(',', ';')
            lines.append(f"{desc}, {item['period']}, {item['qty']}, {item['unit_price']}, {item['amount']}")
            
    lines.append("-" * 50)
    lines.append("") 
    lines.append("") 
    
    return "\n".join(lines)

if __name__ == "__main__":
    # Test with sample files
    files = ['sample1.txt', 'sample2.txt', 'sample3.txt', 'sample4.txt']
    for f_path in files:
        try:
            with open(f_path, 'r') as f:
                content = f.read()
                parsed = parse_invoice_text(content)
                print(f"--- TEST OUTPUT FOR {f_path} ---")
                print(format_to_csv_block(parsed))
                print("\n")
        except FileNotFoundError:
            print(f"Skipping {f_path} (not found)")
