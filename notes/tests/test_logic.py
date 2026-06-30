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

from notes.models import Note
from notes.tests.test_content import BaseNoteTest

User = get_user_model()


class TestNoteLogic(BaseNoteTest):
    """
    Тестирование маршрутов и логики приложения YaNote.

    Проверяется:
    * создание заметок, работа slug (автогенерация, уникальность);
    * возможность редактирование и удаление заметок автором и другими;
    * проверка прав автора и др. пользователей.
    """

    def test_author_can_create_note_with_slug(self):
        """Проверка успешного создания заметки пользователем (автор)."""
        form_data = {
            'title': self.TITLE,
            'text': self.TEXT,
            'slug': 'unique_slug',
        }

        self.assertEqual(Note.objects.count(), 1)
        id_note_before = set(Note.objects.values_list("id", flat=True))

        response = self.author_client.post(self.ADD_URL, data=form_data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Note.objects.count(), 2)

        id_note_after = set(Note.objects.values_list("id", flat=True))
        new_id = (id_note_after - id_note_before).pop()

        note = Note.objects.get(id=new_id)

        self.assertEqual(note.title, form_data['title'])
        self.assertEqual(note.text, form_data['text'])
        self.assertEqual(note.slug, form_data["slug"])
        self.assertEqual(note.author, self.author)

    def test_note_created_with_auto_slug(self):
        """Проверка создания заметки без указания slug."""
        self.assertEqual(Note.objects.count(), 1)
        id_note_before = set(Note.objects.values_list("id", flat=True))

        response = self.author_client.post(
            self.ADD_URL, data=self.form_data_without_slug)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Note.objects.count(), 2)

        id_note_after = set(Note.objects.values_list("id", flat=True))
        new_id = (id_note_after - id_note_before).pop()

        note = Note.objects.get(id=new_id)

        self.assertIsNotNone(note.slug)
        self.assertNotEqual(note.slug, '')
        self.assertEqual(note.title, self.form_data_without_slug['title'])
        self.assertEqual(note.text, self.form_data_without_slug['text'])
        self.assertEqual(note.author, self.author)

    def test_cannot_create_note_with_non_unique_slug(self):
        """Тест создания заметок с неуникальным slug."""
        self.assertEqual(Note.objects.count(), 1)

        response = self.author_client.post(self.ADD_URL, data=self.form_data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Note.objects.count(), 1)

        note = Note.objects.get()

        self.assertEqual(note.title, self.form_data['title'])
        self.assertEqual(note.text, self.form_data['text'])
        self.assertEqual(note.slug, self.form_data["slug"])
        self.assertEqual(note.author, self.author)

    def test_anon_cannot_create_notes(self):
        """Тест создания заметки анонимным пользователем."""
        form_data = {
            'title': self.TITLE,
            'text': self.TEXT,
            'slug': 'slug',
        }

        self.assertEqual(Note.objects.count(), 1)

        response = self.client.post(self.ADD_URL, data=form_data)
        self.assertRedirects(response, "/auth/login/?next=/add/")

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Note.objects.count(), 1)

        self.assertFalse(Note.objects.filter(
            slug=form_data['slug']).exists())

    def test_author_can_edit_note(self):
        """Автор может редактировать заметку через страницу редактирования."""
        self.assertEqual(Note.objects.count(), 1)

        response = self.author_client.post(self.EDIT_URL, data=self.new_data)
        self.assertRedirects(response, self.DONE_URL)

        self.assertEqual(Note.objects.count(), 1)

        updated_note = Note.objects.get()  # self.note.id

        self.assertEqual(updated_note.title, self.new_data['title'])
        self.assertEqual(updated_note.text, self.new_data['text'])
        self.assertEqual(updated_note.slug, self.new_data['slug'])
        self.assertEqual(updated_note.author, self.author)

    def test_reader_cannot_edit_other_note(self):
        """Читатель не может редактировать чужую заметку."""
        self.assertEqual(Note.objects.count(), 1)

        response = self.reader_client.post(self.EDIT_URL, data=self.new_data)

        self.assertIn(
            response.status_code, (HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND))
        self.assertEqual(Note.objects.count(), 1)

        note = Note.objects.get()  # self.note.id

        self.assertEqual(note.title, self.note.title)
        self.assertEqual(note.text, self.note.text)
        self.assertEqual(note.slug, self.note.slug)
        self.assertEqual(note.author, self.author)

    def test_author_can_delete_own_note(self):
        """Автор может удалять заметку через страницу подтверждения."""
        self.assertEqual(Note.objects.count(), 1)

        response = self.author_client.post(self.DEL_URL)

        self.assertEqual(Note.objects.count(), 0)

        self.assertRedirects(response, self.DONE_URL)
        self.assertFalse(Note.objects.filter(id=self.note.id).exists())

    def test_reader_cannot_delete_other_note(self):
        """Читатель не может удалять чужую заметку."""
        self.assertEqual(Note.objects.count(), 1)

        response = self.reader_client.get(self.DEL_URL)

        self.assertIn(response.status_code, (
            HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND))
        self.assertEqual(Note.objects.count(), 1)

        post_response = self.reader_client.post(self.DEL_URL)
        self.assertIn(post_response.status_code, (
            HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND))
        self.assertEqual(Note.objects.count(), 1)

        note = Note.objects.get()  # self.note.id

        self.assertEqual(note.title, self.note.title)
        self.assertEqual(note.text, self.note.text)
        self.assertEqual(note.slug, self.note.slug)
        self.assertEqual(note.author, self.author)

        self.assertTrue(Note.objects.filter(id=self.note.id).exists())
