__author__ = 'kernel-72'

from mongoengine import InvalidQueryError, NotUniqueError
from tastypie.authentication import MultiAuthentication, Authentication, SessionAuthentication
from tastypie.authorization import Authorization
from tastypie.bundle import Bundle
from tastypie.exceptions import BadRequest, NotFound
from tastypie.resources import Resource


# class PrettyJSONSerializer(Serializer):
#     json_indent = 2
#
#     def to_json(self, data, options=None):
#         options = options or {}
#         data = self.to_simple(data, options)
#         return json.dumps(data, cls=DjangoJSONEncoder, sort_keys=True, ensure_ascii=False, indent=self.json_indent)


class BasicMongoResource(Resource):
    class Meta:
        object_class = None
        authentication = MultiAuthentication(Authentication(), SessionAuthentication())
        authorization = Authorization()
        # serializer = PrettyJSONSerializer()
        allowed_methods = ['get', 'post', 'put', 'patch', 'delete']
        always_return_data = True

    def detail_uri_kwargs(self, bundle_or_obj):
        kwargs = {}

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.pk
        else:
            kwargs['pk'] = bundle_or_obj.pk

        return kwargs

    def get_object_list(self, request):
        return self._meta.object_class.objects

    def apply_filters(self, request, applicable_filters):
        if not applicable_filters:
            return self.get_object_list(request).all()

        result = self.get_object_list(request).filter(**applicable_filters.dict())
        return result

    def apply_sorting(self, obj_list, options=None):
        if options is None:
            options = {}

        if 'order_by' not in options:
            return obj_list

        if hasattr(options, 'getlist'):
            order_values = options.getlist('order_by')
        else:
            order_values = options.get('order_by').split(',')

        return obj_list.order_by(*order_values)

    def build_filters(self, filters=None):
        if filters is None:
            filters = {}

        for key in filters.copy():
            if key in ('limit', 'order_by', 'offset'):
                del filters[key]
                continue

            if '__in' in key or '__nin' in key:
                filters[key] = filters[key].split(',')
                continue

        return filters

    def get_query_only_fields(self, use_in='all'):
        only_fields = []
        for f_name, f_instance in self.fields.iteritems():
            if f_name == 'resource_uri':
                continue

            if f_instance.use_in not in (use_in, 'all') or f_instance.attribute is None:
                continue
            only_fields.append(f_instance.attribute)
        return only_fields

    def obj_get_list(self, bundle, **kwargs):
        filters = {}
        if hasattr(bundle.request, 'GET'):
            filters = bundle.request.GET.copy()

        filters.update(kwargs)
        applicable_filters = self.build_filters(filters=filters)

        only_fields = self.get_query_only_fields('list')
        only_fields = set(self._meta.object_class._fields_ordered).intersection(only_fields)

        objects = self.apply_filters(bundle.request, applicable_filters).only(*only_fields)

        # Some hack to check is queryset return correct result
        try:
            objects[0]
        except InvalidQueryError:
            raise BadRequest("Invalid query")
        except IndexError:
            pass

        return self.authorized_read_list(objects, bundle)

    def obj_get(self, bundle, **kwargs):
        try:

            bundle.obj = self._meta.object_class.objects.get(pk=kwargs['pk'])
            self.authorized_read_detail([bundle.obj], bundle)
            return bundle.obj
        except:
            raise NotFound("No such resource")

    def obj_create(self, bundle, **kwargs):
        bundle.obj = self._meta.object_class(**kwargs)
        bundle = self.full_hydrate(bundle)
        self.authorized_create_detail([bundle.obj], bundle)
        bundle.obj.save()
        return bundle

    def obj_update(self, bundle, **kwargs):
        try:
            obj = self.obj_get(bundle, **kwargs)
        except NotFound:
            return self.obj_create(bundle, **kwargs)
        bundle.obj = obj
        bundle = self.full_hydrate(bundle)
        self.authorized_update_detail([bundle.obj], bundle)
        try:
            bundle.obj.save()
        except NotUniqueError as e:
            raise BadRequest("Such value aready exist")
        return bundle

    def obj_delete_list(self, bundle, **kwargs):
        raise NotImplementedError()

    def obj_delete(self, bundle, **kwargs):
        try:
            bundle.obj = self.obj_get(bundle, **kwargs)
        except:
            raise NotFound("No such resource")

        self.authorized_delete_detail(self.get_object_list(bundle.request), bundle)
        bundle.obj.delete()

