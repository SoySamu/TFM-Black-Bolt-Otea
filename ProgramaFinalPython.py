import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
from langdetect import detect
from gtts import gTTS
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend no interactivo para evitar problemas gráficos


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


def crear_pdf(texto, nombre_archivo):
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
    pdf.output(nombre_archivo)
    print(f"PDF creado exitosamente: {nombre_archivo}")


def translate_pdf(input_pdf_path, output_pdf_path, target_language):
    doc = fitz.open(input_pdf_path)
    sample_text = doc[0].get_text("text")
    detected_language = detect(sample_text)

    if detected_language == target_language:
        print(f"El texto ya está en el idioma: {target_language}. Creando una copia del archivo original...")
        doc.save(output_pdf_path)
        print(f"Copia del archivo original guardada como: {output_pdf_path}")
        return

    # Crear un nuevo PDF vacío para almacenar el texto traducido
    nuevo_pdf = fitz.open()

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")  # Obtener el texto original de la página

        # Traducir el texto
        translator = GoogleTranslator(source=detected_language, target=target_language)
        translated_text = translator.translate(text)

        # Crear una nueva página en el PDF traducido
        nueva_pagina = nuevo_pdf.new_page(width=page.rect.width, height=page.rect.height)

        # Insertar el texto traducido en la nueva página
        nueva_pagina.insert_text(
            (50, 50),  # Posición inicial del texto
            translated_text,
            fontname="Times-Roman",
            fontsize=12,
            color=(0, 0, 0)  # Color del texto (negro)
        )

    # Guardar el PDF traducido
    nuevo_pdf.save(output_pdf_path)
    nuevo_pdf.close()
    print(f"PDF traducido exitosamente: {output_pdf_path}")


def convertir_pdf_a_audio(pdf_file, audio_file, target_language):
    from PyPDF2 import PdfReader

    reader = PdfReader(pdf_file)
    texto = ""

    for page in reader.pages:
        texto += page.extract_text()

    if texto.strip():
        frases = re.split(r'(\.|!|\?)', texto)
        texto_con_delay = " ".join([f.strip() + ". " if f in '.!?' else f.strip() for f in frases])
        tts = gTTS(text=texto_con_delay, lang =target_language)
        tts.save(audio_file)
        print(f"Archivo de audio creado: {audio_file}")
    else:
        print("El PDF no contiene texto legible.")


def mejorar_audio(input_audio, output_audio, generar_grafico=False):
    if not os.path.exists(input_audio):
        raise FileNotFoundError(f"El archivo '{input_audio}' no existe.")

    if not output_audio.strip():
        base, _ = os.path.splitext(input_audio)
        output_audio = base + "_procesado.flac"

    # Paso 1: Procesamiento con filtros de FFmpeg
    command = [
        'ffmpeg',
        '-i', input_audio,
        '-vn',
        '-acodec', 'flac',
        '-ab', '320k',
        '-af',
        ('compand=attacks=0.01:decays=0.1:points=-70/-70|-60/-60|-30/-15|-20/-9|-15/-6|-10/-4.5|-5/-3|0/-1.5:'
         'soft-knee=2.5:gain=12,equalizer=f=4000:width_type=q:width=1.5:g=4,'
         'equalizer=f=12000:width_type=q:width=1:g=3,loudnorm=I=-16:TP=-1.5:LRA=11,'
         'agate=threshold=-40dB:ratio=1.5:attack=5:release=50:makeup=1:knee=2'),
        output_audio
    ]

    try:
        print(f"Procesando audio con FFmpeg: {' '.join(command)}")
        subprocess.run(command, check=True)
        print(f"Archivo de audio procesado correctamente: {output_audio}")
    except Exception as e:
        print(f"Error durante el procesamiento de audio: {e}")
        return

    # Paso 2: Comprimir el audio mejorado a formato MP3
    compressed_audio = output_audio.replace(".flac", ".mp3")
    command_compression = [
        'ffmpeg',
        '-i', output_audio,
        '-vn',
        '-acodec', 'libmp3lame',
        '-b:a', '128k',  # Comprimir a tasa de bits de 128 kbps
        compressed_audio
    ]

    try:
        print(f"Comprimiendo audio a MP3: {' '.join(command_compression)}")
        subprocess.run(command_compression, check=True)
        print(f"Archivo de audio comprimido correctamente: {compressed_audio}")
        return compressed_audio  # Devuelve el nombre del archivo comprimido
    except Exception as e:
        print(f"Error durante la compresión de audio: {e}")
        return None

    # Paso 3: Generar gráficos si se requiere
    if generar_grafico:
        try:
            comando_decodificar = [
                'ffmpeg',
                '-i', compressed_audio,
                '-f', 'f32le',
                '-acodec', 'pcm_f32le',
                '-ac', '1',
                '-ar', '44100',
                '-'
            ]
            proceso_decodificar = subprocess.run(comando_decodificar, capture_output=True, check=True)
            audio_procesado = np.frombuffer(proceso_decodificar.stdout, dtype=np.float32)

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.specgram(audio_procesado, Fs=44100, NFFT=2048, noverlap=1024, cmap='viridis')
            ax.set_title('Espectrograma - Audio Comprimido')
            ax.set_xlabel('Tiempo (s)')
            ax.set_ylabel('Frecuencia (Hz)')
            plt.tight_layout()
            plt.savefig("audio_comprimido_espectrograma.png")
            print("Gráfico generado exitosamente: audio_comprimido_espectrograma.png")
        except Exception as e:
            print(f"Error al generar el gráfico: {e}")


def enviar_correo(destinatario, asunto, cuerpo, archivos_adjuntos):
    remitente = "tfmrelatosucm@gmail.com"
    contraseña = "jago yvwn zwro rmbp"

    mensaje = MIMEMultipart()
    mensaje['From'] = remitente
    mensaje['To'] = destinatario
    mensaje['Subject'] = asunto
    mensaje.attach(MIMEText(cuerpo, 'plain'))

    for archivo in archivos_adjuntos:
        with open(archivo, "rb") as adjunto:
            parte = MIMEBase('application', 'octet-stream')
            parte.set_payload(adjunto.read())
            encoders.encode_base64(parte)
            parte.add_header('Content-Disposition', f"attachment; filename={os.path.basename(archivo)}")
            mensaje.attach(parte)

    servidor = smtplib.SMTP('smtp.gmail.com', 587)
    servidor.starttls()
    servidor.login(remitente, contraseña)
    servidor.send_message(mensaje)
    servidor.quit()
    print("Correo enviado exitosamente.")


def main():
   url = input("Introduce la URL del texto: ")
   texto = obtener_texto_web(url)
   if not texto:
        return
   crear_pdf(texto, "resultado.pdf")
   idioma = input("Introduce el idioma deseado ('es', 'en', 'fr', 'de', 'it'): ").strip()
   translate_pdf("resultado.pdf", "resultado_traducido.pdf", idioma)
   convertir_pdf_a_audio("resultado_traducido.pdf", "audio.mp3", idioma)
   compressed_audio = mejorar_audio("audio.mp3", "audio_mejorado.flac", generar_grafico=True)
   if not compressed_audio:
        print("No se pudo comprimir el audio. Abortando.")
        return
   destinatario = input("Introduce el correo del destinatario: ").strip()
   enviar_correo(destinatario, "Archivos Generados", "Adjunto encontrarás el PDF y el audio generados.",
                  ["resultado.pdf", "resultado_traducido.pdf", compressed_audio])

if __name__ == "__main__":
    main()