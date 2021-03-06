from django.db.models import Count, Q
from django.utils.functional import cached_property
from django.views.generic import ListView

from pretix.base.models import Order
from pretix.control.forms.filter import OrderSearchFilterForm


class OrderSearch(ListView):
    model = Order
    context_object_name = 'orders'
    paginate_by = 30
    template_name = 'pretixcontrol/search/orders.html'

    @cached_property
    def filter_form(self):
        return OrderSearchFilterForm(data=self.request.GET, request=self.request)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data()
        ctx['filter_form'] = self.filter_form
        return ctx

    def get_queryset(self):
        qs = Order.objects.all().annotate(pcnt=Count('positions', distinct=True)).select_related('invoice_address')
        if not self.request.user.is_superuser:
            qs = qs.filter(
                Q(event__organizer_id__in=self.request.user.teams.filter(
                    all_events=True, can_view_orders=True).values_list('organizer', flat=True))
                | Q(event_id__in=self.request.user.teams.filter(
                    can_view_orders=True).values_list('limit_events__id', flat=True))
            )

        if self.filter_form.is_valid():
            qs = self.filter_form.filter_qs(qs)

        if self.request.GET.get("ordering", "") != "":
            p = self.request.GET.get("ordering", "")
            p_admissable = ('event', '-event', '-code', 'code', '-email', 'email', '-total', 'total', '-datetime',
                            'datetime', '-status', 'status', 'pcnt', '-pcnt')
            if p in p_admissable:
                qs = qs.order_by(p)

        return qs.distinct().prefetch_related('event', 'event__organizer')
