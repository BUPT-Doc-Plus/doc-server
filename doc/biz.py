from typing import Dict, Iterable, List
from doc_server import settings
from django.db.models.query import QuerySet
from doc.models import Author, Token, Doc, Access
from doc.serializers import AuthorSerializer, DocSerializer
from doc.utils import gen_token, serialized, success_response, parse_email, gen_valid_code, val_valid_code
from doc.exceptions import BizException
from django.core.mail import send_mail

def get_authors(keyword: str) -> QuerySet:
    '''
    用户列表
    '''
    if keyword is None:
        return Author.objects.all()
    nickname_result = Author.objects.filter(nickname__contains=keyword)
    email_result = Author.objects.filter(email__contains=keyword)
    return nickname_result.union(email_result)

def author_exists(email: str) -> Author:
    '''
    用户是否存在
    '''
    authors = Author.objects.filter(email=email)
    return authors[0] if len(authors) else None

def author_register(data: Dict) -> str:
    '''
    用户注册
    '''
    email = data["email"]
    password = data["password"]
    nickname = data["nickname"]
    authors = Author.objects.filter(email=email)
    if len(authors) == 0:
        srlzr = AuthorSerializer(data=data)
        if srlzr.is_valid():
            author = srlzr.save()
            pwd = data.get("password")
            if pwd is None:
                raise BizException("common.bad_request")
            author.set_password(pwd)
            author.save()
            token = Token.objects.create(author=author).content
            send_mail("DocPlus-欢迎来到DocPlus", parse_email(gen_valid_code(token), author.nickname), settings.DEFAULT_FROM_EMAIL, [author.email,])
            return token
        raise BizException("common.bad_request", srlzr.errors)
    elif not authors[0].active:
        author: Author = authors[0]
        author.nickname = nickname
        author.set_password(password)
        author.save()
        token = gen_token()
        tk = Token.objects.get(author=author)
        tk.content = token
        tk.save()
        send_mail("DocPlus-欢迎来到DocPlus", parse_email(gen_valid_code(token), author.nickname), settings.DEFAULT_FROM_EMAIL, [author.email,])
        return token
    else:
        raise BizException("register.duplicated")

def activate(valid_code: str, token: str) -> str:
    if val_valid_code(valid_code, token):
        author = Token.objects.get(content=token).author
        author.active = True
        author.save()
        return token
    else:
        raise BizException("login.invalid")

def get_author(author_id: int) -> Author:
    '''
    获取用户信息
    '''
    authors = Author.objects.filter(pk=author_id)
    if len(authors) == 0:
        raise BizException("common.not_found")
    return authors[0]

def get_author_by_token(token: str) -> Author:
    try:
        return Token.objects.get(content=token).author
    except:
        raise BizException("login.invalid")

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
        access = Access.objects.create(author=author, doc=doc, role=2)
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
    if Access.can_dominate(author, doc):
        raise BizException("doc.cannot_edit_d")
    existence = Access.objects.filter(doc=doc, author=author)
    if len(existence) == 0:
        access = Access.objects.create(doc=doc, author=author, role=role)
        access.save()
    else:
        access = existence[0]
        access.role = role
        access.save()
    return doc

def cancel_access_to_doc(doc_id: int, author_id: int, request_author: Author) -> Doc:
    '''
    取消某用户对某文档的所有权限
    '''
    if doc_id is None or author_id is None:
        raise BizException("common.bad_request")
    doc = get_doc(doc_id, request_author)
    if Access.can_dominate(request_author, doc):
        # 不能取消创建者的权限
        if author_id == request_author.pk:
            raise BizException("doc.cannot_edit_d")
        Access.objects.filter(doc_id=doc_id, author_id=author_id).delete()
        return doc
    # 非创建者只能取消自己的权限
    if author_id != request_author.pk:
        raise BizException("doc.forbidden_cancel")
    Access.objects.filter(doc_id=doc_id, author_id=author_id).delete()
    return doc
    