from time import time
from typing import Iterable
from django.db import models
from django.contrib.auth.models import AbstractUser
from doc.utils import gen_token, now, default_doc_tree


# Create your models here.
class Author(models.Model):
    active = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=128)
    password = models.CharField(max_length=128)
    REQUIRED_FIELDS = ["nickname"]
    USERNAME_FIELD = "email"

    def set_password(self, raw_password):
        AbstractUser.set_password(self, raw_password)
    
    def check_password(self, raw_password) -> bool:
        return AbstractUser.check_password(self, raw_password)
    
    @property
    def is_anonymous(self):
        return True
    
    @property
    def is_authenticated(self):
        return False


class Doc(models.Model):
    label = models.CharField(max_length=256, verbose_name="label", blank=True)
    type = models.CharField(max_length=32)
    recycled = models.BooleanField(default=False)


class Access(models.Model):
    author = models.ForeignKey(Author, related_name="author_accessible", on_delete=models.CASCADE)
    doc = models.ForeignKey(Doc, related_name="doc_accessible", on_delete=models.CASCADE)
    role = models.IntegerField(choices=[(0, 0), (1, 1), (2, 2)])

    DOMINATOR = 2
    VALID_ROLES = [0, 1, 2]

    @staticmethod
    def get_mod(author: Author, doc: Doc) -> int:
        if author is None or doc is None: return -1
        accesses: Iterable[Access] = Access.objects.filter(author=author, doc=doc)
        if len(accesses) == 0:
            return -1
        return accesses[0].role

    @staticmethod
    def can_read(author: Author, doc: Doc) -> bool:
        return Access.get_mod(author, doc) >= 0

    @staticmethod
    def can_collaborate(author: Author, doc: Doc) -> bool:
        return Access.get_mod(author, doc) >= 1

    @staticmethod
    def can_dominate(author: Author, doc: Doc) -> bool:
        return Access.get_mod(author, doc) >= 2

class Token(models.Model):
    author = models.OneToOneField(Author, related_name="author_token", on_delete=models.CASCADE)
    content = models.CharField(max_length=256, unique=True, default=gen_token)
    timestamp = models.IntegerField(default=now)

    def expired(self, duration) -> bool:
        return time() * 1000 - self.timestamp > duration
    
    @staticmethod
    def valid(s) -> Author:
        tokens: Iterable[Token] = Token.objects.filter(content=s)
        if len(tokens) == 0:
            return None
        token = tokens[0]
        if token.expired(2.592e+9):
            return None
        return token.author
    
    @staticmethod
    def generate() -> str:
        return gen_token()

class DocTree(models.Model):
    author = models.OneToOneField(Author, related_name="author_doc_tree", on_delete=models.CASCADE)
    content = models.TextField(default=default_doc_tree)
    timestamp = models.IntegerField(default=now)
