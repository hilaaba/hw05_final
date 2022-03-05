from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': _('Текст поста'),
            'group': _('Группа'),
            'image': _('Изображение')
        }
        help_texts = {
            'text': _('Текст нового поста'),
            'group': _('Группа, к которой будет относиться пост'),
            'image': _('Добавьте изображение к посту')
        }

    def clean_text(self):
        data = self.cleaned_data['text']
        if not data:
            raise forms.ValidationError('Нужно заполнить поле.')
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': _('Комментарий'),
        }
        help_texts = {
            'text': _('Оставьте комментарий'),
        }

    def clean_text(self):
        data = self.cleaned_data['text']
        if not data:
            raise forms.ValidationError('Нужно заполнить поле.')
        return data
