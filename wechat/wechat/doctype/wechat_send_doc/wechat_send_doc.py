# -*- coding: utf-8 -*-
# Copyright (c) 2017, Dirk Chang and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import throw, _
from frappe.model.document import Document
from wechatpy import WeChatClient
from wechatpy.oauth import WeChatOAuth

template_name_map = {
	'IOT Device Error': 'device_alarm_template',
	'Repair Issue': 'repair_issue_template',
}

class WechatSendDoc(Document):
	def after_insert(self):
		frappe.enqueue('wechat.wechat.doctype.wechat_send_doc.wechat_send_doc.wechat_send',
					   doc_name=self.name, doc_doc=self)

	def wechat_send(self):
		if self.status == 'Finished':
			return
		src_doc = frappe.get_doc(self.doc_type, self.doc_id)
		if not src_doc:
			throw(_("Cannot find doc {0} id {1}").format(self.doc_type, self.doc_id))
			return

		data = self.run_method("wechat_tmsg_data")
		if not data:
			throw(_("Cannot generate wechat template data for {0}").format(self.doc_type))
		url = self.run_method("wechat_tmsg_url")
		if not url:
			throw(_("Cannot generate wechat template url for {0}").format(self.doc_type))

		template_id = frappe.get_value('Wechat App', self.app, template_name_map[self.doc_type])
		if not template_id:
			throw(_("Cannot find wechat template id for {0}").format(self.doc_type))

		app_id = frappe.get_value('Wechat App', self.app, 'app_id')
		secret = frappe.get_value('Wechat App', self.app, 'secret')
		domain = frappe.get_value('Wechat App', self.app, 'domain')
		client = WeChatClient(app_id, secret)

		authorize_url = WeChatOAuth(app_id, secret, "http://" + domain + url).authorize_url

		users = self.get("to_users")

		count = 0
		for user in users:
			done = self.__send_wechat_msg(client, user, template_id, authorize_url, data)
			if done:
				count = count + 1

		if count > 0:
			self.set("status", "Partial")
		if count == len(users):
			self.set("status", "Finished")
		self.save()

	def __send_wechat_msg(self, client, user, template_id, url, data):
		if user.status != 'New':
			return True

		frappe.logger(__name__).info("Send template {0} data {1} to user {2} via app {3}"
									 .format(template_id, data, user.user, self.app))
		user_id = frappe.get_value("Wechat Binding", {"app": self.app, "user": user}, "openid")
		if not user_id:
			frappe.logger(__name__).warning(_("User {0} has not bind her/his wechat").format(user.user))
			user.set("sent", 1)
			user.set("status", 'Error')
			user.set("info", ("User {0} has not bind her/his wechat").format(user.user))
			return

		try:
			r = client.message.send_template(user_id, template_id, url, top_color='yellow', data=data)

			if r["errcode"] == 0:
				frappe.logger(__name__).debug(_("Send template message ok {0}").format(r))
				user.set("status", 'Finished')
			else:
				frappe.logger(__name__).error(_("Send template message to user {0} failed {1}").format(user.user, r))
				user.set("status", 'Error')

			user.set("sent", 1)
			user.set("info", r)
			return True
		except Exception, e:
			frappe.logger(__name__).error(_("Send template message to user {0} failed {1}").format(user.user, e.message))
			user.set("sent", 1)
			user.set("status", 'Error')
			user.set("info", e.message)
		return False


def wechat_send(doc_name, doc_doc=None):
	doc = doc_doc or frappe.get_doc('Wechat Send Doc', doc_name)
	return doc.wechat_send()

