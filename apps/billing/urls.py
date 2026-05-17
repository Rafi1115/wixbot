from django.urls import path
from . import views

urlpatterns = [
    path("subscription/", views.SubscriptionView.as_view()),
    path("checkout/", views.CreateCheckoutView.as_view()),
    path("portal/", views.CustomerPortalView.as_view()),
    path("invoices/", views.InvoiceListView.as_view()),
    path("webhook/", views.StripeWebhookView.as_view()),
]
