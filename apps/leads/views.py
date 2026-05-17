import csv
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Lead
from .serializers import LeadSerializer, LeadUpdateSerializer


class LeadListView(APIView):
    """
    GET /api/leads/?bot=<id>&status=new&channel=whatsapp
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Lead.objects.filter(bot__tenant=request.user.tenant)

        bot_id = request.query_params.get("bot")
        if bot_id:
            qs = qs.filter(bot_id=bot_id)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        channel = request.query_params.get("channel")
        if channel:
            qs = qs.filter(channel=channel)

        search = request.query_params.get("search")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )

        return Response(LeadSerializer(qs, many=True).data)


class LeadDetailView(APIView):
    """
    GET   /api/leads/<pk>/
    PATCH /api/leads/<pk>/   — update status / notes
    DELETE /api/leads/<pk>/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, tenant):
        try:
            return Lead.objects.get(pk=pk, bot__tenant=tenant)
        except Lead.DoesNotExist:
            return None

    def get(self, request, pk):
        lead = self.get_object(pk, request.user.tenant)
        if not lead:
            return Response({"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(LeadSerializer(lead).data)

    def patch(self, request, pk):
        lead = self.get_object(pk, request.user.tenant)
        if not lead:
            return Response({"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = LeadUpdateSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(LeadSerializer(lead).data)

    def delete(self, request, pk):
        lead = self.get_object(pk, request.user.tenant)
        if not lead:
            return Response({"detail": "Lead not found."}, status=status.HTTP_404_NOT_FOUND)
        lead.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadExportView(APIView):
    """GET /api/leads/export/?bot=<id>  — download as CSV"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Lead.objects.filter(bot__tenant=request.user.tenant)
        bot_id = request.query_params.get("bot")
        if bot_id:
            qs = qs.filter(bot_id=bot_id)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="leads.csv"'

        writer = csv.writer(response)
        writer.writerow(["Name", "Email", "Phone", "Channel", "Status", "Notes", "Created At"])
        for lead in qs:
            writer.writerow([
                lead.name, lead.email, lead.phone,
                lead.channel, lead.status, lead.notes,
                lead.created_at.strftime("%Y-%m-%d %H:%M"),
            ])
        return response
