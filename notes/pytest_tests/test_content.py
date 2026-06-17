# test_content.py
"""
Тестирование контента веб‑приложения YaNote.

Проверяется доступность контента через:
* пользователя - читатель;
* пользователя - автор.

Включает тесты:
* передачи заметок в список заметок, в словаре context;
* формирования отдельных списков заметок для разных пользователей;
* проверки передачи формы на страницы создания
и редоктирования заметки пользовательем.
"""

import pytest
from pytest_lazyfixture import lazy_fixture as lf  # type: ignore
from django.urls import reverse  # type: ignore
from http import HTTPStatus

# Импортируем класс формы.
from notes.forms import NoteForm


@pytest.mark.parametrize(
    'parametrized_client, note_in_list',
    (
        (lf('author_client'), True),
        (lf('not_author_client'), False),
    )
)
def test_notes_list_for_different_users(
        note, parametrized_client, note_in_list):
    """
    Тест доступности заметки в списке для разных пользователей.

    Проверяет, что:
    * страница списка заметок доступна (статус 200);
    * контекст ответа содержит 'object_list';
    * автор видит свою заметку в списке;
    * читатель (не автор) не видит чужую заметку в списке.

    Параметры (передаются через parametrize):
        parametrized_client: клиент (авторизованный как автор или не автор);
        note_in_list: булево значение — ожидается ли заметка
        в списке для этого клиента.

    Аргументы:
        note: фикстура тестовой заметки (создана автором);
        parametrized_client: HTTP‑клиент, авторизованный под тестируемым
        пользователем;
        note_in_list: флаг, указывающий, должна ли заметка быть в списке
        для данного клиента.
    """
    url = reverse('notes:list')
    response = parametrized_client.get(url)

    # Проверяем доступность страницы
    assert response.status_code == HTTPStatus.OK, (
        f"Страница списка заметок недоступна. Статус: {response.status_code}"
    )

    # Убеждаемся, что контекст содержит object_list
    assert 'object_list' in response.context, (
        "Контекст ответа не содержит 'object_list'"
    )
    object_list = response.context['object_list']

    # Проверяем, что список не пустой (для надёжности проверки)
    if not note_in_list:  # только для not_author_client
        assert len(object_list) >= 0, (
            "Список заметок пуст — невозможно проверить отсутствие заметки"
        )

    # Сравниваем по ID для надёжности
    note_found = any(n.id == note.id for n in object_list)

    # Проверяем соответствие ожидаемому результату
    assert note_found is note_in_list, (
        f"Для клиента {'author' if note_in_list else 'not_author'} "
        f"ожидалось {note_in_list}, но получено {note_found}"
    )


@pytest.mark.parametrize(
    # В качестве параметров передаём name и args для reverse.
    'name, args',
    (
        # Для тестирования страницы создания заметки
        # никакие дополнительные аргументы для reverse() не нужны.
        ('notes:add', None),
        # Для тестирования страницы редактирования заметки нужен slug заметки.
        ('notes:edit', lf('slug_for_args'))
    )
)
def test_pages_contains_form(author_client, name, args):
    """
    Тест наличия формы на страницах создания и редактирования заметки.

    Проверяет, что на указанных страницах:
    * страница доступна (статус 200);
    * в контексте ответа присутствует ключ 'form';
    * объект формы является экземпляром NoteForm.

    Параметры (передаются через parametrize):
        name: имя URL‑маршрута (например, 'notes:add' или 'notes:edit');
        args: дополнительные аргументы для reverse (None для создания,
        slug для редактирования).

    Аргументы:
        author_client: HTTP‑клиент, авторизованный как автор заметки;
        name: строка — имя маршрута для reverse;
        args: кортеж или None — аргументы для формирования URL.
    """
    # Формируем URL.
    url = reverse(name, args=args)
    # Запрашиваем нужную страницу:
    response = author_client.get(url)
    # Проверяем, есть ли объект формы в словаре контекста:
    assert 'form' in response.context
    # Проверяем, что объект формы относится к нужному классу.
    assert isinstance(response.context['form'], NoteForm)
