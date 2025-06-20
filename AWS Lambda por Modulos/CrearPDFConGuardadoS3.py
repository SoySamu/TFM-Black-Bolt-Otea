import boto3
from fpdf import FPDF

s3_client = boto3.client('s3')

def crear_pdf(event, context):
    texto = event['texto']
    output_key = event['output_key']
    bucket_name = event['bucket_name']
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
    s3_client.upload_file(local_filename, bucket_name, output_key)
    return {"statusCode": 200, "body": f"PDF creado y subido a S3 con clave: {output_key}"}