from rest_framework import serializers
from .models import Member, ContactMessage, NewsletterSubscriber, DonationRequest, TicketOrder


class MemberSignupSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=True)
    email      = serializers.EmailField()


class MemberResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Member
        fields = ['first_name', 'email', 'access_code', 'tier', 'status', 'joined_at']


class AccessCodeVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=12)


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ContactMessage
        fields = ['name', 'email', 'subject', 'message']


class NewsletterSerializer(serializers.Serializer):
    email = serializers.EmailField()


class DonationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DonationRequest
        fields = ['name', 'email', 'amount', 'message']


class TicketOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TicketOrder
        fields = ['order_ref', 'ticket_tier', 'ticket_name', 'price', 'quantity', 'first_name', 'email', 'status', 'created_at']
