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
from http import HTTPStatus  # type: ignore

from django.contrib.auth import get_user_model  # type: ignore
from django.urls import reverse  # type: ignore

from notes.tests.test_content import BaseNoteTest

User = get_user_model()


class TestRoutes(BaseNoteTest):
    """Тестированию маршрутов проекта."""

    def test_main_page_anonymous_access(self):
        """Главная страница доступна анонимному пользователю."""
        response = self.client.get(reverse('notes:home'))
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_access_to_notes_pages(self):
        """Проверка доступности страниц аутентифицированному пользователю.

        Страница со списком заметок notes/.
        Страница успешного добавления заметки done/.
        Страница добавления новой заметки add/.
        """
        self.client.login(username='Автор', password='au123')
        urls = ('notes:list', 'notes:add', 'notes:success')
        for name in urls:
            with self.subTest(name=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_note_detail_edit_delete_access_only_for_author(self):
        """Доступность страниц отдельной заметки, удаления и редактирования.

        Доступ автора заметки.
        Доступ другого пользователя — ошибка 404.
        """
        urls = (
            ('notes:detail', {'slug': self.note.slug}),
            ('notes:edit', {'slug': self.note.slug}),
            ('notes:delete', {'slug': self.note.slug})
        )
        for name, kwargs in urls:
            with self.subTest(name=name):
                url = reverse(name, kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.client.login(username='Автор', password='au123')

        for name, kwargs in urls:
            with self.subTest(name=name):
                url = reverse(name, kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

        self.client.login(username='Читатель', password='re123')

        for name, kwargs in urls:
            with self.subTest(name=name):
                url = reverse(name, kwargs=kwargs)
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_for_protected_pages_for_anonymous(self):
        """Перенаправление анонимного пользователя на страницу логина.

        Перенапаление происходит при обращении к старницам списка заметок,
        успешного добавление записи, добавления заметки, отдельной заметки,
        редактирования или удаления заметки.
        """
        urls = (
            ('notes:list', None),
            ('notes:add', None),
            ('notes:success', None),
            ('notes:detail', {'slug': self.note.slug}),
            ('notes:edit', {'slug': self.note.slug}),
            ('notes:delete', {'slug': self.note.slug})
        )

        for item in urls:
            if isinstance(item, tuple):
                name, kwargs = item
                response = self.client.get(reverse(name, kwargs=kwargs))
            else:
                name = item
                response = self.client.get(reverse(name))

            with self.subTest(name=name):
                self.assertEqual(response.status_code, HTTPStatus.FOUND)
                self.assertIn('login', response.url)

    def test_auth_pages_accessibility(self):
        """Проверка доступности страниц авторизации для всех пользователей.

        Вход в учетную запись и выход из неё.
        """
        urls = ('users:login', 'users:signup')

        for name in urls:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, HTTPStatus.OK)

                self.client.login(username='Автор', password='au123')

                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, HTTPStatus.OK)

                self.client.logout()

        with self.subTest(name='users:logout'):
            self.client.login(username='Автор', password='au123')
            response = self.client.post(reverse('users:logout'))
            self.assertEqual(response.status_code, HTTPStatus.OK)
