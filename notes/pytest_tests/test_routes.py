"""
Тестирование маршрутов веб‑приложения YaNote.

Проверяется доступность различных страниц для:
* анонимных пользователей;
* авторизованных пользователей;
* пользователей-авторов.

Включает тесты:
* главной страницы;
* страниц авторизации (вход, регистрация, выход);
* страниц работы с заметками (список, добавление, редактирование, удаление);
* проверки страниц доступа для автора и читателя.
"""
import pytest
from http import HTTPStatus

from pytest_django.asserts import assertRedirects
from pytest_lazyfixture import lazy_fixture as lf  # type: ignore
from django.urls import reverse  # type: ignore


def test_home_availability_for_anonymous_user(client):
    """Главная страница доступна анонимному пользователю."""
    url = reverse('notes:home')
    response = client.get(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    'name,expected_status',
    [
        ('notes:home', HTTPStatus.OK),
        ('users:login', HTTPStatus.OK),
        ('users:signup', HTTPStatus.OK),
        ('users:logout', HTTPStatus.OK),  # FOUND
    ]
)
@pytest.mark.django_db
def test_pages_availability_for_anonymous_user(client, name, expected_status):
    """Доступ анонимного пользователя к списку заметок их удаления и др."""
    url = reverse(name)  # Получаем ссылку на нужный адрес.
    if name != 'users:logout':
        response = client.get(url, follow=True)  # Выполняем запрос.
    else:
        response = client.post(url, follow=False)
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    'name',
    ('notes:list', 'notes:add', 'notes:success')
)
def test_pages_availability_for_auth_user(not_author_client, name):
    """Доступ пользоватепля не автора к списку заметок их добавления и др."""
    url = reverse(name)
    response = not_author_client.get(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    'name',
    ('notes:detail', 'notes:edit', 'notes:delete'),
)
def test_pages_availability_for_author(author_client, name, note):
    """Доступ пользоватепля автора к списку заметок их добавления и др."""
    url = reverse(name, args=(note.slug,))
    response = author_client.get(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    'parametrized_client, expected_status',
    # Предварительно оборачиваем имена фикстур
    # в вызов функции pytest.lazy_fixture().
    [
        (lf('not_author_client'), HTTPStatus.NOT_FOUND),
        (lf('author_client'), HTTPStatus.OK)
    ],
)
@pytest.mark.parametrize(
    'name',
    ('notes:detail', 'notes:edit', 'notes:delete'),
)
def test_pages_availability_for_different_users(
        parametrized_client, name, note, expected_status
):
    """Доступ любого пользоватепля к своей заметки и к её редакции."""
    url = reverse(name, args=(note.slug,))
    response = parametrized_client.get(url)
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    'name, args',
    (
        ('notes:detail', lf('slug_for_args')),
        ('notes:edit', lf('slug_for_args')),
        ('notes:delete', lf('slug_for_args')),
        ('notes:add', None),
        ('notes:success', None),
        ('notes:list', None),
    ),
)
# Передаём в тест анонимный клиент, name проверяемых страниц и args:
def test_redirects(client, name, args):
    """Тестирования редиректорв всех страниц."""
    login_url = reverse('users:login')
    # Теперь не надо писать никаких if и можно обойтись одним выражением.
    url = reverse(name, args=args)
    expected_url = f'{login_url}?next={url}'
    response = client.get(url)
    assertRedirects(response, expected_url)
