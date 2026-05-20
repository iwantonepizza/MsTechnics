# T-3-020. Displays — list / detail / photos / contacts

> **Тип:** API
> **Приоритет:** P0
> **Оценка:** 2.5 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Эндпоинты для экранов. Включают вложенную сетку ячеек (для Display View / Сервис фронт-экрана).

---

## Зависимости

- **Блокируется:** T-3-011 (City)
- **Блокирует:** T-3-021, T-3-022, T-3-023, T-3-030

---

## Эндпоинты

```
GET    /api/v1/displays?city=<slug>             → list (city filter)
GET    /api/v1/displays/{slug}                  → detail с cells, panels, current_condition
GET    /api/v1/displays/{slug}/contacts         → список контактов экрана
POST   /api/v1/displays/{slug}/photos (multipart) [admin/control]
GET    /api/v1/displays/{slug}/photos
DELETE /api/v1/displays/{slug}/photos/{photo_id} [admin/control]
```

---

## Что нужно сделать

### Шаг 1. Сериализаторы

`apps/interface/api/v1/displays/serializers.py`:

```python
from rest_framework import serializers

from apps.directory.displays.models import Display, Cell
from apps.directory.panels.models import Panel
from apps.workflow.departures.models import Contact

from apps.interface.api.v1.refs.serializers import (
    ColorSerializer, SmileSerializer, ConditionSerializer, CitySerializer,
    ApplicationStatusSerializer,
)


class DisplayListItemSerializer(serializers.ModelSerializer):
    """Лёгкая версия для списков."""
    city = CitySerializer(read_only=True)
    current_condition = ConditionSerializer(read_only=True)
    
    class Meta:
        model = Display
        fields = [
            'id', 'name', 'description', 'slug', 'city',
            'rows', 'cols', 'current_condition',
        ]


class PanelOnCellSerializer(serializers.Serializer):
    """Минимальный embedded в Cell."""
    id = serializers.CharField(source='name')  # api-contract.md: panel.id = string from Panel.name
    condition = ConditionSerializer(read_only=True)
    application_status = serializers.SerializerMethodField()
    comment = serializers.CharField(allow_blank=True)
    
    def get_application_status(self, panel):
        # Из annotation if available, иначе fallback
        from apps.directory.panels.managers import PanelManager
        status_name = getattr(panel, 'active_application_status', None)
        if status_name:
            return {'name': status_name}
        return {'name': 'default'}


class CellInDisplaySerializer(serializers.ModelSerializer):
    panel = PanelOnCellSerializer(read_only=True)
    position = serializers.CharField()  # property вычисляется в Cell.position
    
    class Meta:
        model = Cell
        fields = ['id', 'position', 'row', 'col', 'panel']


class DisplayDetailSerializer(serializers.ModelSerializer):
    """Полная детализация со всеми ячейками — для рабочей зоны."""
    city = CitySerializer(read_only=True)
    current_condition = ConditionSerializer(read_only=True)
    cells = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    project_photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Display
        fields = [
            'id', 'name', 'description', 'slug', 'city',
            'rows', 'cols', 'current_condition',
            'file_url', 'project_photo_url', 'cells',
        ]
    
    def get_cells(self, display):
        # prefetched через get_object
        cells = display.cells.select_related('panel__condition').order_by('row', 'col')
        # annotate panels with active_application_status
        from apps.directory.panels.models import Panel
        from apps.directory.panels.managers import PanelQuerySet
        panel_ids = [c.panel_id for c in cells if c.panel_id]
        annotated_panels = {
            p.id: p for p in
            Panel.objects.filter(id__in=panel_ids).with_active_application_status()
        }
        
        result = []
        for cell in cells:
            panel = annotated_panels.get(cell.panel_id)
            if panel:
                cell.panel = panel  # подмена на annotated
            result.append(CellInDisplaySerializer(cell).data)
        return result
    
    def get_file_url(self, display):
        return display.file.url if display.file else None
    
    def get_project_photo_url(self, display):
        return display.project_photo.url if display.project_photo else None


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'first_name', 'last_name', 'description', 'phone_number', 'telegram_id']


class PhotoUploadSerializer(serializers.Serializer):
    file = serializers.ImageField(required=True)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True)
```

