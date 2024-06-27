from django.shortcuts import render
import datetime
import json
import re
import jwt
import ldap
import requests
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from django.forms.models import model_to_dict
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.settings import api_settings
from rest_framework.views import View, APIView
# from django.shortcuts import JsonResponse, render
from webportal import settings
from django.contrib.auth.hashers import make_password
from jenkinsServer.models import Group
from loginAndLogout.models import Eventlog
# Create your views here.
from rest_framework.response import Response
from rest_framework.serializers import Serializer


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)


class CustomResponse(Response):
    def __init__(self, data=None, msg=None, status=None, template_name=None, headers=None, exception=False,
                 content_type=None, **kwargs):
        super().__init__(None, status=status)
        if isinstance(data, Serializer):
            msg = (
                'You passed a Serializer instance as data, but '
                'probably meant to pass serialized `.data` or '
                '`.error`. representation.'
            )
            raise AssertionError(msg)
            # 自定义返回格式
        self.data = {'msg': msg, 'data': data}
        self.data.update(kwargs)
        self.template_name = template_name
        self.exception = exception
        self.content_type = content_type
        if headers:
            for name, value in headers.items():
                self[name] = value


class Login(APIView):
    authentication_classes = []
    permission_classes = []

    def auth_user(self, username, password):
        if username != "admin":
            conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
            try:
                # 将username附加上域名
                username += '@company.com'
                # 验证用户是否存在，存在返回1，不存在，则会报错
                conn.simple_bind_s(username, password)
                return 1
            except Exception as e:
                return e
        else:
            return 1

    def post(self, request):
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)
        if self.auth_user(username, password) != 1:
            event = Eventlog()
            event.events = username + " login"
            event.result = "fail"
            event.userid = User.objects.get(username=username)
            event.save()
            return CustomResponse(data={}, msg='username or password error', status=500)
        else:
            try:
                User.objects.get(username=username, is_active=1)
                User.objects.filter(username=username).update(password=make_password(password))
            except User.DoesNotExist:
                if username == "admin":
                    User.objects.create_user(username=username, password=password, email=f"gujie6@company.com",
                                             is_active=1, is_superuser=1)
                else:
                    User.objects.create_user(username=username, password=password, email=f"{username}@company.com",
                                             is_active=1)
            user = authenticate(username=username, password=password)
            if user is None:
                return CustomResponse(data={}, msg='username or password error', status=500)
            login(request, user=user)
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)
            request.session['is_login'] = True
            request.session['username'] = username
            # request.session['token'] = token
            # 设置登录时间
            now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            request.session['last_visit_time'] = now_time
            event = Eventlog()
            event.events = username + " login"
            event.result = "success"
            event.userid = User.objects.get(username=username)
            event.save()
            return CustomResponse(data={'token': token}, msg='login success', status=200)


