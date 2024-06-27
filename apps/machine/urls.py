# -*- coding: utf-8 -*-
"""
@Time ： 3/22/23 2:38 PM
@Auth ： gujie5
"""
from apps.machine import views
from django.urls import path, include

urlpatterns = [
    path('info/', views.MachineInfo.as_view(), name="getMachineInfo"),
    # path('config/<int:configId>',views.ApiConfigMessage.as_view(),name="getConfigMessage"),
    path("allconfig/", views.AllConfigMess.as_view(), name='allconfig'),
    path('commonconfig/', views.CommonConfigMess.as_view(), name='commonconfig'),
    path('getcategory/', views.CommonCategoryRelease.as_view(), name='getcategory'),
    path('powerAction/', views.PowerAction.as_view(), name='powerAction'),
    path("openBackdoor/", views.OpenBackDoorAction.as_view(), name='openBackdoor')

]
