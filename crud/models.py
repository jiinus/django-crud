# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid
import django
import logging
from datetime import datetime
from django.db import models
from django.utils import timezone

# Get an instance of a logger
logger = logging.getLogger(__name__)

def serialize_user(self):
	return {
		'username': self.username,
		'full_name': self.get_full_name(),
		'first_name': self.first_name,
		'last_name': self.last_name,
	}
django.contrib.auth.models.User.serialize = serialize_user

class CRUModel(models.Model):
	'''
	An abstract base class to add UUID and created/modified fields
	'''
	uuid               = models.UUIDField(default=uuid.uuid4, db_index=True, unique=True)
	created_at         = models.DateTimeField(auto_now_add=True)
	created_by         = models.ForeignKey(django.conf.settings.AUTH_USER_MODEL, related_name='+', null=True, default=None, blank=True, on_delete=models.SET_NULL)
	modified_at        = models.DateTimeField(auto_now=True, blank=True)
	modified_by        = models.ForeignKey(django.conf.settings.AUTH_USER_MODEL, related_name='+', null=True, default=None, blank=True, on_delete=models.SET_NULL)

	@property
	def is_transient(self):
		return self._state.adding

	# Recursive serialization of objects with three-level access control
	def serialize(self, details=False, privates=False, secrets=False, recurse=0, recurse_properties=0):
		obj = {}

		included_fields = [] + self.Marshall.list_fields

		if details and recurse_properties >= 0 and hasattr(self.Marshall, 'detail_fields'):
			included_fields += self.Marshall.detail_fields
		else:
			details = False

		if privates and recurse_properties >= 0 and hasattr(self.Marshall, 'private_fields'):
			included_fields += self.Marshall.private_fields
		else:
			privates = False

		if secrets and recurse_properties >= 0 and hasattr(self.Marshall, 'secret_fields'):
			included_fields += self.Marshall.secret_fields
		else:
			secrets = False

		for field_name in included_fields:
			try:
				field = self._meta.get_field(field_name)
			except:
				field = None

			try:
				field_value = getattr(self, field_name)
			except ValueError:
				if field and field.is_relation:
					field_value = []
				else:
					field_value = None
			except django.core.exceptions.ObjectDoesNotExist:
				field_value = None

			if type(field_value) is datetime:

				obj[field_name] = field_value.isoformat()

			elif isinstance(field_value, models.Model):
				if recurse > 0:
					if isinstance(field_value, CRUModel):
						obj[field_name] = field_value.serialize(details=details, privates=privates, secrets=secrets, recurse=recurse - 1, recurse_properties=recurse_properties - 1)
					elif hasattr(field_value, 'serialize'):
						obj[field_name] = field_value.serialize()
					else:
						obj[field_name] = unicode(field_value)

			elif field_value and field and field.is_relation:
				if recurse > 0:
					obj[field_name] = [child_obj.serialize(details=details, privates=privates, secrets=secrets, recurse=recurse - 1, recurse_properties=recurse_properties - 1) for child_obj in field_value.all()]

			elif isinstance(field_value, dict):
				obj[field_name] = field_value

			elif hasattr(field_value, '__iter__') and not isinstance(field_value, str):
				if recurse >= 0:
					obj[field_name] = [child_obj.serialize(details=details, privates=privates, secrets=secrets, recurse=recurse - 1, recurse_properties=recurse_properties - 1) if hasattr(child_obj, 'serialize') else child_obj for child_obj in field_value]
			else:
				obj[field_name] = field_value

		return obj

	class Marshall:
		list_fields = ['uuid']
		detail_fields = ['created_at', 'modified_at', 'is_transient']
		private_fields = ['created_by', 'modified_by']
		secret_fields = []

	class Meta:
		abstract = True

class CRUDModelManager(models.Manager):
	def get_queryset(self):
		return super(CRUDModel, self).get_queryset().filter(is_deleted=False)

class CRUDModel(CRUModel):
	'''
	An abstract base class to add UUID and created/modified/deleted fields
	'''
	is_deleted         = models.BooleanField(default=False, db_index=True)
	deleted_at         = models.DateTimeField(null=True, default=None, blank=True)
	deleted_by         = models.ForeignKey(django.conf.settings.AUTH_USER_MODEL, related_name='+', null=True, default=None, blank=True, on_delete=models.SET_NULL)

	# Custom manager to filter out deleted objects
	objects            = CRUDModelManager()

	def _delete(self, *args, **kwargs):
		super(CRUDModel, self).delete()

	def delete(self, *args, **kwargs):
		self.is_deleted = True
		self.deleted_at = timezone.now()
		if ('request' in kwargs):
			request = kwargs['request']
			if request.user and request.user.is_authenticated:
				self.deleted_by = request.user
		if ('user' in kwargs):
			self.deleted_by = kwargs['user']
		self.save(update_fields=("is_deleted", "deleted_at", "deleted_by"))

	class Meta:
		abstract = True

