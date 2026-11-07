"""Shared validation for read-only instrument history filters."""
from django.db.models import Q
from rest_framework import serializers


class RecordFilters(serializers.Serializer):
    account_id = serializers.IntegerField(min_value=1, required=False)
    account_ids = serializers.CharField(max_length=2000, required=False)
    search = serializers.CharField(max_length=100, required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, values):
        if 'account_ids' in values:
            values['account_ids'] = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100).run_validation(values['account_ids'].split(','))
        if values.get('start_date') and values.get('end_date') and values['start_date'] > values['end_date']:
            raise serializers.ValidationError('Start date must not follow end date.')
        return values


def record_filters(queryset, params, date_field, *, instrument=True, account=True):
    fields = RecordFilters(data=params)
    fields.is_valid(raise_exception=True)
    values = fields.validated_data
    if account and values.get('account_id'):
        queryset = queryset.filter(account_id=values['account_id'])
    if account and values.get('account_ids'):
        queryset = queryset.filter(account_id__in=values['account_ids'])
    if instrument and values.get('search'):
        search = values['search']
        queryset = queryset.filter(Q(instrument__name__icontains=search) | Q(instrument__sym_ticker__icontains=search))
    for param, lookup in [('start_date', 'gte'), ('end_date', 'lte')]:
        if param in values:
            queryset = queryset.filter(**{f'{date_field}__date__{lookup}': values[param]})
    return queryset
