import os
from openai import OpenAI
import json
import re
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


def clean_and_parse_openai_response(content: str):
    """
    Clean OpenAI response text and safely parse JSON.
    Equivalent to the n8n JavaScript logic you shared.
    """

    # Step 1 — Remove markdown-style code fences
    json_string = re.sub(r"^```json\s*", "", content.strip(), flags=re.IGNORECASE)
    json_string = re.sub(r"```$", "", json_string.strip(), flags=re.IGNORECASE)

    # Step 2 — Try parsing JSON
    try:
        parsed = json.loads(json_string)
    except Exception as err:
        raise ValueError(f"Failed to parse JSON: {err}\nRaw content:\n{content}")

    # Step 3 — Always return a list (even if single object)
    if isinstance(parsed, list):
        return parsed
    else:
        return [parsed]


def process_email_with_openai(subject, body):
    """Sends subject + body to OpenAI for processing and parses response JSON."""
    user_prompt = f"""Input JSON:\n
    Email subject: {subject}
    Email body: {body}
    """

    system_prompt = "You are a journal entry extraction assistant.\n\nYour task is to analyze the input text and extract all valid journal entries.\n\nEach journal entry must include:\n- An amount\n- A debit account number\n- A credit account number\n- A short description summarizing the entry\n- A date\n\nRules:\n- Only extract entries where amount, debit account, and credit account are clearly present.\n- If a full date (e.g., which have date,month,year) is present, use it in YYYY-MM-DD format(Use this date not last date of that month in this case.).\n- If only a month and year are found (e.g., May 2025), set the date as the last day of that month (e.g., 2025-05-31).\n- If no date or month is found, set the date as null.\n- Do not guess missing values.\n- Ignore totals, headers, summaries, or incomplete rows.\n\nYour task is to extract all journal entry rows that contain an account number and either a debit or credit amount (not necessarily both).\n\nFor each row:\n- Extract the `account` field never null.Account number format (eg - 15010-110-02).\n- Extract `amount` and whether it is a `debit` or `credit`.\n- Extract `description` if available in the row.\n Journal entries either in the column format (credit and debit field define then below contain the information) or in the row format (with in the same row credit key and the value in front of that similarly for the debit and amount. But in this case the amount will be pass to the both entries debit and credit).\nAlways remember about the amount that if amount  find separately for debit and credit entry then use as it is, otherwise for the debit and credit use same amount.\n\nOutput each row in this format:\n```\n{\n  \"date\": \"value or null\",\n  \"description\": \"text or null\",\n  \"amount\": extracted amount,\n  \"account\": \"account number\",\n  \"type\": \"debit\" or \"credit\"\n}\n```\n\nDo not group entries. Do not try to match debits and credits. Just return all individual rows with account + amount + type.\n\n If no journal entries are found but a date (or month/year) is available, return:\n```\n{\n  \"date\": \"YYYY-MM-DD\",\n  \"message\": \"NO_JOURNAL_ENTRY_IN_BODY\"\n}\n```\n- If no entries and no date are found, return:\n```\n{\n  \"date\": null,\n  \"message\": \"NO_JOURNAL_ENTRY_IN_BODY\"\n}\n```\nOnly return valid results, and no extra explanation or notes."


    # Send to OpenAI (exact same structure as your n8n JSON)
    response = client.chat.completions.create(
        model="gpt-4.1",  # same model
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    text = response.choices[0].message.content.strip()
    # return clean_and_parse_openai_response(text)
    return text


def process_attachment_with_openai(attachment_content):
    """Alternative processing if the email body fails validation."""
    user_prompt = f"Input JSON:\n{attachment_content}"
    system_prompt = "You are a journal entry extraction assistant. You are given array from an Excel sheet. These array are formed row wise from the spreadsheet now you have to analyse this in the horizontal format of row (make the layer of the array to get the actual xl sheet view first layer means first array, similarly for other array). \nFor a empty cell there is an empty entry in the array.\n\nStep-1 :-\nfirstly analyse the Journal entries are in the row format or in the column format using the below information. For the Journal entry only, that can be identify by the some keywords like credit, debit or amount.\n\nNote:- Journal Entry may have \n- **One-to-Many**: One account debited, multiple accounts credited (or vice versa)\n- **Many-to-One**: Multiple accounts debited, one account credited\n- **One-to-One**: Single account debited, single account credited\n- **Many-to-Many**: Multiple accounts debited, multiple accounts credited\n\nThere can be two cases in the entry Format :-\n1.Journal entry in the column format:-\n - If a column start with the title like 'credit' then the all other below array on that column contain the credit until there is other title not define for that column (similarly for debit).\n If there is the entry in the credit then debit may be 0 or empty, similarly for debit..\n\n\n2.Journal entry in the Row format:-\n - If the journal entry in the row format then the one journal entry detail (either debit or credit or amount)  will find in one array. then the below array will contain the information related to that journal entry ( like amount).\n\nStep-2 :-\n\nTasks :-\n1.If Journal entry in the column format then :- There will be a individual amount for each.\n2.If Journal entry in the row format then :- There is the single amount need to assign both entry (debit and credit).\n\nRule:-\n\n 1.Your task is to extract all journal entry rows that contain an account number and either a debit or credit amount.\n\n\n 2.For each entry:\n- Extract the `account` field never null. If it's already in format like `15060-000-02` or `01-15060-000-02`, use as-is. If not, construct it using: `Account#-Dept#-Div#`.\n\n- 3.Extract `amount` if have the account number and whether it is a `debit` or `credit`.\n Do not extract any row where the account number is missing but amounts are present — treat those as summary rows, not journal entries.\n\n- 4.Extract `description` if available in the row.\n\n- 5.Extract `date` only from a field labeled `Date:` (keep Excel serial or YYYY-MM-DD format as-is). Otherwise, set to null.\n\n- 6.Always remember about the amount that if amount find separately for debit and credit entry then use as it is, otherwise for the debit and credit use same amount.\nStep-3 :- Journal Entry Grouping and ID Extraction\n\n- Each Journal Entry (JE) block begins with a line like \"JE 3\", \"JE 4\", etc.\n- The line immediately below often contains a description like \"Record Inbound Freight - WIP\".\n- All subsequent rows with account, debit, or credit data belong to that JE until the next \"JE\" line appears or until the section ends.\n\nFor every extracted journal entry row:\n- Extract only the numeric part of the JE identifier (for example, from \"JE 3\" extract 3).\n- Include this numeric value as \"Jnlidn\".\n- If no explicit JE is found, set \"Jnlidn\": null. \n\n\n\nOutput each row in this format:\n```\n{\n  \"date\": \"value or null\",\n  \"Jnlidn\",\n  \"description\": \"text or null\",\n  \"amount\": extracted amount,\n  \"account\": \"account number\",\n  \"type\": \"debit\" or \"credit\"\n}\n```\n\nDo not group entries. Do not try to match debits and credits. Just return all individual rows with account + amount + type.\nIf there is a total written of the journal entries then ignore that do not make entry of the total.\n if the amount are zero or not available then do not include this entry also.\n  Only return the extracted journal entry objects in the exact JSON format specified."
    
    # Send to OpenAI (exact same structure as your n8n JSON)
    response = client.chat.completions.create(
        model="gpt-4.1",  # same model
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )


    text = response.choices[0].message.content.strip()
    return clean_and_parse_openai_response(text)
