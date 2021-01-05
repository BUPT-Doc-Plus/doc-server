from typing import Iterable
from doc.models import Author, Doc, Access, DocTree
from rest_framework import serializers

class AuthorRelatedExpandedField(serializers.RelatedField):
    def to_representation(self, value):
        return AuthorSerializer(value).data

class DocAccessSerializer(serializers.HyperlinkedModelSerializer):
    author = AuthorRelatedExpandedField(read_only=True)
    class Meta:
        model = Access
        fields = ["author", "role"]


class DocAccessListField(serializers.RelatedField):
    def to_representation(self, value: Access):
        return DocAccessSerializer(value).data


class AuthorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "email", "nickname", "active"]


class DocSerializer(serializers.HyperlinkedModelSerializer):
    doc_accessible = DocAccessListField(read_only=True, many=True)
    class Meta:
        model = Doc
        fields = ["id", "label", "type", "doc_accessible"]


class DocTreeSerializer(serializers.HyperlinkedModelSerializer):
    author = AuthorRelatedExpandedField(read_only=True)
    class Meta:
        model = DocTree
        fields = ["id", "author", "content", "timestamp"]