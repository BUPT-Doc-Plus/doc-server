import json
import threading
import requests
from django.db.models import Q
from typing import Dict, Iterable, List, Set, Tuple
from doc_server import settings
from django.db.models.query import QuerySet
from doc.models import Author, Chat, CollaborateToken, Message, ReadToken, Token, Doc, Access, DocTree
from doc.serializers import AuthorSerializer, ChatSerializer, DocAccessSerializer, DocSerializer
from doc.exceptions import BizException
from django.core.mail import send_mail
from doc.utils import (
    gen_token, now,
    parse_email,
    gen_valid_code,
    val_valid_code,
    trim_doc_tree,
    extract_doc_from_root,
    digest)
from doc_server import settings

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
        tks = Token.objects.filter(author=author)
        if len(tks):
            tk = tks[0]
            tk = Token.objects.get(author=author)
            tk.content = token
            tk.save()
        else:
            tk = Token.objects.create(author=author, content=token)
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
                prev_token: Token = previous_tokens[0]
                prev_token.timestamp = now()
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

def get_doc(doc_id: int, request_author: Author, token: str = None) -> Doc:
    '''
    获取文档信息
    '''
    docs: Iterable[Doc] = Doc.objects.filter(pk=doc_id)
    if len(docs) == 0:
        raise BizException("common.not_found")
    doc = docs[0]
    if token is not None:
        reads = ReadToken.objects.filter(content=token)
        if len(reads):
            grant_doc_to_author(doc.id, request_author.pk, 0, doc.get_creator())
        colls = CollaborateToken.objects.filter(content=token)
        if len(colls):
            grant_doc_to_author(doc.id, request_author.pk, 1, doc.get_creator())
    if Access.can_read(request_author, doc):
        return doc
    raise BizException("doc.not_r")

def get_doc_batch(doc_ids: List[int], from_tos: List[str], request_author: Author) -> QuerySet:
    '''
    批量获取文档信息
    '''
    doc_ids: Set = set(doc_ids)
    for ft in from_tos:
        f, t = ft.split("-")
        f, t = int(f), int(t)
        doc_ids = doc_ids.union(list(range(f, t + 1)))
    doc_ids = list(doc_ids)
    valid_doc_ids = []
    for doc_id in doc_ids:
        try:
            query_access(request_author.pk, doc_id, request_author)
            valid_doc_ids.append(doc_id)
        except:
            pass
    return Doc.objects.filter(pk__in=valid_doc_ids)

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
    if Access.can_dominate(request_author, doc):
        doc.delete()
        return doc
    elif Access.can_collaborate(request_author, doc) or Access.can_read(request_author, doc):
        Access.objects.filter(author=request_author, doc=doc).delete()
        return doc
    else:
        raise BizException("doc.not_d")

def del_doc_batch(doc_ids: List[int], from_tos: List[str], request_author: Author) -> Dict:
    '''
    批量删除文档
    '''
    doc_ids: Set = set(doc_ids)
    for ft in from_tos:
        f, t = ft.split("-")
        f, t = int(f), int(t)
        doc_ids = doc_ids.union(list(range(f, t + 1)))
    doc_ids = list(doc_ids)
    to_del = []
    to_unlink = []
    denied = []
    for doc_id in doc_ids:
        try:
            access = query_access(request_author.pk, doc_id, request_author)
            if access.role == 2:
                to_del.append(doc_id)
            else:
                to_unlink.append(doc_id)
        except BizException:
            denied.append(doc_id)
    Doc.objects.filter(pk__in=to_del).delete()
    Access.objects.filter(author=request_author, doc_id__in=to_unlink).delete()
    return { "deleted": to_del, "unlinked": to_unlink, "denied": denied }

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
    data = {
        "type": "invite",
        "doc": DocSerializer(doc).data,
        "author": AuthorSerializer(author).data
    }
    threading.Thread(target=requests.post,
        args=("{}/invite_or_kick".format(settings.MID_HOST),),
        kwargs={"data": {"data": json.dumps(data)}}).start()
    data = DocAccessSerializer(access).data
    threading.Thread(target=requests.post,
        args=("{}/access_change".format(settings.MID_HOST),),
        kwargs={"data": {"data": json.dumps(data)}}).start()
    return doc

def cancel_access_to_doc(doc_id: int, author_id: int, request_author: Author) -> Doc:
    '''
    取消某用户对某文档的所有权限
    '''
    if doc_id is None or author_id is None:
        raise BizException("common.bad_request")
    doc = get_doc(doc_id, request_author)
    author = get_author(author_id)
    data = {
        "type": "kick",
        "doc": DocSerializer(doc).data,
        "author": AuthorSerializer(author).data
    }
    if Access.can_dominate(request_author, doc):
        # 不能取消创建者的权限
        if author_id == request_author.pk:
            raise BizException("doc.cannot_edit_d")
        Access.objects.filter(doc_id=doc_id, author_id=author_id).delete()
        threading.Thread(target=requests.post,
            args=("{}/invite_or_kick".format(settings.MID_HOST),),
            kwargs={"data": {"data": json.dumps(data)}}).start()
        return doc
    # 非创建者只能取消自己的权限
    if author_id != request_author.pk:
        raise BizException("doc.forbidden_cancel")
    Access.objects.filter(doc_id=doc_id, author_id=author_id).delete()
    threading.Thread(target=requests.post,
        args=("{}/invite_or_kick".format(settings.MID_HOST),),
        kwargs={"data": {"data": json.dumps(data)}}).start()
    return doc

