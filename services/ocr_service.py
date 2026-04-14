# OCR service: extract text from bill images and parse fertilizer items
import re
import os
from pathlib import Path

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def extract_text_from_image(image_path):
    """Run OCR on image and return raw text lines."""
    if not HAS_EASYOCR:
        # Fallback: return placeholder so UI still works (e.g. add sample line)
        return ['Sample line - Install easyocr for real OCR: Urea 50 kg 1200.00']
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    result = reader.readtext(str(image_path), detail=0)
    return [line.strip() for line in result if line.strip()]

def parse_fertilizer_lines(lines):
    """
    Parse OCR lines into list of { name, quantity, price_per_unit, total_price }.
    Heuristics:
    - Ignore header/footer text and lines without any letters.
    - If a line has letters but no numbers: treat as product name only (user can fill qty/price).
    - If a line has both letters and numbers: try to extract qty and price from the numbers.
    """
    items = []
    in_items_section = False
    # Patterns: quantity often in kg/bags, price as number with . or ,
    qty_pattern = re.compile(r'\b(\d+(?:\.\d+)?)\s*(?:kg|kgs|bag|bags|qtl|qtls)?\b', re.I)
    price_pattern = re.compile(r'\b(\d+(?:[.,]\d{2})?)\s*$')
    skip_keywords = [
        'invoice', 'issue date', 'due date', 'subtotal', 'tax', 'total due',
        'payment terms', 'thank you', 'visit again', 'bill from', 'bill to',
        'description', 'qty', 'quantity', 'price', 'total', 'cash', 'notes'
    ]
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        low = line.lower()

        # Detect the start of the table section (after headers/address).
        if not in_items_section:
            # In many invoices the item table starts after a 'Date' or 'Description' header row.
            # Once we see that, start capturing subsequent lines as potential items.
            if low.strip() == 'date' or 'description' in low:
                in_items_section = True
                continue
            # Before the table starts (invoice title, address, bill from/to), skip everything.
            continue

        # Inside the items section, still skip obvious non-item keywords.
        if any(k in low for k in skip_keywords):
            continue

        has_letters = bool(re.search(r'[A-Za-z]', line))
        has_digits = bool(re.search(r'\d', line))

        # If line has no letters, it's probably a bare number cell (price/qty/total) – skip it.
        if not has_letters:
            continue

        # If there are no digits, treat as a product name only.
        if not has_digits:
            clean_name = re.sub(r'\s+', ' ', line).strip()
            if clean_name:
                items.append({
                    'name': clean_name[:255],
                    'quantity': 0,
                    'price_per_unit': None,
                    'total_price': None,
                })
            continue

        # Line has both letters and digits: try to extract quantity and price.
        qty_matches = qty_pattern.findall(line)
        price_matches = re.findall(r'\d+(?:[.,]\d{2})?', line)
        quantity = None
        price_val = None
        if qty_matches:
            try:
                quantity = float(qty_matches[0].replace(',', '.'))
            except ValueError:
                quantity = None
        if price_matches:
            try:
                # Last number often total price or price per unit; we store it as price_per_unit
                price_val = float(price_matches[-1].replace(',', '.'))
            except ValueError:
                price_val = None

        name = line
        for m in (qty_matches + price_matches):
            name = name.replace(m, '', 1)
        name = re.sub(r'\s+', ' ', name).strip()
        if not name:
            name = line[:50]
        items.append({
            'name': name[:255],
            'quantity': quantity or 0,
            'price_per_unit': price_val,
            'total_price': price_val,
        })
    return items

def parse_invoice_table(lines):
    """
    Special parser for invoice-style tables with columns:
    No | Description | Price | Qty | Total

    OCR for such tables is often like:
      '1'
      'POTASSIUM NITRATE'
      '50.00'
      '12'
      '600.00'
      '2'
      'UREA'
      '89.00'
      '10'
      '890.00'
      ...

    This parser walks through the raw OCR lines and looks for that pattern.
    """
    items = []
    in_items_section = False

    def is_number(text: str) -> bool:
        return bool(re.fullmatch(r"\d+(?:\.\d+)?", text.strip()))

    skip_keywords = ["subtotal", "tax", "total due", "payment terms", "thank you", "visit again"]

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        low = line.lower()

        # Find where item table starts
        if not in_items_section:
            if low.strip() == "date" or "description" in low:
                in_items_section = True
            i += 1
            continue

        # Stop when we hit footer / totals
        if any(k in low for k in skip_keywords) or not line:
            i += 1
            continue

        has_letters = bool(re.search(r"[A-Za-z]", line))
        has_digits = bool(re.search(r"\d", line))

        # We only consider description lines (letters, no digits)
        if has_letters and not has_digits:
            desc = line
            # Look ahead for up to 4 numeric-only lines (price, qty, total)
            nums = []
            j = i + 1
            while j < n and len(nums) < 4:
                t = lines[j].strip()
                tl = t.lower()
                if not t:
                    j += 1
                    continue
                if any(k in tl for k in skip_keywords):
                    break
                # If this line has letters as well, it's likely next description
                if re.search(r"[A-Za-z]", t):
                    break
                if is_number(t):
                    nums.append(t)
                    j += 1
                    continue
                else:
                    break

            if len(nums) >= 2:
                # Heuristic: last 2 or 3 numbers are qty and total (and maybe price)
                try:
                    if len(nums) >= 3:
                        price = float(nums[0])
                        qty = float(nums[1])
                        total = float(nums[2])
                    else:
                        # Only price and qty, compute total
                        price = float(nums[0])
                        qty = float(nums[1])
                        total = price * qty
                except ValueError:
                    # Fallback to next line
                    i += 1
                    continue

                items.append(
                    {
                        "name": desc[:255],
                        "quantity": qty,
                        "price_per_unit": price,
                        "total_price": total,
                    }
                )
                i = j
                continue

        i += 1
    return items


def process_bill_image(image_path):
    """Full pipeline: read image, OCR, parse items."""
    lines = extract_text_from_image(image_path)
    # First try the invoice-style parser; if it finds rows, use them.
    items = parse_invoice_table(lines)
    if not items:
        items = parse_fertilizer_lines(lines)
    return {'lines': lines, 'items': items}