### Шаг 2. ViewSet

`apps/interface/api/v1/displays/views.py`:

```python
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.directory.displays.models import Display, PhotoDisplay
from shared.permissions import HasCityAccess, HasDepartmentAccess
from .serializers import (
    DisplayListItemSerializer, DisplayDetailSerializer,
    ContactSerializer, PhotoUploadSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=['displays'],
        summary='Список экранов',
        parameters=[
            OpenApiParameter('city', str, description='Slug города (фильтр)'),
        ],
    ),
    retrieve=extend_schema(tags=['displays'], summary='Детальная информация об экране'),
)
class DisplayViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasCityAccess]
    lookup_field = 'slug'
    
    def get_queryset(self):
        qs = Display.objects.select_related('city', 'current_condition__color', 'current_condition__icon')
        
        # Фильтр по городам, к которым доступ
        user = self.request.user
        if user.permission not in ('admin', 'all'):
            qs = qs.filter(city__in=user.allowed_city.all())
        
        # Фильтр по slug города
        city_slug = self.request.query_params.get('city')
        if city_slug:
            qs = qs.filter(city__slug=city_slug)
        
        return qs.order_by('city__name', 'name')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DisplayDetailSerializer
        return DisplayListItemSerializer
    
    @extend_schema(tags=['displays'], summary='Контакты экрана', responses=ContactSerializer(many=True))
    @action(detail=True, methods=['get'])
    def contacts(self, request, slug=None):
        display = self.get_object()
        contacts = display.contacts.all().order_by('last_name', 'first_name')
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['displays'],
        summary='Фотографии экрана',
        request=None,
        responses={200: PhotoUploadSerializer(many=True)},
    )
    @action(detail=True, methods=['get'])
    def photos(self, request, slug=None):
        display = self.get_object()
        photos = display.photos.all().order_by('-id') if hasattr(display, 'photos') else []
        return Response([
            {
                'id': p.id,
                'url': p.image.url if p.image else None,
                'description': getattr(p, 'description', ''),
                'uploaded_at': getattr(p, 'uploaded_at', None),
            }
            for p in photos
        ])
    
    @extend_schema(
        tags=['displays'],
        summary='Загрузить фото экрана',
        request={'multipart/form-data': PhotoUploadSerializer},
        responses={201: PhotoUploadSerializer},
    )
    @action(
        detail=True, methods=['post'],
        url_path='photos/upload',
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsAuthenticated, HasDepartmentAccess.for_('control', 'admin', 'all')],
    )
    def upload_photo(self, request, slug=None):
        display = self.get_object()
        serializer = PhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        photo = PhotoDisplay.objects.create(
            display=display,
            image=serializer.validated_data['file'],
            # description=serializer.validated_data.get('description', ''),  # если поле есть
        )
        return Response(
            {'id': photo.id, 'url': photo.image.url},
            status=http_status.HTTP_201_CREATED,
        )
    
    @extend_schema(tags=['displays'], summary='Удалить фото', responses={204: None})
    @action(
        detail=True, methods=['delete'],
        url_path='photos/(?P<photo_id>[^/.]+)',
        permission_classes=[IsAuthenticated, HasDepartmentAccess.for_('control', 'admin', 'all')],
    )
    def delete_photo(self, request, slug=None, photo_id=None):
        display = self.get_object()
        try:
            photo = display.photos.get(id=photo_id)
        except PhotoDisplay.DoesNotExist:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        photo.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)
```

### Шаг 3. URLs

`apps/interface/api/v1/displays/urls.py`:

```python
from rest_framework.routers import DefaultRouter
from .views import DisplayViewSet

router = DefaultRouter()
router.register('displays', DisplayViewSet, basename='displays')
urlpatterns = router.urls
```

В `apps/interface/api/v1/urls.py` добавить:
```python
path('', include('apps.interface.api.v1.displays.urls')),
```

### Шаг 4. Тесты

`apps/interface/tests/test_displays.py`:

