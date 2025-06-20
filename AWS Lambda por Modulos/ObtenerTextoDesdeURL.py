import requests
from bs4 import BeautifulSoup

def obtener_texto_web(event, context):
    url = event['url']
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        div_content = soup.find('div', class_='post-body entry-content float-container')
        if div_content:
            return {"statusCode": 200, "body": div_content.get_text()}
        else:
            return {"statusCode": 404, "body": "No se encontró el div especificado."}
    else:
        return {"statusCode": response.status_code, "body": "Error al acceder a la página."}