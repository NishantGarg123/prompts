# prompts

## First replace the name of the email that wants to run.
In the file ->test_email_process.py


## Run the code using 
pytest -s -v test_email_process.py

## Flow Working
* When we run the above command then firstly our 'test_email_process.py' file runs in this we simply read the email (Subject, body, Attachments) then pass the email sub and body in the 'process_email_with_openai' function present in the 'openai_process.py' file.
* This return the JE if available in the body. else me run 'process_attachment_with_openai' function that process the attachment.


