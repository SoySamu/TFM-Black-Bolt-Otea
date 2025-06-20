import boto3
import json
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from langdetect import detect
from gtts import gTTS
import re
import subprocess
import os

# S3 client
s3_client = boto3.client('s3')

# Obtener texto desde una URL
def obtener_texto_web(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        div_content = soup.find('div', class_='post-body entry-content float-container')
        if div_content:
            return div_content.get_text()
        else:
            print("No se encontró el div especificado.")
            return None
    else:
        print("Error al acceder a la página:", response.status_code)
        return None

# Crear PDF y guardar en S3
def crear_pdf(texto, output_key, bucket_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    frases = texto.split('.')
    for frase in frases:
        frase = frase.strip()
        if frase:
            pdf.multi_cell(0, 10, f'{frase}.'.encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(5)
    local_filename = "/tmp/" + output_key
    pdf.output(local_filename)
    print(f"PDF creado exitosamente: {local_filename}")
    s3_client.upload_file(local_filename, bucket_name, output_key)
    print(f"PDF subido a S3: {output_key}")

# Traducir PDF y guardar en S3
def translate_pdf(input_key, output_key, bucket_name, target_language):
    # Descargar el archivo PDF desde S3
    local_input_filename = "/tmp/" + input_key
    local_output_filename = "/tmp/" + output_key
    s3_client.download_file(bucket_name, input_key, local_input_filename)
    
    doc = fitz.open(local_input_filename)
    sample_text = doc[0].get_text("text")
    detected_language = detect(sample_text)

    if detected_language == target_language:
        print(f"El texto ya está en el idioma: {target_language}. Creando una copia del archivo original...")
        doc.save(local_output_filename)
        s3_client.upload_file(local_output_filename, bucket_name, output_key)
        print(f"Copia del archivo original subida a S3: {output_key}")
        return

    nuevo_pdf = fitz.open()
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        translator = GoogleTranslator(source=detected_language, target=target_language)
        translated_text = translator.translate(text)
        nueva_pagina = nuevo_pdf.new_page(width=page.rect.width, height=page.rect.height)
        nueva_pagina.insert_text((50, 50), translated_text, fontname="Times-Roman", fontsize=12, color=(0, 0, 0))
    nuevo_pdf.save(local_output_filename)
    s3_client.upload_file(local_output_filename, bucket_name, output_key)
    print(f"PDF traducido subido a S3: {output_key}")

# Convertir PDF a audio y guardar en S3
def convertir_pdf_a_audio(input_key, audio_key, bucket_name, target_language):
    local_pdf = "/tmp/" + input_key
    local_audio = "/tmp/" + audio_key
    s3_client.download_file(bucket_name, input_key, local_pdf)

    from PyPDF2 import PdfReader
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
        print(f"Archivo de audio subido a S3: {audio_key}")
    else:
        print("El PDF no contiene texto legible.")

# Mejorar audio y guardar en S3
def mejorar_audio(input_key, output_key, bucket_name):
    local_input_audio = "/tmp/" + input_key
    local_output_audio = "/tmp/" + output_key
    s3_client.download_file(bucket_name, input_key, local_input_audio)

    command = [
        'ffmpeg',
        '-i', local_input_audio,
        '-vn',
        '-acodec', 'libmp3lame',
        '-b:a', '128k',  # Compresión
        local_output_audio
    ]
    try:
        subprocess.run(command, check=True)
        s3_client.upload_file(local_output_audio, bucket_name, output_key)
        print(f"Audio comprimido subido a S3: {output_key}")
    except Exception as e:
        print(f"Error al comprimir audio: {e}")

# Lambda handler
def lambda_handler(event, context):
    bucket_name = event['bucket_name']
    url = event['url']
    target_language = event['target_language']
    pdf_key = "resultado.pdf"
    translated_pdf_key = "resultado_traducido.pdf"
    audio_key = "audio.mp3"
    compressed_audio_key = "audio_comprimido.mp3"

    # Obtener texto desde la URL
    texto = obtener_texto_web(url)
    if not texto:
        return {"statusCode": 400, "body": "No se pudo obtener el texto desde la URL."}

    # Crear y traducir el PDF
    crear_pdf(texto, pdf_key, bucket_name)
    translate_pdf(pdf_key, translated_pdf_key, bucket_name, target_language)

    # Convertir el PDF traducido a audio
    convertir_pdf_a_audio(translated_pdf_key, audio_key, bucket_name, target_language)

    # Comprimir el audio
    mejorar_audio(audio_key, compressed_audio_key, bucket_name)

    return {
        "statusCode": 200,
        "body": {
            "pdf_key": pdf_key,
            "translated_pdf_key": translated_pdf_key,
            "audio_key": compressed_audio_key
        }
    }