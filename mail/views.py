import structlog

logger = structlog.get_logger(__name__)
import os
import json
import base64
from datetime import datetime, timedelta
from django.conf import settings
from django.shortcuts import redirect, render
from django.http import HttpResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
import logging

from get_time import get_time_setting_tz
from zip.models import Display
from .models import GmailMessage, Alarm
import time
TOKEN_FILE = os.path.join(settings.BASE_DIR, 'Config/token.pickle')
CREDENTIALS_FILE = settings.GOOGLE_CREDENTIALS_FILE
SCOPES = settings.SCOPES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_emails(service):
    messages = []
    page_token = None

    while True:
        response = service.users().messages().list(
            userId='me',
            q='from:service@alimail.vnnox.com',
            includeSpamTrash=False,
            pageToken=page_token
        ).execute()

        messages.extend(response.get('messages', []))
        page_token = response.get('nextPageToken')

        if not page_token:
            break

    return messages
def google_auth(request):
    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri="http://localhost:8000/gmail/oauth2callback/"
        )
        auth_url, _ = flow.authorization_url(prompt="consent")
        return redirect(auth_url)
    except Exception as e:
        return HttpResponse(f"Ошибка аутентификации: {e}", status=500)


def oauth2callback(request):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Только для разработки
    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri="http://localhost:8000/gmail/oauth2callback/"
        )
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        creds = flow.credentials
        with open(TOKEN_FILE, "w") as token:
            json.dump(json.loads(creds.to_json()), token)  # Сохраняем как объект
        return redirect("/gmail/emails/")
    except Exception as e:
        return HttpResponse(f"Ошибка обратного вызова: {e}", status=500)


def get_message_body(payload):
    text = ""
    try:
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html' and 'data' in part['body']:
                    text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in payload and 'data' in payload['body']:
            text = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        return text.strip() if text else "Нет текста"
    except Exception as e:
        logger.info(f"Ошибка декодирования тела: {e}")
        return "Ошибка извлечения текста"


def extract_display_name(display_text):
    """Функция для поиска дисплея по имени в базе данных"""
    displays = Display.objects.all()
    display_values = displays.values_list('description', flat=True)
    for display_value in display_values:
        if display_value.lower() in display_text.lower():
            display = displays.get(description__contains=display_value)
            if display is not None:
                return display
            else:
                logger.debug('debug', value=display_value)
    return None  # Если дисплей не найден


def parse_description(description):
    """Функция для разбора статуса из строки"""
    keywords = ["working status", "voltage", "temperature", "fan speed"]
    for keyword in keywords:
        if keyword in description:
            status = description.replace(keyword, "").strip()
            return f"{keyword}: {status}"
    return description  # Если не найдено, вернуть оригинал


def parse_alarms(html):
    soup = BeautifulSoup(html, "html.parser")
    alarm_blocks = soup.find_all("div", class_="emailDetail-list-block")

    display_block = soup.find("div", class_="emailDetail-title")
    alarm_data_list = []

    if not alarm_blocks:
        if display_block:
            return [{
                "time": get_time_setting_tz().strftime('%Y-%m-%d %H:%M:%S'),
                "description": display_block.text.strip(),
                "status": display_block.text.strip().split(':')[0],
                "number": '0'
            }], display_block.text.strip()
        return None, display_block.text.strip()

    for block in alarm_blocks:
        tbody = block.find("table").find("tbody")
        if not tbody:
            continue
        rows = tbody.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 4:  # Проверяем наличие нужных колонок
                continue
            time = cols[0].text.strip()
            description = cols[1].text.strip()
            status = cols[2].text.strip()
            position = cols[3].text.strip()
            number = None
            if "Receiving card(No:" in position:
                number = position.split("Receiving card(No:")[1].split(")")[0]
            alarm_data_list.append({
                "time": time,
                "description": description,
                "status": status,
                "number": number
            })
    return alarm_data_list, display_block.text.strip()


def get_emails(request):
    start_time = time.time()
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as token:
            creds_data = json.load(token)
            if isinstance(creds_data, str):
                creds_data = json.loads(creds_data)
            creds = Credentials.from_authorized_user_info(creds_data)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as token:
                json.dump(json.loads(creds.to_json()), token)
        else:
            return redirect('google_auth')

    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(
        userId='me',
        q='from:service@alimail.vnnox.com',
        includeSpamTrash=False
    ).execute()
    messages = get_all_emails(service)

    if not messages:
        return HttpResponse("Писем не найдено.")

    processed_count = 0
    for message in messages:
        if GmailMessage.objects.filter(message_id=message['id']).exists():
            logger.info('exist')
            continue
        logger.info('iter')
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        received_at = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
        full_text = get_message_body(msg['payload'])
        alarm_data_list, alarm_display = parse_alarms(full_text)

        try:
            received_at = datetime.strptime(received_at, '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
            received_at = None
        display = extract_display_name(alarm_display) if alarm_display else None
        if not display:
            logger.info(f"Дисплей не найден: {alarm_display}")

        # Создаём запись письма
        gmail_message = GmailMessage.objects.create(
            message_id=message['id'],
            received_at=received_at,
            full_text=full_text
        )

        # Создаём записи для всех тревог
        if alarm_data_list:
            for alarm_data in alarm_data_list:

                Alarm.objects.create(display=display,
                                     message=gmail_message,
                                     alarm_time=alarm_data['time'],
                                     slot_number=alarm_data['number'],
                                     description=alarm_data['description'],
                                     status=alarm_data['status']
                                     )
            processed_count += 1
        else:
            logger.debug('debug', value=alarm_display)
    end_time = time.time()  # Записываем конечное время
    execution_time = end_time - start_time
    time_str = str(timedelta(seconds=execution_time))[2:]
    return HttpResponse(f"Обработано {processed_count} новых писем. За {time_str}")
