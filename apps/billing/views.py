import stripe
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invoice, Subscription
from .serializers import CreateCheckoutSerializer, InvoiceSerializer, SubscriptionSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY

# Map plan names to Stripe Price IDs — store these in settings
PLAN_PRICE_MAP = {
    "smart": settings.STRIPE_PRICE_SMART,
    "boost": settings.STRIPE_PRICE_BOOST,
    "ultimo": settings.STRIPE_PRICE_ULTIMO,
}


class SubscriptionView(APIView):
    """GET /api/billing/subscription/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(tenant=request.user.tenant)
            return Response(SubscriptionSerializer(sub).data)
        except Subscription.DoesNotExist:
            return Response({"plan": "free", "status": "active"})


class CreateCheckoutView(APIView):
    """POST /api/billing/checkout/  — create a Stripe checkout session"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.validated_data["plan"]
        tenant = request.user.tenant

        # get or create Stripe customer
        if not tenant.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=tenant.name,
                metadata={"tenant_id": str(tenant.id)},
            )
            tenant.stripe_customer_id = customer.id
            tenant.save(update_fields=["stripe_customer_id"])

        session = stripe.checkout.Session.create(
            customer=tenant.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": PLAN_PRICE_MAP[plan], "quantity": 1}],
            mode="subscription",
            success_url=serializer.validated_data["success_url"],
            cancel_url=serializer.validated_data["cancel_url"],
            metadata={"tenant_id": str(tenant.id), "plan": plan},
        )
        return Response({"checkout_url": session.url})


class CustomerPortalView(APIView):
    """POST /api/billing/portal/  — Stripe billing portal (manage/cancel)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant = request.user.tenant
        if not tenant.stripe_customer_id:
            return Response(
                {"detail": "No billing account found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return_url = request.data.get("return_url", settings.FRONTEND_URL)
        session = stripe.billing_portal.Session.create(
            customer=tenant.stripe_customer_id,
            return_url=return_url,
        )
        return Response({"portal_url": session.url})


class InvoiceListView(APIView):
    """GET /api/billing/invoices/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.filter(tenant=request.user.tenant)
        return Response(InvoiceSerializer(invoices, many=True).data)


class StripeWebhookView(APIView):
    """
    POST /api/billing/webhook/
    Public — called by Stripe. Verifies signature and handles events.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data)

        elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
            self._handle_subscription_updated(data)

        elif event_type == "customer.subscription.deleted":
            self._handle_subscription_deleted(data)

        elif event_type == "invoice.payment_succeeded":
            self._handle_invoice_paid(data)

        elif event_type == "invoice.payment_failed":
            self._handle_invoice_failed(data)

        return Response({"status": "ok"})

    def _handle_checkout_completed(self, session):
        from apps.accounts.models import Tenant
        tenant_id = session.get("metadata", {}).get("tenant_id")
        plan = session.get("metadata", {}).get("plan")
        if not tenant_id or not plan:
            return
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            tenant.plan = plan
            tenant.save(update_fields=["plan"])
        except Tenant.DoesNotExist:
            pass

    def _handle_subscription_updated(self, subscription):
        from apps.accounts.models import Tenant
        from django.utils import timezone
        import datetime

        customer_id = subscription.get("customer")
        try:
            tenant = Tenant.objects.get(stripe_customer_id=customer_id)
        except Tenant.DoesNotExist:
            return

        period_end = subscription.get("current_period_end")
        period_start = subscription.get("current_period_start")

        Subscription.objects.update_or_create(
            tenant=tenant,
            defaults={
                "stripe_subscription_id": subscription["id"],
                "stripe_price_id": subscription["items"]["data"][0]["price"]["id"],
                "plan": tenant.plan,
                "status": subscription["status"],
                "current_period_start": timezone.datetime.fromtimestamp(period_start, tz=timezone.utc) if period_start else None,
                "current_period_end": timezone.datetime.fromtimestamp(period_end, tz=timezone.utc) if period_end else None,
                "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
            },
        )

    def _handle_subscription_deleted(self, subscription):
        from apps.accounts.models import Tenant
        customer_id = subscription.get("customer")
        try:
            tenant = Tenant.objects.get(stripe_customer_id=customer_id)
            tenant.plan = "free"
            tenant.save(update_fields=["plan"])
            Subscription.objects.filter(tenant=tenant).update(status="canceled")
        except Tenant.DoesNotExist:
            pass

    def _handle_invoice_paid(self, invoice):
        from apps.accounts.models import Tenant
        customer_id = invoice.get("customer")
        try:
            tenant = Tenant.objects.get(stripe_customer_id=customer_id)
            Invoice.objects.get_or_create(
                stripe_invoice_id=invoice["id"],
                defaults={
                    "tenant": tenant,
                    "amount_paid": invoice.get("amount_paid", 0),
                    "currency": invoice.get("currency", "usd"),
                    "status": invoice.get("status", "paid"),
                    "invoice_pdf": invoice.get("invoice_pdf", ""),
                },
            )
            # reset monthly message counter on successful payment
            from apps.bots.models import Bot
            Bot.objects.filter(tenant=tenant).update(messages_used=0)
        except Tenant.DoesNotExist:
            pass

    def _handle_invoice_failed(self, invoice):
        from apps.accounts.models import Tenant
        customer_id = invoice.get("customer")
        try:
            tenant = Tenant.objects.get(stripe_customer_id=customer_id)
            Subscription.objects.filter(tenant=tenant).update(status="past_due")
        except Tenant.DoesNotExist:
            pass
