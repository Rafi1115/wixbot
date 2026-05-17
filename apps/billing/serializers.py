from rest_framework import serializers
from .models import Invoice, Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id", "plan", "status", "cancel_at_period_end",
            "current_period_start", "current_period_end", "created_at",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ["id", "amount_paid", "amount_display", "currency", "status", "invoice_pdf", "created_at"]

    def get_amount_display(self, obj):
        return f"${obj.amount_paid / 100:.2f}"


class CreateCheckoutSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=["smart", "boost", "ultimo"])
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()