```python
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(ms_user_factory, city_factory):
    client = APIClient()
    user = ms_user_factory(permission='control')
    city_a = city_factory(name='izhevsk', slug='izhevsk')
    user.allowed_city.add(city_a)
    client.force_authenticate(user=user)
    return client, user, city_a


def test_displays_list(auth_client, display_factory):
    client, user, city = auth_client
    display_factory.create_batch(3, city=city)
    
    response = client.get('/api/v1/displays/')
    
    assert response.status_code == 200
    assert len(response.data['results']) >= 3


def test_displays_filtered_by_city(auth_client, display_factory, city_factory):
    client, user, city_a = auth_client
    city_b = city_factory(name='perm', slug='perm')
    user.allowed_city.add(city_b)
    
    display_factory(city=city_a)
    display_factory(city=city_b)
    
    response = client.get('/api/v1/displays/?city=izhevsk')
    
    assert response.status_code == 200
    cities_in_response = [d['city']['slug'] for d in response.data['results']]
    assert all(c == 'izhevsk' for c in cities_in_response)


def test_display_detail_includes_cells(auth_client, display_with_layout_factory):
    client, user, city = auth_client
    display = display_with_layout_factory(rows=2, cols=2, city=city)
    
    response = client.get(f'/api/v1/displays/{display.slug}/')
    
    assert response.status_code == 200
    assert 'cells' in response.data
    assert len(response.data['cells']) == 4


def test_no_access_to_foreign_city_display(client_factory, ms_user_factory, display_factory, city_factory):
    other_city = city_factory(name='kazan', slug='kazan')
    display = display_factory(city=other_city)
    
    user = ms_user_factory(permission='control')
    # NOT adding kazan to allowed_city
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.get(f'/api/v1/displays/{display.slug}/')
    assert response.status_code in (403, 404)


def test_get_contacts(auth_client, display_factory):
    client, user, city = auth_client
    display = display_factory(city=city)
    # Создаём contact + связь:
    from apps.workflow.departures.models import Contact
    c = Contact.objects.create(first_name='Иван', last_name='Иванов', phone_number='+79991234567')
    c.displays.add(display)
    
    response = client.get(f'/api/v1/displays/{display.slug}/contacts/')
    
    assert response.status_code == 200
    assert any(x['first_name'] == 'Иван' for x in response.data)


def test_upload_photo_requires_control_role(client_factory, ms_user_factory, display_factory, city_factory):
    """Monitoring может только смотреть, control загружать."""
    city = city_factory()
    display = display_factory(city=city)
    
    monitor = ms_user_factory(permission='monitoring')
    monitor.allowed_city.add(city)
    client = APIClient()
    client.force_authenticate(user=monitor)
    
    from django.core.files.uploadedfile import SimpleUploadedFile
    response = client.post(
        f'/api/v1/displays/{display.slug}/photos/upload/',
        {'file': SimpleUploadedFile('test.jpg', b'x' * 100, content_type='image/jpeg')},
        format='multipart',
    )
    
    assert response.status_code == 403
```

---

## Критерии приёмки

- [ ] DisplayViewSet с list / retrieve / contacts / photos / upload_photo / delete_photo
- [ ] Detail возвращает cells с panels (с `active_application_status`)
- [ ] Permission HasCityAccess работает (юзер видит только свои города)
- [ ] Upload photo требует роль control/admin
- [ ] N+1 нет: detail на 100-cell экране < 5 запросов (проверить через django-debug-toolbar или counting cursor)
- [ ] OpenAPI документирует все 6 эндпоинтов
- [ ] Минимум 6 тестов (см. выше)

---

## Что НЕ делать

- **НЕ возвращай** в `cells` всю информацию о панели (запрещённые поля и т.п.) — это раздуёт payload до сотен KB
- **НЕ грузи** PDF / project-photo в detail-сериализатор — только URL
- **НЕ дай** возможность изменения rows/cols (это изменение архитектуры экрана — через DisplayService.create в admin)

---

## Производительность

Для `/api/v1/displays/{slug}/` на экране 10×10:
- 1 запрос на Display (с select_related city, condition)
- 1 запрос на Cells
- 1 запрос на annotated Panels (с subquery для active_application_status)

Итого ~3 SQL — это норма. Если 100+ — N+1, разбираемся.
