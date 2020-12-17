from typing import Dict, Iterable, List
from django.db.models.query import QuerySet
from doc.models import Author, Token, Doc, Access
from doc.serializers import AuthorSerializer, DocSerializer
from doc.utils import serialized, success_response
from doc.exceptions import BizException

def get_authors(nickname: str) -> QuerySet:
    '''
    用户列表
    '''
    if nickname is None:
        return Author.objects.all()
    return Author.objects.filter(nickname=nickname)

def author_register(data: Dict) -> Author:
    '''
    用户注册
    '''
    srlzr = AuthorSerializer(data=data)
    if srlzr.is_valid():
        author = srlzr.save()
        pwd = data.get("password")
        if pwd is None:
            raise BizException("common.bad_request")
        author.set_password(pwd)
        author.save()
        return author
    raise BizException("common.bad_request", srlzr.errors)

def get_author(author_id: int) -> Author:
    '''
    获取用户信息
    '''
    authors = Author.objects.filter(pk=author_id)
    if len(authors) == 0:
        raise BizException("common.not_found")
    return authors[0]

def edit_author_profile(author_id: int, data: Dict, request_author: Author) -> Author:
    '''
    修改用户信息
    '''
    author = get_author(author_id)
    if request_author != author:
        raise BizException("profile.forbidden")
    srlzr = AuthorSerializer(author, data=data)
    if srlzr.is_valid():
        author = srlzr.save()
        return author
    raise BizException("common.bad_request", srlzr.errors)

def login(email: str, password: str) -> str:
    '''
    获取令牌（登录）
    '''
    if email is None or password is None:
        raise BizException("common.bad_request")
    authors: Iterable[Author] = Author.objects.filter(email=email)
    if len(authors) == 0:
        raise BizException("login.wrong")
    author = authors[0]
    if author.active:
        if author.check_password(password):
            previous_tokens: Iterable[Token] = Token.objects.filter(author=author)
            if len(previous_tokens) == 0:
                token = Token.objects.create(author=author).content
            else:
                prev_token = previous_tokens[0]
                prev_token.content = Token.generate()
                prev_token.save()
                token = prev_token.content
            return token
        raise BizException("login.wrong")
    raise BizException("login.inactive")

def get_doc_by_author_with_role(author_id: int, role: str, request_author: Author) -> QuerySet:
    '''
    获取用户以特定角色加入的文档的列表
    '''
    authors = Author.objects.filter(pk=author_id)
    if len(authors) == 0:
        raise BizException("common.not_found")
    author = authors[0]
    if author != request_author:
        raise BizException("common.forbidden")
    accesses = Access.objects.filter(role=role, author=author)
    doc_ids = accesses.values_list("doc_id")
    docs = Doc.objects.filter(pk__in=doc_ids)
    return docs

def create_doc(doc_data: Dict, author_id: int, request_author: Author) -> Doc:
    '''
    创建文档
    '''
    if request_author is None or request_author.pk != author_id:
        raise BizException("common.forbidden")
    authors = Author.objects.filter(pk=author_id)
    if len(authors) == 0:
        raise BizException("common.not_found")
    author = authors[0]
    srlzr = DocSerializer(data=doc_data)
    if srlzr.is_valid():
        doc = srlzr.save()
        access = Access.objects.create(author=author, doc=doc, mod=2)
        access.save()
        return doc
    raise BizException("common.bad_request", srlzr.errors)

def get_doc(doc_id: int, request_author: Author) -> Doc:
    '''
    获取文档信息
    '''
    docs: Iterable[Doc] = Doc.objects.filter(pk=doc_id)
    if len(docs) == 0:
        raise BizException("common.not_found")
    doc = docs[0]
    if Access.can_read(request_author, doc):
        return doc
    raise BizException("doc.not_r")

def edit_doc_info(doc_id: int, data: Dict, request_author: Author) -> Doc:
    '''
    修改文档信息
    '''
    doc = get_doc(doc_id, request_author)
    if not Access.can_dominate(request_author, doc):
        raise BizException("doc.not_d")
    srlzr = DocSerializer(doc, data)
    if srlzr.is_valid():
        doc = srlzr.save()
        return doc
    raise BizException("common.bad_request")

def delete_doc(doc_id: int, request_author: Author) -> Doc:
    '''
    删除文档
    '''
    doc = get_doc(doc_id, request_author)
    if not Access.can_dominate(request_author, doc):
        raise BizException("doc.not_d")
    doc.delete()
    return doc

def grant_doc_to_author(doc_id: int, author_id: int, role: int, request_author: Author) -> Doc:
    '''
    授予某用户对某文档的权限
    '''
    if doc_id is None or author_id is None or role is None:
        raise BizException("common.bad_request")
    doc = get_doc(doc_id, request_author)
    if not Access.can_dominate(request_author, doc):
        raise BizException("doc.not_d")
    if role == Access.DOMINATOR:
        raise BizException("doc.only_one_d")
    if role not in Access.VALID_ROLES:
        raise BizException("doc.invalid_role")
    author = get_author(author_id)
    access = Access.objects.create(doc=doc, author=author, mod=role)
    access.save()
    return doc
