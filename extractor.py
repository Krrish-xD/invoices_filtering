import re

def split_into_blocks(text):
    """
    Splits the raw text into logical blocks based on headers.
    Returns a dictionary of block_name -> content.
    """
    blocks = {}
    
    # Define primary markers for block starts
    # Pattern: (block_name, regex_for_start_of_block)
    # Order is not strictly important for this approach, as we sort by position.
    primary_markers = [
        ('recent_activity', r'^Recent activity'),
        ('summary', r'^Summary\n'),
        ('description', r'^Description\s*\n\s*Qty'),
        ('payments', r'^Payments'),
        ('logs', r'^Logs'),
        ('events', r'^Events'),
        ('details', r'^Details\nID'),
        ('metadata', r'^Metadata'),
        # ('footer_kapsel', r'^Kastle AI') # REMOVED: Caused false positive with line items
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
    # The 'Details' block might be followed by 'Metadata', 'Kastle AI', or end of file
    details_start_match = re.search(r'Details\nID', text, re.IGNORECASE | re.DOTALL)
    if details_start_match:
        potential_details_block = text[details_start_match.start():].strip()
        
        # Find next major header after 'Details' within this potential block
        next_header_match = re.search(r'\n(Kastle AI|Developers|Metadata)', potential_details_block, re.IGNORECASE)
        if next_header_match:
            blocks['details'] = potential_details_block[:next_header_match.start()].strip()
        else:
            blocks['details'] = potential_details_block.strip() # Go till end if no subsequent header
            
    return blocks


def parse_invoice_text(text):
    """
    Parses the raw text from a Stripe invoice page (Ctrl+A copy) using block-based extraction.
    """
    blocks = split_into_blocks(text)
    data = {}
    
    # --- 1. Header & Global Parsing (Status, Total, Link) ---
    # Status can be floating, so check globally
    status_match = re.search(r'\b(Void|Open|Paid|Draft|Uncollectible)\b', text, re.IGNORECASE)
    data['status'] = status_match.group(1).title() if status_match else "Unknown"
    
    # Total Amount (can be in header or description section, best to check globally)
    total_match = re.search(r'Total\s*\n\s*(\$[\d,]+\.\d{2})', text, re.MULTILINE)
    data['total_amount'] = total_match.group(1) if total_match else "N/A"
    
    # Payment Page Link (often in header)
    link_match = re.search(r'(https://invoice\.stripe\.com/i/[^\s]+)', text)
    data['payment_page'] = link_match.group(1) if link_match else "N/A"

    # --- 2. Summary Block Parsing (Invoice #, Due Date, Billed To, Currency) ---
    summary_text = blocks.get('summary', '')
    
    # Invoice Number
    inv_match = re.search(r'Invoice number\n([A-Z0-9]+-\d{4,})', summary_text, re.IGNORECASE)
    data['invoice_number'] = inv_match.group(1) if inv_match else "N/A"
    
    # Due Date
    due_match = re.search(r'Due date\n(.+)', summary_text, re.IGNORECASE)
    if due_match:
        data['due_date'] = due_match.group(1).strip().replace(',', ' ')
    else:
        data['due_date'] = "N/A"
        
    # Billed To Email
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', summary_text)
    data['billed_to_email'] = email_match.group(0) if email_match else "N/A"
    
    # Billed To Name - "Billed to" in summary block has newline before name
    billed_match = re.search(r'Billed to\n(.+)', summary_text, re.IGNORECASE)
    data['billed_to_name'] = billed_match.group(1).strip() if billed_match else "N/A"
    
    # Currency
    curr_match = re.search(r'Currency\n(.+)', summary_text)
    data['currency'] = curr_match.group(1).strip() if curr_match else "N/A"

    # --- 3. Details Block Parsing (ID, Dates) ---
    details_text = blocks.get('details', '')
    
    # Internal ID
    id_match = re.search(r'ID\n(in_[a-zA-Z0-9]+)', details_text)
    data['internal_id'] = id_match.group(1) if id_match else "N/A"
    
    # Dates from Details Block
    dates = {}
    # We explicitly look for these keys in the Details block
    target_dates = ['Created', 'Finalized', 'Voided'] # 'Paid' removed as it's not a date here. 
    
    for key in target_dates:
        # Regex: Key followed by newline, then value
        match = re.search(rf'{key}\n(.+)', details_text, re.IGNORECASE)
        if match:
            raw_date = match.group(1).strip()
            dates[key] = raw_date.replace(',', ' ') # Clean commas
            
    # Add Due Date to dates dict for consistency in output if not N/A
    if data['due_date'] != 'N/A':
        dates['Due'] = data['due_date']
        
    data['dates'] = dates

    # --- 4. Description Block (Line Items) ---
    desc_text = blocks.get('description', '')
    items = []
    
    # Restoring the original logic for line item parsing
    start_marker = re.search(r'Description\s*\n\s*Qty\s*\n\s*Unit price\s*\n\s*Amount', desc_text, re.IGNORECASE)
    end_marker = re.search(r'\nSubtotal', desc_text, re.IGNORECASE)
    
    if start_marker and end_marker:
        start_idx = start_marker.end()
        end_idx = end_marker.start()
        
        # Ensure we are only grabbing text BETWEEN the markers
        table_text = desc_text[start_idx:end_idx].strip()
        lines = [line.strip() for line in table_text.split('\n') if line.strip()]
        
        chunk_size = 5
        for i in range(0, len(lines), chunk_size):
            chunk = lines[i:i+chunk_size]
            if len(chunk) == 5:
                item = {
                    'description': chunk[0],
                    'period': chunk[1],
                    'qty': chunk[2],
                    'unit_price': chunk[3],
                    'amount': chunk[4]
                }
                items.append(item)
    
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
    
    # Row 4: IDs
    lines.append(f"Internal ID, {data['internal_id']}, Payment Link, {data['payment_page']}")
    
    lines.append("")
    lines.append("IMPORTANT DATES")
    
    # Dynamic Date Table
    if data['dates']:
        # Sort keys to have a consistent order
        preferred_order = ['Created', 'Finalized', 'Sent', 'Due', 'Voided'] # 'Paid' removed from order
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
    lines.append("") # Extra newlines as requested
    
    return "\n".join(lines)

if __name__ == "__main__":
    # Test with sample files
    files = ['sample1.txt', 'sample2.txt', 'sample3.txt']
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
