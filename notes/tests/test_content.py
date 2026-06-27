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

    TEXT_1 = "Текст заметки."
    TITLE_1 = "Заголовок заметки."
    SLUG_1 = "test-note-1"

    ADD_URL = reverse("notes:add")
    LIST_URL = reverse("notes:list")

    @classmethod
    def setUpTestData(cls):
        """Подготовка данных для тестов. Создаются пользователи и заметка."""
        super().setUpTestData()

        cls.author = User.objects.create_user(
            username="Автор",
            password="au123",
        )
        cls.reader = User.objects.create_user(
            username="Читатель",
            password="re123",
        )

        cls.note_1 = Note.objects.create(
            title=cls.TITLE_1,
            text=cls.TEXT_1,
            author=cls.author,
            slug=cls.SLUG_1,
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

        cls.anon_client = cls.client_class()   # Анонимный клиент

        cls.author_client = cls._create_logged_client(cls.author, "au123")
        cls.reader_client = cls._create_logged_client(cls.reader, "re123")

        cls.EDIT_URL = reverse("notes:edit", args=(cls.note_1.slug,))

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


class TestNoteContent(BaseNoteTest):
    """
    Тестирование отображения контента на страницах приложения.

    Проверяется:
      * изоляция заметок между пользователями;
      * корректная передача заметок в контекст страниц;
      * передача форм на соответствующие страницы.
    """

    def test_notes_list_for_author(self):
        """Автор видит свои заметки на странице списка."""
        response = self.author_client.get(self.LIST_URL)

        self.assert_response_ok(response)
        self.assert_note_in_list(response, self.note_1)

    def test_not_notes_list_for_reader(self):
        """Авторизированный клиент не видит чужие заметки."""
        response = self.reader_client.get(self.LIST_URL)

        self.assert_response_ok(response)
        self.assert_note_not_in_list(response, self.note_1)

    def test_create_form_is_present(self):
        """Тест формы на странице создания заметки."""
        response = self.author_client.get(self.ADD_URL)

        self.assert_response_ok(response)
        self.assert_form_in_context(response)

    def test_edit_form_initial_data(self):
        """Тест формы на странице редактирования заметки."""
        response = self.author_client.get(self.EDIT_URL)

        self.assert_response_ok(response)
        self.assert_form_in_context(response)

        form = response.context["form"]

        self.assertEqual(form.initial["title"], self.TITLE_1)
        self.assertEqual(form.initial["text"], self.TEXT_1)
        self.assertEqual(form.initial.get("slug"), self.SLUG_1)

    def test_single_note_appears_once_with_all_fields(self):
        """Соответствие количества переданых заметок отображаемым."""
        response = self.author_client.get(self.LIST_URL)

        self.assert_response_ok(response)

        object_list = response.context.get("object_list")

        self.assertIsNotNone(object_list)
        self.assertEqual(len(object_list), 1)
