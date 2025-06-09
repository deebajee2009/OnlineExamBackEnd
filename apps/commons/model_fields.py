from django.db import models


class CharFieldNoEmptyString(models.CharField):
    def get_prep_value(self, value):
        value = super(CharFieldNoEmptyString, self).get_prep_value(value)
        return value or None

class EmailFieldNoEmptyString(models.EmailField):
    def get_prep_value(self, value):
        value = super(EmailFieldNoEmptyString, self).get_prep_value(value)