class LogoutView(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # jwt.
        # 清理session（redis中的会话，请求对象cookie中的sessionid）-request.session.flush()
        logout(request=request)
        return CustomResponse(data={"success": True}, msg='logout success', status=200)


class ApiUsers(APIView):
    # api_view = (['GET'],)
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        res = {}
        username = request.session.get("username")
        if username:
            user = User.objects.get(username=username, is_active=1)
            res["create_time"] = user.date_joined.strftime("%Y-%m-%d %H:%M:%S")
            res["last login"] = user.last_login.strftime("%Y-%m-%d %H:%M:%S")
            res["username"] = user.username
            res['email'] = user.email
            res["is_active"] = user.is_active
            res['is_super'] = user.is_superuser
            res['menus'] = [
                {
                    "name": "Home",
                    "frontpath": "/",
                    "icon": "home-filled",
                    "child": []
                },
                {
                    "name": "Web Portal",
                    "frontpath": None,
                    "icon": "Menu",
                    "child": [
                        {
                            "name": "MRT",
                            "frontpath": "/panel/mrt",
                            "icon": "Watermelon",
                            "child": []
                        },
                        {
                            "name": "XPIT",
                            "frontpath": "/panel/xpit",
                            "icon": "help",
                            "child": []
                        },
                        {
                            "name": "DAILY",
                            "frontpath": "/panel/daily",
                            "icon": "ShoppingBag",
                            "child": []
                        },
                        {
                            "name": "MEMSTRESS",
                            "frontpath": "/panel/memstress",
                            "icon": "PieChart",
                            "child": []
                        },
                        {
                            "name": "PERFORMANCE",
                            "frontpath": "/panel/performance",
                            "icon": "TrophyBase",
                            "child": []
                        }
                    ]
                },
                {
                    "name": "Performance Analysis",
                    "frontpath": "/performance",
                    "icon": "List",
                    "child": []
                }
            ]
            # rest = json.dumps(res)
            # print(type(rest))
            return CustomResponse(data=res, msg='get user success', status=200)
        else:
            return CustomResponse(data={}, msg="get user fail", status=500)


class ReceiverGroup(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    # def get(self):
    #     private_groups = [g.to_dict() for g in Group.objects.filter_by(
    #         userid=current_user.id).order_by(Group.id.desc())]
    #     private_groups_ids = {g['id'] for g in private_groups}
    #     public_groups = [g.to_dict() for g in Group.query.filter_by(
    #         public=True).order_by(Group.id.desc()) if g.id not in private_groups_ids]
    #     return jsonify(public_groups + private_groups)
    #

    # def get_update_data(self, jsondata):
    #     res = {}
    #     res["name"] = jsondata["name"]
    #     res["members"] = jsondata["members"]
    #     res["public"] = jsondata["public"]
    #     return res

    def get(self, request):
        username = request.session.get("username")
        userid = User.objects.filter(username=username, is_active=1).values('id')[0]['id']
        print(userid)
        ret = Group.objects.filter(userid=int(userid))
        lis = []
        for i in ret:
            lis.append(model_to_dict(i))
        res = {"success": True, "group": lis}
        return CustomResponse(data=res, msg="get receiver success")

    def post(self, request):
        jd = json.loads(request.body.decode())
        action = jd.get('action', None)
        name = jd.get('name', None)
        members = jd.get("members", None)
        if action == "create":
            group = Group()
            group.name = name
            group.members = members
            username = request.session.get("username")
            userid = User.objects.filter(username=username, is_active=1).values('id')[0]['id']
            group.userid = User.objects.get(id=int(userid))
            group.save()
            ret = Group.objects.filter(name=name, userid=int(userid)).order_by("-createtime").first()
            res = {"success": True, "group": model_to_dict(ret)}
            return CustomResponse(data=res, msg="create success")
        elif action == "update":
            group = Group.objects.filter(id=jd.get("id"))
            if group: group.update(name=name, members=members)
            ret = Group.objects.filter(id=jd.get("id")).order_by("-updatetime").first()
            res = {"success": True, "group": model_to_dict(ret)}
            return CustomResponse(data=res, msg="update success")
        elif action == "delete":
            group = Group.objects.filter(id=jd["id"]).first()
            if group: group.delete()
            res = {"success": True}
            return CustomResponse(data=res, msg="delete success")


class AdminAction(APIView):
    authentication_classes = (JSONWebTokenAuthentication,)  # token认证
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        username = request.session.get("username")
        if username == "admin":
            group = User.objects.values_list('id', "is_superuser", "username", "is_active")
            lis = []
            for i in group:
                if i[2] != "admin": lis.append({"username": i[2], "super": i[1]})
            res = {"success": True, "group": lis}
            return CustomResponse(data=res, msg="get group success")
        else:
            res = {"success": False, "issue": "not admin user"}
            return CustomResponse(data=res, msg="get group fail", status=500)

    def post(self, request):
        jd = json.loads(request.body.decode())
        action = jd.get('action', None)
        username = jd.get('username', None)
        superuser = jd.get("super", None)
        print(superuser)
        if action == "update":
            User.objects.filter(username=username).update(is_superuser=superuser)
            res = {"success": True}
            return CustomResponse(data=res, msg="update success")
