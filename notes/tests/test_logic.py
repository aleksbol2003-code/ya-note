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


class TestNoteLogic(TestCase):
    """
    Тестирование маршрутов и логики приложения YaNote.

    Проверяется:
    * создание заметок, работа slug (автогенерация, уникальность);
    * возможность редактирование и удаление заметок автором и другими;
    * проверка прав автора и др. пользователей.
    """

    TEXT = 'Текст заметки'
    TITLE = 'Заголовок заметки'
    NEW_TEXT = 'Новый текст заметки'
    NEW_TITLE = 'Новый заголовок заметки'
    SLUG = 'test-note'
    NEW_SLUG = 'updated-note'

    @classmethod
    def setUpTestData(cls):
        """Подготовка тестовых данных, создание пользователей, заметки и др."""
        cls.author = User.objects.create_user(
            username='Автор',
            password='au123',
        )
        cls.reader = User.objects.create_user(
            username='Читатель',
            password='re123',
        )

        # здесь оставил присвоение request.user = user без аутентификации
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)

        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)

        cls.client = Client()  # аноним

        cls.note = Note.objects.create(
            title=cls.TITLE,
            text=cls.TEXT,
            author=cls.author,
            slug=cls.SLUG,
        )

        cls.add_url = reverse('notes:add')
        cls.done_url = reverse('notes:success')

        cls.form_data = {
            'title': cls.TITLE,
            'text': cls.TEXT,
            'slug': cls.SLUG,
        }
        cls.form_data_without_slug = {
            'title': cls.TITLE,
            'text': cls.TEXT,
        }

    def test_author_can_create_note_with_slug(self):
        """Проверка успешного создания заметки пользователем (автор)."""
        form_data = {
            'title': self.TITLE,
            'text': self.TEXT,
            'slug': 'unique_slug',
        }
        response = self.author_client.post(
            self.add_url, data=form_data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        note = Note.objects.filter(
            slug=self.form_data['slug']).first()

        self.assertIsNotNone(note)
        self.assertEqual(Note.objects.count(), 2)
        self.assertEqual(note.title, form_data['title'])
        self.assertEqual(note.text, form_data['text'])
        self.assertEqual(note.author, self.author)

    def test_note_created_with_auto_slug(self):
        """Проверка создания заметки без указания slug."""
        response = self.author_client.post(
            self.add_url, data=self.form_data_without_slug)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        self.assertEqual(Note.objects.count(), 2)

        note = Note.objects.latest('id')

        self.assertIsNotNone(note.slug)
        self.assertNotEqual(note.slug, '')
        self.assertEqual(note.title, self.form_data_without_slug['title'])

    def test_cannot_create_note_with_non_unique_slug(self):
        """Тест создания заметок с неуникальным slug."""
        self.author_client.post(self.add_url, data=self.form_data)

        response = self.author_client.post(self.add_url, data=self.form_data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Note.objects.count(), 1)

    def test_anon_cannot_create_notes(self):
        """Тест создания заметки анонимным пользователем."""
        form_data = {
            'title': self.TITLE,
            'text': self.TEXT,
            'slug': 'slug',
        }
        response = self.client.post(self.add_url, data=form_data)

        self.assertRedirects(response, "/auth/login/?next=/add/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertFalse(Note.objects.filter(
            slug=form_data['slug']).exists())

    def test_author_can_edit_note(self):
        """Автор может редактировать заметку через страницу редактирования."""
        new_data = {
            'title': self.NEW_TITLE,
            'text': self.NEW_TEXT,
            'slug': self.NEW_SLUG,
        }
        edit_url = reverse('notes:edit', args=(self.note.slug,))
        response = self.author_client.post(edit_url, data=new_data)

        self.assertRedirects(response, self.done_url)

        updated_note = Note.objects.get(id=self.note.id)

        self.assertEqual(Note.objects.count(), 1)

        self.assertEqual(updated_note.title, new_data['title'])
        self.assertEqual(updated_note.text, new_data['text'])
        self.assertEqual(updated_note.slug, new_data['slug'])

        self.assertEqual(updated_note.author, self.author)

    def test_reader_cannot_edit_other_note(self):
        """Читатель не может редактировать чужую заметку."""
        new_data = {
            'title': self.NEW_TITLE,
            'text': self.NEW_TEXT,
            'slug': self.NEW_SLUG,
        }
        edit_url = reverse('notes:edit', args=(self.note.slug,))
        response = self.reader_client.post(edit_url, data=new_data)

        self.assertIn(
            response.status_code, (HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND))

        note = Note.objects.get(id=self.note.id)

        self.assertEqual(note.title, self.TITLE)
        self.assertEqual(note.text, self.TEXT)

        self.assertEqual(note.author, self.author)

        self.assertEqual(Note.objects.count(), 1)

    def test_author_can_delete_own_note(self):
        """Автор может удалять заметку через страницу подтверждения."""
        del_url = reverse('notes:delete', args=(self.note.slug,))
        response = self.author_client.post(del_url)

        self.assertRedirects(response, self.done_url)
        self.assertFalse(Note.objects.filter(id=self.note.id).exists())

    def test_reader_cannot_delete_other_note(self):
        """Читатель не может удалять чужую заметку."""
        del_url = reverse('notes:delete', args=(self.note.slug,))
        response = self.reader_client.get(del_url)

        self.assertIn(response.status_code, (
            HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND))

        post_response = self.reader_client.post(del_url)
        self.assertIn(post_response.status_code, (
            HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND))

        self.assertTrue(Note.objects.filter(id=self.note.id).exists())
