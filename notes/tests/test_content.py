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
from http import HTTPStatus

from django.contrib.auth import get_user_model  # type: ignore
from django.test import TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from notes.models import Note
from notes.forms import NoteForm

User = get_user_model()


class BaseNoteTest(TestCase):
    """Базовый класс для тестов приложения YaNote."""

    TEXT = 'Текст заметки.'
    TITLE = 'Заголовок заметки.'
    SLUG = 'test-note-1'
    NEW_TEXT = 'Новый текст заметки'
    NEW_TITLE = 'Новый заголовок заметки'
    NEW_SLUG = 'updated-note'

    ADD_URL = reverse('notes:add')
    LIST_URL = reverse('notes:list')
    DONE_URL = reverse('notes:success')

    @classmethod
    def setUpTestData(cls):
        """Подготовка данных для тестов. Создаются пользователи и заметка."""
        super().setUpTestData()

        cls.author = User.objects.create_user(
            username='Автор',
            password='au123',
        )
        cls.reader = User.objects.create_user(
            username='Читатель',
            password='re123',
        )

        cls.note = Note.objects.create(
            title=cls.TITLE,
            text=cls.TEXT,
            author=cls.author,
            slug=cls.SLUG,
        )

    # по рекомендация ИИ исходя из логики тестирования контента ушёл от
    # force_login, так как здесь лучше полноценная аутентификация,
    # а не присвоение
    @classmethod
    def _create_logged_client(cls, user, password):
        """Создаёт авторизированного клиента через client.login."""
        client = cls.client_class()

        success = client.login(username=user.username, password=password)
        if not success:
            raise RuntimeError(
                f"Не удалось залогинить пользователя {user.username}.")

        return client

    @classmethod
    def setUpClass(cls):
        """Инициализация клиентов и динамического URL."""
        super().setUpClass()

        cls.client = cls.client_class()   # Анонимный клиент
        cls.author_client = cls._create_logged_client(cls.author, "au123")
        cls.reader_client = cls._create_logged_client(cls.reader, "re123")

        cls.EDIT_URL = reverse("notes:edit", args=(cls.note.slug,))
        cls.DEL_URL = reverse("notes:delete", args=(cls.note.slug,))

        cls.form_data = {
            'title': cls.TITLE,
            'text': cls.TEXT,
            'slug': cls.SLUG,
        }
        cls.form_data_without_slug = {
            'title': cls.TITLE,
            'text': cls.TEXT,
        }


class TestNoteContent(BaseNoteTest):
    """
    Тестирование отображения контента на страницах приложения.

    Проверяется:
      * изоляция заметок между пользователями;
      * корректная передача заметок в контекст страниц;
      * передача форм на соответствующие страницы.
    """

    def assert_response_ok(self, response):
        """Проверяет, что ответ имеет статус 200 OK."""
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def assert_form_in_context(self, response, form_class=NoteForm):
        """Проверка наличия формы в контексте и её типа."""
        self.assertIn("form", response.context)

        form = response.context["form"]

        self.assertIsInstance(form, form_class)

    def assert_note_in_list(self, response, note):
        """Проверка, что заметка есть в object_list."""
        object_list = response.context.get("object_list")

        self.assertIsNotNone(object_list)
        self.assertIn(note, object_list)

    def assert_note_not_in_list(self, response, note):
        """Проверка, что заметки нет в object_list."""
        object_list = response.context.get("object_list")

        self.assertIsNotNone(object_list)
        self.assertNotIn(note, object_list)

    def test_notes_list_for_author(self):
        """Автор видит свои заметки на странице списка."""
        response = self.author_client.get(self.LIST_URL)

        self.assert_response_ok(response)
        self.assert_note_in_list(response, self.note)

    def test_not_notes_list_for_reader(self):
        """Авторизированный клиент не видит чужие заметки."""
        response = self.reader_client.get(self.LIST_URL)

        self.assert_response_ok(response)
        self.assert_note_not_in_list(response, self.note)

    def test_create_form_is_present(self):
        """Тест формы на странице создания заметки."""
        response = self.author_client.get(self.ADD_URL)

        self.assert_response_ok(response)
        self.assert_form_in_context(response)

    def test_edit_form_initial_data(self):
        """Тест формы на странице редактирования заметки."""
        response = self.author_client.get(self.EDIT_URL)

        self.assert_response_ok(response)
        self.assert_form_in_context(response, form_class=NoteForm)

        form = response.context["form"]

        self.assertEqual(form.initial["title"], self.TITLE)
        self.assertEqual(form.initial["text"], self.TEXT)
        self.assertEqual(form.initial.get("slug"), self.SLUG)

    def test_single_note_appears_once_with_all_fields(self):
        """Соответствие количества переданых заметок отображаемым."""
        response = self.author_client.get(self.LIST_URL)

        self.assert_response_ok(response)

        object_list = response.context.get("object_list")

        self.assertIsNotNone(object_list)
        self.assertEqual(len(object_list), 1)
