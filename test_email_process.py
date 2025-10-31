import sys, os
sys.path.append(os.path.dirname(__file__))
import json
import pytest
from email_reader import read_eml
# from openai_processor import process_email_with_openai, process_attachment_with_openai
from openai_process import process_email_with_openai, process_attachment_with_openai

import pandas as pd

@pytest.mark.parametrize("eml_file", ["test_data/Davenport Lease Reclass - October 2025.eml"])
def test_email_processing(eml_file):
    subject, body, attachments = read_eml(eml_file)

    #process email via OpenAI
    response_json = process_email_with_openai(subject, body)
    
    #validation logic
    valid = (
        "NO_JOURNAL_ENTRY_IN_BODY" not in str(response_json)
    )
    if valid:
        attachment_json = response_json
        assert "NO_JOURNAL_ENTRY_IN_BODY" not in str(response_json), "JE not in body"
    else:
        assert attachments, "No attachments found for fallback"
        # --- Read the first Excel attachment (.xlsx) ---
        attachment_path = attachments[0]
        # Load workbook
        workbook = pd.ExcelFile(attachment_path)
        
        # Pick matched sheet or first sheet (same logic as your JS)
        sheet_name = None
        matched_sheet = 'Monthly JE'  # You can set dynamically if needed

        if matched_sheet and matched_sheet in workbook.sheet_names:
            sheet_name = matched_sheet
        else:
            sheet_name = workbook.sheet_names[0]
            
        # Read the sheet into a DataFrame
        df = pd.read_excel(workbook, sheet_name=sheet_name, dtype=str, header=None).fillna("")

        # Clean each cell: remove newlines, trim spaces, collapse multiple spaces
        df = df.applymap(
            lambda x: " ".join(str(x).replace("\n", " ").split())
        )

        # Remove fully empty rows (optional)
        df = df[df.apply(lambda r: any(str(c).strip() != "" for c in r), axis=1)]

        # Convert to array-of-arrays like in n8n
        non_empty_rows = df.values.tolist()

        # --- Now send this structured data to OpenAI ---
        prompt_input = json.dumps(non_empty_rows)
        attachment_json = process_attachment_with_openai(prompt_input)

        # # --- Run same checks as before ---  
        assert "description" in attachment_json, "Missing 'description' in attachment response"
        assert "amount" in attachment_json, "Missing 'amount' in attachment response"
    # Save the response JSON
    json_dir = "test_data/json"
    os.makedirs(json_dir, exist_ok=True)

    # Get base name (without extension)
    base_name = os.path.splitext(os.path.basename(eml_file))[0]
    json_path = os.path.join(json_dir, f"{base_name}.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(attachment_json, f, indent=2, ensure_ascii=False)

    print(f"Saved OpenAI response to: {json_path}")