# -*- coding: utf-8 -*-
"""
@Time ： 1/12/23 2:40 PM
@Auth ： gujie5
"""

from apps.bugzila import views
from django.urls import path, include
from rest_framework.documentation import include_docs_urls

urlpatterns = [
    path("id/<int:bugId>/", views.get_bug),
    path('allBug/', views.get_total_bug),
    path('bugHistory/<int:id>/', views.get_bug_history),
    path('user/', views.Bug_user),
    path('bugdate/<int:date>', views.get_bug_date),
    path('bugmonth/<int:date>/<int:month>', views.get_month_bug),
    path('detail/',views.get_bug_message_detail),
    path('bc/',views.get_bug_classfied),
    path('rank/',views.bug_rank_list),
    path('bugcount/',views.get_bug_message),
    path('bugweek/',views.get_week_bug),
    path('high/',views.high_level_bug)
]
