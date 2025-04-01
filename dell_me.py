import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MsServiceControl.settings")
import django

django.setup()

from sorting_message import presend_filters


presend_filters(text=f"❌",type_msg='manage_control')