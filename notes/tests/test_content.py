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
from http import HTTPStatus  # type: ignore

from django.contrib.auth import get_user_model  # type: ignore
from django.test import TestCase, Client  # type: ignore
from django.urls import reverse  # type: ignore

from notes.models import Note
from notes.forms import NoteForm

User = get_user_model()


class TestNoteContent(TestCase):
    """
    Тестирование отображения контента на страницах приложения.

    Проверяется:
    * корректная передача заметок в контекст страниц;
    * изоляция заметок между пользователями;
    * передача форм на соответствующие страницы.
    """

    TEXT_1 = 'Текст заметки'
    TITLE_1 = 'Заголовок заметки'
    TEXT_2 = 'Текст другой заметки'
    TITLE_2 = 'Заголовок другой заметки'
    SLUG_1 = 'test-note-1'
    SLUG_2 = 'test-note-2'

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
        cls.note_1 = Note.objects.create(
            title=cls.TITLE_1,
            text=cls.TEXT_1,
            author=cls.author,
            slug=cls.SLUG_1
        )
        cls.note_2 = Note.objects.create(
            title=cls.TITLE_2,
            text=cls.TEXT_2,
            author=cls.reader,
            slug=cls.SLUG_2
        )
        cls.add_url = reverse('notes:add', None)
        cls.list_url = reverse('notes:list', None)
        cls.edit_url = reverse('notes:edit', args=(cls.note_1.slug,))

    def test_notes_list_for_different_users(self):
        """Тест заметок разных пользователей, на странице списка заметок."""
        response = self.author_client.get(self.list_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        object_list = response.context['object_list']
        self.assertIn(self.note_1, object_list)
        self.assertNotIn(self.note_2, object_list)

        response = self.reader_client.get(self.list_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        object_list = response.context['object_list']
        self.assertIn(self.note_2, object_list)
        self.assertNotIn(self.note_1, object_list)

    def test_creat_abd_edit_form(self):
        """Тест формы на страницвх: создания и редактирования заметок."""
        response = self.author_client.get(self.add_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn('form', response.context)

        form = response.context['form']
        self.assertIsInstance(form, NoteForm)

        response = self.author_client.get(self.edit_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn('form', response.context)

        edit_form = response.context['form']
        self.assertEqual(edit_form.initial['title'], self.TITLE_1)
        self.assertEqual(edit_form.initial['text'], self.TEXT_1)
        self.assertEqual(edit_form.initial.get('slug'), self.SLUG_1)
