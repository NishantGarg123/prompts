from email import policy
from email.parser import BytesParser
import os

def read_eml(file_path):
    """Reads .eml file and returns subject, body, and attachments."""
    with open(file_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    subject = msg["subject"]
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body += part.get_content()
    else:
        body = msg.get_content()

    attachments = []
    attachments_dir = os.path.join(os.path.dirname(file_path), "attachments")
    os.makedirs(attachments_dir, exist_ok=True)

    for part in msg.iter_attachments():
        filename = part.get_filename()
        if filename and filename.lower().endswith(".xlsx"):   # ✅ only .xlsx files
            path = os.path.join(attachments_dir, filename)
            with open(path, "wb") as f:
                f.write(part.get_payload(decode=True))
            attachments.append(path)

    return subject, body.strip(), attachments
