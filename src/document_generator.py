from transformers import pipeline
from docx import Document

def generate_document(template_path, data):
    document = Document(template_path)
    for paragraph in document.paragraphs:
        for key, value in data.items():
            if key in paragraph.text:
                inline = paragraph.runs
                for i in range(len(inline)):
                    if key in inline[i].text:
                        inline[i].text = inline[i].text.replace(key, value if value else '')
    return document

def generate_text(prompt):
    generator = pipeline('text-generation', model='gpt-2')
    result = generator(prompt, max_length=50, num_return_sequences=1)
    return result[0]['generated_text']
