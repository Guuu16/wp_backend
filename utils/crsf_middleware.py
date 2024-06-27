# -*- coding: utf-8 -*-
"""
@Time ： 2/1/23 7:32 PM
@Auth ： gujie5
"""
from django.utils.deprecation import MiddlewareMixin


class NotUseCsrfTokenMiddlewareMixin(MiddlewareMixin):

    def process_request(self, request):
        setattr(request, '_dont_enforce_csrf_checks', True)
