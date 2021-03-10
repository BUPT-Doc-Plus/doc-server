from typing import Iterable
from doc.models import Author, Doc, Access, DocTree, Chat, Message
from rest_framework import serializers

class AuthorRelatedExpandedField(serializers.RelatedField):
    def to_representation(self, value):
        return AuthorSerializer(value).data


class ChatRelatedExpandedField(serializers.RelatedField):
    def to_representation(self, value):
        return ChatSerializer(value).data

class DocAccessSerializer(serializers.HyperlinkedModelSerializer):
    author = AuthorRelatedExpandedField(read_only=True)
    class Meta:
        model = Access
        fields = ["author", "role", "doc_id"]


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


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    sender = AuthorRelatedExpandedField(read_only=True)
    receiver = AuthorRelatedExpandedField(read_only=True)
    class Meta:
        model = Message
        fields = ["chat_id", "sender", "receiver", "msg", "time"]


class ChatRecordsField(serializers.RelatedField):
    def to_representation(self, value):
        return [val[0] for val in value.values_list("id")]


class ChatSerializer(serializers.HyperlinkedModelSerializer):
    initiator = AuthorRelatedExpandedField(read_only=True)
    recipient = AuthorRelatedExpandedField(read_only=True)
    records = ChatRecordsField(read_only=True)
    class Meta:
        model = Chat
        fields = ["id", "initiator", "recipient", "time", "records"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["preview"] = MessageSerializer(Message.objects.get(pk=data["records"][-1])).data
        return data
