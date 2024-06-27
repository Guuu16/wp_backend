# -*- coding: utf-8 -*-
"""
@Time ： 1/12/23 10:26 AM
@Auth ： gujie5
"""
import json
import logging

from apps.bugzila.bugzila_server.bugzilawrapper import *


@RequestGetDecorator
def Get_Bug(url_base, token, id_alias=None, include_fields=None):
    '''
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html#get-bug
    '''
    req = url_base + "/rest/bug"
    if id_alias:
        params = {"id": int(id_alias), "token": token}
    else:
        params = {"token": token}
    if include_fields:
        params.update({"include_fields": include_fields})
    print(params)
    return req, params


@RequestGetDecorator
def Bug_History(id, url_base, token, new_since=None):
    '''
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html#bug-history
        new_since=YYYY-MM-DD
    '''
    req = "{url_base}/rest/bug/{id}/history".format(url_base=url_base, id=str(id))
    params = {"token": token}
    if new_since:
        params.update({"new_since": new_since})
    return req, params


@RequestGetDecorator
def Search_Bugs(url_base, token, *args, **kwargs):
    '''
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html#search-bugs
        quicksearch:
            https://www.squarefree.com/bugzilla/quicksearch-help.html
            http://eigen.tuxfamily.org/bz/page.cgi?id=quicksearch.html
    '''
    options = ["alias", "assigned_to", "component", "creation_time", "creator", "id",
               "last_change_time", "limit", "offset", "op_sys", "platform", "priority",
               "product", "resolution", "severity", "status", "summary", "tags",
               "target_milestone", "qa_contact", "url", "version", "whiteboard", "quicksearch",
               "include_fields", 'url_base', 'token'
               ]
    params = {"token": token}
    if kwargs:
        for key in kwargs.keys():
            if key not in options:
                err = "\'" + key + "\' is not supported!"
                raise Exception(err)
        params.update(kwargs)
    else:
        raise Exception("one of  {} must be set!".format(options))

    req = url_base + "/rest/bug"
    return req, params


@RequestPostDecorator
def Create_Bug(url_base, token, *args, **kwargs):
    '''
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html#create-bug
    '''
    options_in_need = ['product', 'component', 'version', 'cf_change_type', 'cf_probability', "cf_cusprj",
                       'summary']
    options = [
        "description", "op_sys", "target_milestone", "flags",
        "platform", "priority", "severity", "alias", "assigned_to", "cc",
        "comment_is_private", "groups", "qa_contact", "status", "resolution"
    ]
    req = url_base + "/rest/bug"

    params = {"token": token}

    if kwargs:
        for opt in options_in_need:
            if opt not in params.keys():
                raise Exception(opt + " must be set")

        for key in kwargs.keys():
            if key not in options:
                err = "\'" + key + "\' is not supported!"
                raise Exception(err)
        params = kwargs.copy()
    else:
        raise Exception("{} must be set".format(",".join(options_in_need)))

    return req, params


@RequestPutDecorator
def Update_Bug(url_base, token, id, **kwargs):
    '''
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html#update-bug
    '''
    options = [
        "alias", "assigned_to", "blocks", "depends_on", "cc", "is_cc_accessible",
        "comment", "comment_is_private", "component", "deadline", "dupe_of", "estimated_time",
        "flags", "groups", "keywords", "op_sys", "platform", "priority",
        "product", "qa_contact", "is_creator_accessible", "remaining_time", "reset_assigned_to", "reset_qa_contact",
        "reset_qa_contact", "resolution", "see_also", "severity", "status", "summary",
        "target_milestone", "url", "version", "whiteboard", "work_time"
    ]
    params = {"token": token}
    if not kwargs:
        raise Exception("kwargs cannot be empty!")
    else:
        for key in kwargs.keys():
            if key not in options:
                err = "\'" + key + "\' is not supported!"
                raise Exception(err)

    req = url_base + "/rest/bug/" + str(id)
    params.update(kwargs)
    return req, params


@RequestGetDecorator
def Bug_Fields(url_base, token, field=None):
    '''
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/field.html#fields
    '''
    params = {"token": token}
    req = url_base + "/rest/field/bug"
    if field:
        req = req + "/" + field
    return req, params


@RequestGetDecorator
def Field_values(url_base, token, field, product_id=None):
    '''
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/field.html#legal-values
    '''
    params = {"token": token}
    req = url_base + "/rest/field/bug/{field}".format(field=field)
    if product_id:
        req = req + "/{product_id}".format(product_id=product_id)
    req = req + "/values"
    return req, params
