# -*- coding: utf-8 -*-
# Copyright (c) 2017, Dirk Chang and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from wechatpy.oauth import WeChatOAuth
from wechat.api import check_wechat_binding


def get_context(context):
	wc_rurl = frappe.form_dict.wc_rurl or "wechat_home"
	context.no_cache = 1

	check_wechat_binding(redirect_url=wc_rurl)
