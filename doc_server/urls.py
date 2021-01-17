"""doc_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from doc import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('author/', views.AuthorList.as_view()),
    path('author/<int:pk>', views.AuthorDetail.as_view()),
    path('reveal/', views.TokenReverseView.as_view()),
    path('check/author', views.AuthorCheck.as_view()),
    path('auth/', views.AuthView.as_view()),
    path('doc/<str:role>/<int:author_id>', views.DocList.as_view()),
    path('doc/<int:pk>', views.DocDetail.as_view()),
    path('invite/', views.AccessListView.as_view()),
    path('kick/<int:doc_id>/<int:author_id>', views.AccessDetailView.as_view()),
    path('doctree/<int:author_id>', views.DocTreeView.as_view()),
    path('batch/query/doc', views.DocQueryBatch.as_view()),
    path('batch/delete/doc', views.DocDeleteBatch.as_view()),
]
