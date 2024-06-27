"""webportal URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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

from apps.bugzila import views as bug_views
from django.urls import path, include, re_path
from apps.loginAndLogout import views

urlpatterns = [
    # path('admin/', admin.site.urls),
    path("api/bz/", include("apps.bugzila.urls")),
    path("api/jk/", include("apps.jenkinsServer.urls")),
    path("api/performance/", include("apps.performance.urls")),
    path("api/mach/", include("apps.machine.urls")),
    path('bug/', bug_views.index),
    path('b/', bug_views.get_bug_message),
    path('login/', views.Login.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('user/', views.ApiUsers.as_view()),
    path('receiver/group/', views.ReceiverGroup.as_view()),
    path("admin/", views.AdminAction.as_view())

]
