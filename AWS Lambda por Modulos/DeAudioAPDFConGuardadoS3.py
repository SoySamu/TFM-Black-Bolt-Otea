import boto3
import re
from gtts import gTTS
from PyPDF2 import PdfReader

s3_client = boto3.client('s3')

def convertir_pdf_a_audio(event, context):
    input_key = event['input_key']
    audio_key = event['audio_key']
    bucket_name = event['bucket_name']
    target_language = event['target_language']

    local_pdf = "/tmp/" + input_key
    local_audio = "/tmp/" + audio_key
    s3_client.download_file(bucket_name, input_key, local_pdf)

    reader = PdfReader(local_pdf)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()
    if texto.strip():
        frases = re.split(r'(\.|!|\?)', texto)
        texto_con_delay = " ".join([f.strip() + ". " if f in '.!?' else f.strip() for f in frases])
        tts = gTTS(text=texto_con_delay, lang=target_language)
        tts.save(local_audio)
        s3_client.upload_file(local_audio, bucket_name, audio_key)
        return {"statusCode": 200, "body": f"Archivo de audio subido a S3 con clave: {audio_key}"}
    else:
        return {"statusCode": 400, "body": "El PDF no contiene texto legible."}