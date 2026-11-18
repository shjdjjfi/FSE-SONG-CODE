from django.db import models


class Son(models.Model):
    """The HEAD name of a model originally named Song."""


class SongProfile(models.Model):
    """An unrelated model whose name contains the former model name."""
