# -*- coding: utf-8 -*-
"""
@Time ： 1/12/23 6:09 PM
@Auth ： gujie5
"""

from apps.jenkinsServer import views
from django.urls import path, include

urlpatterns = [
    path('p/<str:job>/jobs',views.ApiJobs.as_view()),
    path('p/task/trigger', views.ApiTaskTrigger.as_view(), name="task_trigger"),
    path('p/task', views.ApiTask.as_view(), name="task"),
    path('p/task/<int:id>', views.ApiTaskDetail.as_view(), name="task"),
    path('p/task/stages', views.ApiTaskStages.as_view(), name="stages"),
    path('p/upload', views.UploadFile.as_view(), name='upload'),
    path('p/building', views.BuildingHostInfoStages.as_view(), name='host'),
    path('p/emaildetail', views.TaskEmailDetailStages.as_view(), name='emaildetail'),
    path('p/stress/archive', views.ApiStressArchive.as_view(), name='archive'),
    path('p/stress/chart/options', views.ApiStressChartOptions.as_view(), name="chartoption"),
    path('p/stress/chart', views.ApiStressChart.as_view(), name="chart"),
    path('p/taskSchedulerlist',views.ApiTaskschedulerList.as_view(),name='taskSchedulerlist'),
    path('p/taskScheduler/<int:sid>',views.ApiTaskscheduler.as_view(),name='taskScheduler')
]
