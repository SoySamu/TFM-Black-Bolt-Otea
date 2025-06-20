import boto3
from langdetect import detect
from deep_translator import GoogleTranslator
import fitz  # PyMuPDF

s3_client = boto3.client('s3')

def translate_pdf(event, context):
    input_key = event['input_key']
    output_key = event['output_key']
    bucket_name = event['bucket_name']
    target_language = event['target_language']

    local_input_filename = "/tmp/" + input_key
    local_output_filename = "/tmp/" + output_key
    s3_client.download_file(bucket_name, input_key, local_input_filename)

    doc = fitz.open(local_input_filename)
    sample_text = doc[0].get_text("text")
    detected_language = detect(sample_text)

    nuevo_pdf = fitz.open()
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if detected_language != target_language:
            translator = GoogleTranslator(source=detected_language, target=target_language)
            translated_text = translator.translate(text)
        else:
            translated_text = text
        nueva_pagina = nuevo_pdf.new_page(width=page.rect.width, height=page.rect.height)
        nueva_pagina.insert_text((50, 50), translated_text, fontname="Times-Roman", fontsize=12, color=(0, 0, 0))
    nuevo_pdf.save(local_output_filename)
    s3_client.upload_file(local_output_filename, bucket_name, output_key)
    return {"statusCode": 200, "body": f"PDF traducido subido a S3 con clave: {output_key}"}