def complete_doc_tree(tree: DocTree, author: Author) -> None:
    root = json.loads(tree.content)
    docs_in_tree = extract_doc_from_root(root)
    all_docs = set([item["doc_id"] for item in Access.objects.filter(author=author).values("doc_id")])
    sup_docs = all_docs.difference(docs_in_tree)
    if len(sup_docs) == 0:
        return
    sup_docs: Iterable[Doc] = Doc.objects.filter(pk__in=sup_docs)
    for sup_doc in sup_docs:
        key = digest(sup_doc.label + "-" + str(sup_doc.pk), iter=1)
        root["children"][key] = {"id": sup_doc.pk}
    tree.content = json.dumps(root, ensure_ascii=False)
    tree.save()

def get_doc_tree_of(author_id: int, request_author: Author) -> DocTree:
    '''
    获取用户的文档树
    '''
    if request_author is None or request_author.pk != author_id:
        raise BizException("common.forbidden")
    trees = DocTree.objects.filter(author_id=author_id)
    if len(trees) == 0:
        tree = DocTree.objects.create(author_id=author_id)
        complete_doc_tree(tree, request_author)
        return tree
    complete_doc_tree(trees[0], request_author)
    return trees[0]

def save_doc_tree(author_id: int, content: str, request_author: Author) -> DocTree:
    '''
    保存用户的文档树
    '''
    if content is None:
        raise BizException("common.bad_request")
    if request_author.pk != author_id:
        raise BizException("common.forbidden")
    content = trim_doc_tree(content)
    tree = get_doc_tree_of(author_id, request_author)
    tree.content = content
    tree.save()
    return tree

def query_access(author_id: int, doc_id: int, request_author: Author) -> Access:
    '''
    查询权限
    '''
    u_accesses = Access.objects.filter(author=request_author, doc_id=doc_id)
    if len(u_accesses) == 0:
        # 不允许查询没有任何权限的文档
        raise BizException("common.forbidden")
    accesses = Access.objects.filter(author_id=author_id, doc_id=doc_id)
    if len(accesses) == 0:
        raise BizException("common.not_found")
    return accesses[0]

def search_doc(keywords: str, request_author: Author) -> QuerySet:
    '''
    搜索文档
    '''
    result = []
    if keywords is None or keywords.strip() == "":
        return result
    for role in range(3):
        res = get_doc_by_author_with_role(request_author.pk, role, request_author).filter(label__icontains=keywords)
        result.extend(res)
    return result

def get_chat_by_id(chat_id: int, request_author: Author) -> Chat:
    '''
    根据id获取chat
    '''
    chats = Chat.objects.filter(pk=chat_id)
    if len(chats) == 0:
        raise BizException("common.not_found")
    chat: Chat = chats[0]
    if request_author.pk != chat.initiator.pk and request_author.pk != chat.recipient.pk:
        raise BizException("chat.cannot_read")
    return chat

def get_or_create_chat(author_id1: int, author_id2: int, request_author: Author) -> Iterable:
    '''
    根据双方获取聊天, 没有则创建新聊天
    '''
    if request_author.pk != author_id1 and author_id2 is not None and request_author.pk != author_id2:
        raise BizException("chat.cannot_read")
    if author_id2 is not None:
        chats = Chat.objects.filter(Q(initiator_id=author_id1) & Q(recipient_id=author_id2) |
                            Q(initiator_id=author_id2) & Q(recipient_id=author_id1))
        if len(chats) == 0:
            recipient_id = author_id1 if author_id2 == request_author.pk else author_id2
            chat = Chat.objects.create(initiator_id=request_author.pk, recipient_id=recipient_id)
        else:
            chat = chats[0]
        return [chat]
    chats = Chat.objects.filter(Q(initiator_id=author_id1) | Q(recipient_id=author_id1))
    return chats

def send_message(sender_id: int, receiver_id: int, msg: str, request_author: Author) -> Message:
    '''
    发送消息
    '''
    chat = get_or_create_chat(sender_id, receiver_id, request_author)[0]
    message = Message.objects.create(chat=chat, sender_id=sender_id, receiver_id=receiver_id, msg=msg)
    return message

def get_records(chat_id: int, page: int, page_size: int, request_author: Author) -> Message:
    '''
    根据id列表分页地获取消息
    '''
    chats = Chat.objects.filter(pk=chat_id)
    if len(chats) == 0:
        raise BizException("common.not_found")
    chat: Chat = chats[0]
    rows = Message.objects.filter(chat=chat).values_list("id")
    ids = [row[0] for row in rows]
    ids.reverse()
    ids = ids[page_size*page:page_size*(page+1)]
    messages = Message.objects.filter(pk__in=ids).filter(Q(sender=request_author)|Q(receiver=request_author))
    return messages

def get_invite_link(doc_id: int, auth: str, request_author: Author) -> str:
    '''
    获取邀请链接
    '''
    doc = get_doc(doc_id, request_author)
    if auth == "read":
        tokens = ReadToken.objects.filter(doc=doc)
        if len(tokens):
            token = tokens[0]
        else:
            token = ReadToken.objects.create(doc=doc)
    elif auth == "collaborate":
        tokens = CollaborateToken.objects.filter(doc=doc)
        if len(tokens):
            token = tokens[0]
        else:
            token = CollaborateToken.objects.create(doc=doc)
    link = settings.FRONT_HOST + "/#/invite/{}/{}"
    link = link.format(doc_id, token.content)
    return link
