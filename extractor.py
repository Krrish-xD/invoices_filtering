import re

def parse_invoice_text(text):
    """
    Parses the raw text from a Stripe invoice page (Ctrl+A copy) and extracts
    structured data fields including status, dates, and the description table.
    """
    data = {}

    # 1. Invoice Number (looks like 1RJXXWRK-0009)
    inv_match = re.search(r'\b([A-Z0-9]+-\d{4})\b', text)
    data['invoice_number'] = inv_match.group(1) if inv_match else "N/A"

    # 2. Status
    status_match = re.search(r'\b(Void|Open|Paid|Draft|Uncollectible)\b', text)
    data['status'] = status_match.group(1) if status_match else "Unknown"

    # 3. Billed To Info
    billed_match = re.search(r'Billed to\s+(.*?)(?:\s+·|\n|$)', text)
    data['billed_to_name'] = billed_match.group(1).strip() if billed_match else "N/A"
    
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    data['billed_to_email'] = email_match.group(0) if email_match else "N/A"

    # 4. Financials
    total_match = re.search(r'^Total\s*\n\s*(\$[\d,]+\.\d{2})', text, re.MULTILINE)
    data['total_amount'] = total_match.group(1) if total_match else "N/A"

    curr_match = re.search(r'Currency\n(.+)', text)
    data['currency'] = curr_match.group(1).strip() if curr_match else "N/A"

    # 5. ID & Links
    id_match = re.search(r'\b(in_[a-zA-Z0-9]+)\b', text)
    data['internal_id'] = id_match.group(1) if id_match else "N/A"

    link_match = re.search(r'(https://invoice\.stripe\.com/i/[^\s]+)', text)
    data['payment_page'] = link_match.group(1) if link_match else "N/A"

    # 6. Dates (Dynamic Parsing)
    dates = {}
    
    # Define mapping of keys to regex patterns
    date_patterns = {
        'Created': r'Created\n(.+)',
        'Finalized': r'Finalized\n(.+)',
        'Due': r'Due date\n(.+)',
        'Voided': r'Invoice was voided\n(.+)',
        'Sent': r'Invoice was sent.*?\n(.+)'
    }
    
    for key, pattern in date_patterns.items():
        match = re.search(pattern, text)
        if match:
            dates[key] = match.group(1).strip()
            
    data['dates'] = dates

    # 7. Description Table Parsing
    start_marker = re.search(r'Description\s*\n\s*Qty\s*\n\s*Unit price\s*\n\s*Amount', text)
    end_marker = re.search(r'\nSubtotal', text)

    items = []
    if start_marker and end_marker:
        start_idx = start_marker.end()
        end_idx = end_marker.start()
        
        table_text = text[start_idx:end_idx].strip()
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
        # Sort keys to have a consistent order (Created first, etc.)
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
    
    return "\n".join(lines)

if __name__ == "__main__":
    # Test with sample files
    import sys
    
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
