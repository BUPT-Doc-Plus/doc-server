from doc.models import Author, Token
from doc.serializers import AuthorSerializer, ChatSerializer, DocAccessSerializer, DocSerializer, DocTreeSerializer, MessageSerializer
from rest_framework.views import APIView
from rest_framework.request import Request
from doc.utils import api
from doc import biz

def u(request: Request) -> Author:
    s = request.query_params.get("token", None)
    return Token.valid(s)

# Create your views here.
class AuthorList(APIView):

    @api(AuthorSerializer, many=True)
    def get(self, request: Request):
        keyword = request.query_params.get("q", None)
        return biz.get_authors(keyword)

    @api()
    def post(self, request: Request):
        data = request.data
        return biz.author_register(data)


class AuthorCheck(APIView):

    @api(AuthorSerializer)
    def get(self, request: Request):
        email = request.query_params.get("email", None)
        return biz.author_exists(email)

    @api()
    def post(self, request: Request):
        code = request.data.get("code", None)
        token = request.data.get("token", None)
        print(code, token)
        return biz.activate(code, token)


class AuthorDetail(APIView):

    @api(AuthorSerializer)
    def get(self, request: Request, pk):
        return biz.get_author(pk)
    
    @api(AuthorSerializer)
    def put(self, request: Request, pk):
        return biz.edit_author_profile(pk, request.data, u(request))


class AuthView(APIView):

    @api()
    def post(self, request: Request):
        email = request.data.get("email", None)
        password = request.data.get("password", None)
        return biz.login(email, password)


class DocList(APIView):

    @api(DocSerializer, many=True)
    def get(self, request: Request, role, author_id):
        return biz.get_doc_by_author_with_role(author_id, role, u(request))

    @api(DocSerializer)
    def post(self, request: Request, role, author_id):
        return biz.create_doc(request.data, author_id, u(request))


class DocDetail(APIView):
    
    @api(DocSerializer)
    def get(self, request: Request, pk):
        code = request.query_params.get("code", None)
        return biz.get_doc(pk, u(request), code)
    
    @api(DocSerializer)
    def put(self, request: Request, pk):
        return biz.edit_doc_info(pk, request.data, u(request))

    @api(DocSerializer)
    def delete(self, request: Request, pk):
        return biz.delete_doc(pk, u(request))


class DocQueryBatch(APIView):

    @api(DocSerializer, many=True)
    def get(self, request: Request):
        keywords = request.query_params.get("keywords", None)
        return biz.search_doc(keywords, u(request))

    @api(DocSerializer, many=True)
    def post(self, request: Request):
        doc_ids = set(request.data.get("ids", []))
        from_tos = request.data.get("fts", [])
        return biz.get_doc_batch(doc_ids, from_tos, u(request))


class DocDeleteBatch(APIView):

    @api()
    def post(self, request: Request):
        doc_ids = set(request.data.get("ids", []))
        from_tos = request.data.get("fts", [])
        return biz.del_doc_batch(doc_ids, from_tos, u(request))


class AccessListView(APIView):
    
    @api(DocAccessSerializer)
    def get(self, request: Request):
        author_id = request.query_params.get("author_id", None)
        doc_id = request.query_params.get("doc_id", None)
        return biz.query_access(author_id, doc_id, u(request))

    @api(DocSerializer)
    def post(self, request: Request):
        doc_id = request.data.get("doc_id", None)
        author_id = request.data.get("author_id", None)
        role = request.data.get("role", None)
        return biz.grant_doc_to_author(doc_id, author_id, role, u(request))


class AccessDetailView(APIView):

    @api(DocSerializer)
    def delete(self, request: Request, doc_id, author_id):
        return biz.cancel_access_to_doc(doc_id, author_id, u(request))


class TokenReverseView(APIView):

    @api(AuthorSerializer)
    def get(self, request: Request):
        token = request.query_params.get("token", None)
        return biz.get_author_by_token(token)


class DocTreeView(APIView):

    @api(DocTreeSerializer)
    def get(self, request: Request, author_id: int):
        return biz.get_doc_tree_of(author_id, u(request))
    
    @api(DocTreeSerializer)
    def post(self, request: Request, author_id: int):
        content = request.data.get("content", None)
        return biz.save_doc_tree(author_id, content, u(request))


class ChatView(APIView):

    @api(ChatSerializer, many=True)
    def get(self, request: Request):
        author_id1 = request.query_params.get("a1", None)
        author_id2 = request.query_params.get("a2", None)
        return biz.get_or_create_chat(author_id1, author_id2, u(request))

    @api(MessageSerializer)
    def post(self, request: Request):
        sender = request.data.get("sender", None)
        receiver = request.data.get("receiver", None)
        msg = request.data.get("msg", None)
        return biz.send_message(sender, receiver, msg, u(request))


class ChatDetailView(APIView):

    @api(ChatSerializer)
    def get(self, request: Request, pk: int):
        return biz.get_chat_by_id(pk, u(request))

class GetInviteLink(APIView):

    @api()
    def get(self, request: Request):
        doc_id = request.query_params.get("doc_id", None)
        auth = request.query_params.get("auth", None)
        return biz.get_invite_link(doc_id, auth, u(request))

class GetRecords(APIView):

    @api(MessageSerializer, many=True)
    def get(self, request: Request):
        chat_id = request.query_params.get("chat_id", None)
        page = int(request.query_params.get("page", 0))
        page_size = int(request.query_params.get("page_size", 10))
        return biz.get_records(chat_id, page, page_size, u(request))


class MessageQuery(APIView):

    @api(MessageSerializer, many=True)
    def get(self, request: Request):
        keywords = request.query_params.get("keywords", None)
        return biz.search_message(keywords, u(request))
