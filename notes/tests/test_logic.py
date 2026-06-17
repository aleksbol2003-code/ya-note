"""
Тестирование маршрутов логики приложения YANOTE.

Проверяется логика взаимодействия пользователей с приложением:
* анонимных пользователей;
* авторизованных пользователей;
* пользователей-авторов.

Включает тесты:
* создание заметок и проверки работы slug;
* редактирование и удаление заметок.
"""
from http import HTTPStatus  # type: ignore

from django.contrib.auth import get_user_model  # type: ignore
from django.test import Client, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from notes.models import Note  # type: ignore

User = get_user_model()


class TestCommentCreation(TestCase):
    """
    Тестирование создания заметок разными пользователеми, проверка работы slug.

    Проверяется:
    * создание заметки аторизироваными и анонимным пользователями;
    * попытка создания заметки с неуникальным slug;
    * создание заметки без указания slug (автоматическое формирование).
    """

    TEXT = 'Текст заметки'
    TITLE = 'Заголовок заметки'

    @classmethod
    def setUpTestData(cls):
        """Подготовка тестовых данных, создание пользователей и др."""
        cls.author = User.objects.create_user(
            username='Автор',
            password='au123'
        )
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.reader = User.objects.create_user(
            username='Читатель',
            password='re123'
        )
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)
        cls.url = reverse('notes:add')
        cls.form_data = {
            'title': cls.TITLE,
            'text': cls.TEXT,
            'slug': 'slug'
        }

    def test_user_and_not_user_can_create_notes_and_not_unique_slug(self):
        """
        Тест создания заметок с неуникальным slug разными типами пользователей.

        Проверяется:
        * успешное создание заметки пользователем (автором);
        * попытка создания заметки пользователем (читателем) с тем же slug;
        * попытка создания заметки анонимным пользователем.
        """
        self.author_client.login(username='Автор', password='au123')
        response = self.author_client.post(self.url, data=self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(Note.objects.get().title, self.TITLE)
        self.assertEqual(Note.objects.get().text, self.TEXT)
        self.assertEqual(Note.objects.get().author, self.author)

        self.author_client.logout()

        self.reader_client.login(username='Читатель', password='re123')
        response = self.reader_client.post(self.url, data=self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Note.objects.count(), 1)

        self.reader_client.logout()

        response = self.client.post(self.url, data=self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Note.objects.count(), 1)

    def test_user_create_notes_not_slug(self):
        """
        Тест создания заметки без указания slug.

        Проверяется:
        * автоматическое формирование slug при создании заметки;
        * корректность сохранения остальных полей заметки.
        """
        self.author_client.login(username='Автор', password='au123')
        form_data = {
            'title': 'Заголовок',
            'text': 'Текст',
        }
        response = self.author_client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(Note.objects.get().title, 'Заголовок')
        self.assertEqual(Note.objects.get().text, 'Текст')
        self.assertEqual(Note.objects.get().author, self.author)
        self.assertIsNotNone(Note.objects.get().slug)
        self.assertNotEqual(Note.objects.get().slug, '')


class TestNoteEditDelete(TestCase):
    """
    Тестирование редактирования и удаления заметок.

    Проверяется:
    * возможность пользователя (автора) редактировать и удалять свои заметки;
    * невозможность пользователя (читателя) редактировать
    и удалять чужие заметки.
    """

    TEXT = 'Текст заметки'
    TITLE = 'Заголовок заметки'
    NEW_TEXT = 'Новый текст заметки'
    NEW_TITLE = 'Новый заголовок заметки'
    SLUG = 'test-note'
    NEW_SLUG = 'updated-note'

    @classmethod
    def setUpTestData(cls):
        """Подготовка тестовых данных, создание пользователей и заметки."""
        cls.author = User.objects.create_user(
            username='Автор',
            password='au123'
        )
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.reader = User.objects.create_user(
            username='Читатель',
            password='re123'
        )
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)
        cls.note = Note.objects.create(
            title=cls.TITLE,
            text=cls.TEXT,
            author=cls.author,
            slug=cls.SLUG
        )
        cls.edit_url = reverse('notes:edit', args=(cls.note.slug,))
        cls.del_url = reverse('notes:delete', args=(cls.note.slug,))
        cls.done_url = reverse('notes:success', None)
        cls.form_data = {
            'title': cls.NEW_TITLE,
            'text': cls.NEW_TEXT,
            'slug': cls.NEW_SLUG
        }

    def test_author_can_edit_note_via_edit_page(self):
        """Автор может редактировать заметку через страницу редактирования."""
        response = self.author_client.post(self.edit_url, data=self.form_data)
        self.assertRedirects(response, self.done_url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        updated_note = Note.objects.get()
        self.assertEqual(updated_note.title, self.NEW_TITLE)
        self.assertEqual(updated_note.text, self.NEW_TEXT)
        self.assertEqual(updated_note.author, self.author)

    def test_author_can_delete_note_via_confirm_page(self):
        """Автор может удалять заметку через страницу подтверждения."""
        # GET-запрос на страницу подтверждения
        get_response = self.author_client.get(self.del_url)
        self.assertEqual(get_response.status_code, HTTPStatus.OK)

        # POST-запрос для подтверждения удаления
        post_response = self.author_client.post(self.del_url)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertFalse(Note.objects.filter(slug=self.NEW_SLUG).exists())

    def test_reader_cannot_edit_other_note(self):
        """Читатель не может редактировать чужую заметку."""
        response = self.reader_client.post(self.edit_url, data=self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        note = Note.objects.get()
        self.assertEqual(note.title, self.TITLE)
        self.assertEqual(note.text, self.TEXT)

    def test_reader_cannot_delete_other_note(self):
        """Читатель не может удалять чужую заметку."""
        # GET-запрос на страницу подтверждения удаления
        get_response = self.reader_client.get(self.del_url)
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)

        # POST-запрос на удаление
        post_response = self.reader_client.post(self.del_url)
        self.assertEqual(post_response.status_code, HTTPStatus.NOT_FOUND)
