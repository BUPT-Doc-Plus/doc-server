from typing import Iterable
from doc.models import Author, Doc, Access
from rest_framework import serializers

class DocAccessSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Access
        fields = ["author_id", "role"]


class DocAccessListField(serializers.RelatedField):
    def to_representation(self, value: Access):
        return DocAccessSerializer(value).data


class AuthorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "email", "nickname"]


class DocSerializer(serializers.HyperlinkedModelSerializer):
    doc_accessible = DocAccessListField(read_only=True, many=True)
    class Meta:
        model = Doc
        fields = ["id", "label", "type", "doc_accessible"]
