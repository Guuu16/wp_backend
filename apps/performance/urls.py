# -*- coding: utf-8 -*-
"""
@Time ： 3/15/23 3:48 PM
@Auth ： gujie5
"""
from apps.performance import views
from django.urls import path, include

urlpatterns = [
    path('perf/platform', views.Getplatform.as_view(), name="getplatform"),
    path('perf/casemac', views.Getcasemac.as_view(), name="getmac"),
    path('perf/search', views.Search.as_view(), name='search'),
    path('perf/getbuildno',views.get_buildno),
    path('perf/getperf',views.get_perf)

]
