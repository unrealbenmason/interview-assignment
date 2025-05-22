import os
import csv
import base64
from openai import OpenAI
from dotenv import load_dotenv
import sys
import json
from functools import partial
import re
import fitz

json.dumps = partial(json.dumps, ensure_ascii=False)

# Load API key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
product_to_manufacturer = {}

def convert_pdf_to_base64_images(pdf_path, dpi=150):
    doc = fitz.open(pdf_path)
    base64_images = []
    zoom = dpi / 72  # 72 dpi is default
    for page_num, page in enumerate(doc, start=1):
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        img_str = base64.b64encode(img_data).decode("utf-8")
        base64_images.append((page_num, f"data:image/png;base64,{img_str}"))
    return base64_images

def call_gpt_vision_for_extraction(image_base64, page_num):
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_base64}
                        },
                        {
                            "type": "text",
                            "text": (
                                "You are a document parser for a construction product submittal PDF.\n"
                                "Extract a list of distinct product entries from this page.\n"
                                "Format: Product Name, Manufacturer Name (CSV, no header). Only include actual products.\n"
                                "Each product must include a model number if present, and a clear descriptive name.\n"
                                "The manufacturer should be inferred from the page layout or branding, not just who submitted the document.\n"
                                "Avoid listing features or internal specs as separate products.\n"
                                f"Example: DX08QGP Roof & Wall Exhaust Fan,PennBarry"
                            )
                        }
                    ]
                }
            ],
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ GPT Vision API error on page {page_num}: {e}")
        return ""

def parse_gpt_response(response, page_num):
    results = []
    for line in response.strip().splitlines():
        if not line or "," not in line:
            continue

        if any(phrase in line.lower() for phrase in [
            "there are no specific product entries",
            "the image provided does not contain",
            "cover page", "submittal data", "detailed information"
        ]):
            continue

        parts = [p.strip() for p in line.split(",", 1)]
        if len(parts) != 2:
            continue

        prod, manu = parts

        if re.fullmatch(r'[A-Z]{2}-\d|EF-\d|Product Data.*', prod, re.IGNORECASE):
            continue
        if not re.search(r'\d', prod):
            continue

        results.append((prod, manu, page_num))
    return results




def clean_cell(value):
    value = value.strip()
    value = re.sub(r'^["“”‘’]+|["“”‘’]+$', '', value)  # remove surrounding quotes
    value = value.replace('"', '').replace("'", '')    # remove internal quotes
    value = re.sub(r'\s+', ' ', value)  # normalize whitespace
    return value

def extract_actual_manufacturer(raw_value):
    # Get the last comma-separated segment as manufacturer name
    parts = [part.strip() for part in raw_value.split(',')]
    return parts[-1] if parts else "Unspecified Manufacturer"

def save_to_csv(output_path, rows):
    seen = set()
    clean_rows = []

    for prod, manu, page in rows:
        prod_clean = clean_cell(prod)

        # Normalize and extract actual manufacturer from trailing part
        manu_clean_raw = clean_cell(manu)
        manu_clean = extract_actual_manufacturer(manu_clean_raw)

        if not manu_clean:
            manu_clean = "Unspecified Manufacturer"

        key = (prod_clean.lower(), manu_clean.lower())
        if key not in seen:
            seen.add(key)
            clean_rows.append((prod_clean, manu_clean, page))
        else:
            print(f"🔁 Duplicate skipped: {prod_clean} / {manu_clean}")

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["product_name", "manufacturer", "page_number"])
        for row in clean_rows:
            writer.writerow(row)




def extract_products_with_vision(pdf_path):
    all_results = []
    base64_images = convert_pdf_to_base64_images(pdf_path)
    for page_num, image_data in base64_images:
        print(f"📄 Processing page {page_num}...")
        gpt_response = call_gpt_vision_for_extraction(image_data, page_num)
        parsed = parse_gpt_response(gpt_response, page_num)
        all_results.extend(parsed)
    return all_results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_products.py input/yourfile.pdf")
        exit(1)

    input_pdf = sys.argv[1]
    output_csv = os.path.join("output", os.path.basename(input_pdf).replace(".pdf", ".csv"))
    os.makedirs("output", exist_ok=True)

    results = extract_products_with_vision(input_pdf)
    save_to_csv(output_csv, results)
    print(f"✅ Saved {len(results)} unique rows to {output_csv}")
