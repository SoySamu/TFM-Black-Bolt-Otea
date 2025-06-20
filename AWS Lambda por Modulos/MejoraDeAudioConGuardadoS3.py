import boto3
import subprocess

s3_client = boto3.client('s3')

def mejorar_audio(event, context):
    input_key = event['input_key']
    output_key = event['output_key']
    bucket_name = event['bucket_name']

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
        return {"statusCode": 200, "body": f"Audio comprimido subido a S3 con clave: {output_key}"}
    except Exception as e:
        return {"statusCode": 500, "body": f"Error al comprimir audio: {e}"}