# -*- coding: utf-8 -*-
# Copyright (c) 2019, Dirk Chang and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
import redis
import datetime
from frappe.utils import now, get_datetime, convert_utc_to_user_timezone
from iot.iot.doctype.iot_device.iot_device import IOTDevice
from cloud.cloud.doctype.cloud_company_group.cloud_company_group import list_user_groups as _list_user_groups
from cloud.cloud.doctype.cloud_company.cloud_company import list_user_companies
from iot.hdb_api import list_iot_devices
from iot.iot.doctype.iot_hdb_settings.iot_hdb_settings import IOTHDBSettings
from iot.hdb import iot_device_tree
from wechat.api import check_wechat_binding


def get_context(context):
	app = check_wechat_binding()

	if frappe.session.user == 'Guest':
		frappe.local.flags.redirect_location = "/login"
		raise frappe.Redirect
	name = frappe.form_dict.device or frappe.form_dict.name
	if not name:
		frappe.local.flags.redirect_location = "/"
		raise frappe.Redirect
	context.no_cache = 1
	context.show_sidebar = True

	context.language = frappe.db.get_value("User", frappe.session.user, ["language"])
	context.csrf_token = frappe.local.session.data.csrf_token

	if 'Company Admin' in frappe.get_roles(frappe.session.user):
		context.isCompanyAdmin = True

	# print(name)
	context.devsn = name
	device = frappe.get_doc('IOT Device', name)
	device.has_permission('read')
	context.doc = device

	client1 = redis.Redis.from_url(IOTHDBSettings.get_redis_server() + "/0")
	cfg = None
	if client1.get(name):
		cfg = json.loads(client1.get(name))
	context.dev_desc = device.description or device.dev_name
	if cfg:
		context.dev_desc = cfg['desc']

	client = redis.Redis.from_url(IOTHDBSettings.get_redis_server() + "/1")
	context.devices = []
	for d in client.lrange(name, 0, -1):
		dev = {
			'sn': d
		}
		if d[0:len(name)] == name:
			dev['name']= d[len(name):]

		context.devices.append(dev)
	# print(context.devices)
	if device.sn:
		context.vsn = iot_device_tree(device.sn)
	else:
		context.vsn = []
	context.title = _('Wechat Device Data')