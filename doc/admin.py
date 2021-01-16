from django.contrib import admin
from doc.models import Author, Doc, Access, Token, DocTree

# Register your models here.
admin.site.register(Author)
admin.site.register(Doc)
admin.site.register(Access)
admin.site.register(Token)
admin.site.register(DocTree)