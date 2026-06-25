import string
import random
from django.db import models


class Member(models.Model):
    """Fan Club membership — Back Road Nation."""

    STATUS_PENDING = 'pending_payment'
    STATUS_ACTIVE  = 'active'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Payment'),
        (STATUS_ACTIVE,  'Active'),
    ]

    first_name         = models.CharField(max_length=100, blank=True, default='')
    email              = models.EmailField(unique=True)
    access_code        = models.CharField(max_length=12, unique=True, blank=True, null=True)
    tier               = models.CharField(max_length=50, default='Back Road Member')
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    joined_at          = models.DateTimeField(auto_now_add=True)
    approved_at        = models.DateTimeField(null=True, blank=True)
    is_active          = models.BooleanField(default=False)
    # Payment proof screenshot
    proof_image        = models.ImageField(upload_to='member_proofs/', null=True, blank=True)
    # Session management — one active session per code
    session_token      = models.CharField(max_length=64, null=True, blank=True)
    session_started_at = models.DateTimeField(null=True, blank=True)
    # One-time approval token sent in Telegram link
    approval_token     = models.CharField(max_length=64, unique=True, null=True, blank=True)

    def __str__(self):
        name = self.first_name or self.email.split('@')[0]
        return f'{name} <{self.email}> [{self.get_status_display()}]'

    @property
    def display_name(self):
        return self.first_name or self.email.split('@')[0]

    @staticmethod
    def generate_code():
        chars = string.ascii_uppercase.replace('I', '').replace('O', '') + '23456789'
        return 'RG-' + ''.join(random.choices(chars, k=6))


class ContactMessage(models.Model):
    """Contact form submissions."""
    name       = models.CharField(max_length=200)
    email      = models.EmailField()
    subject    = models.CharField(max_length=300, blank=True)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read    = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.name} — {self.subject or "No subject"}'


class NewsletterSubscriber(models.Model):
    """Newsletter signups."""
    email         = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active     = models.BooleanField(default=True)

    def __str__(self):
        return self.email


class DonationRequest(models.Model):
    """Donation requests — payment details sent privately."""
    name        = models.CharField(max_length=200)
    email       = models.EmailField()
    amount      = models.CharField(max_length=50)  # Free text e.g. "$500" or "custom"
    message     = models.TextField(blank=True)
    proof_image = models.ImageField(upload_to='donation_proofs/', null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.email}) — {self.amount}'


class TicketOrder(models.Model):
    """Ticket purchase orders — PayPal flow with proof upload and shipping."""

    STATUS_PENDING        = 'pending_payment'
    STATUS_PROOF_UPLOADED = 'proof_uploaded'
    STATUS_APPROVED       = 'approved'
    STATUS_ADDRESS_NEEDED = 'awaiting_address'
    STATUS_COMPLETE       = 'complete'
    STATUS_REJECTED       = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING,        'Pending Payment'),
        (STATUS_PROOF_UPLOADED, 'Proof Uploaded'),
        (STATUS_APPROVED,       'Approved'),
        (STATUS_ADDRESS_NEEDED, 'Awaiting Address'),
        (STATUS_COMPLETE,       'Complete'),
        (STATUS_REJECTED,       'Rejected'),
    ]

    order_ref        = models.CharField(max_length=20, unique=True)
    ticket_tier      = models.CharField(max_length=50)
    ticket_name      = models.CharField(max_length=100)
    price            = models.DecimalField(max_digits=10, decimal_places=2)
    quantity         = models.PositiveIntegerField(default=1)
    first_name       = models.CharField(max_length=100)
    email            = models.EmailField()
    status           = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    proof_image      = models.ImageField(upload_to='ticket_proofs/', null=True, blank=True)
    shipping_address = models.TextField(blank=True)
    address_token    = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    approved_at      = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.order_ref} — {self.first_name} ({self.ticket_name} x{self.quantity})'

    @staticmethod
    def generate_ref():
        chars = string.ascii_uppercase + string.digits
        return 'RG-TKT-' + ''.join(random.choices(chars, k=6))


class MeetGreetRequest(models.Model):
    """Meet & greet booking requests from Back Road Nation members."""

    STATUS_PENDING   = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_REJECTED  = 'rejected'
    STATUS_CHOICES   = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_REJECTED,  'Rejected'),
    ]

    member_name       = models.CharField(max_length=200)
    member_email      = models.EmailField()
    preferred_date    = models.CharField(max_length=50)
    time_slot         = models.CharField(max_length=50)
    city              = models.CharField(max_length=200)
    hotel_name        = models.CharField(max_length=200, blank=True)
    hotel_room_type   = models.CharField(max_length=50, blank=True)
    group_size        = models.CharField(max_length=50, blank=True)
    vip_extras        = models.TextField(blank=True)
    special_requests  = models.TextField(blank=True)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.member_name} — {self.preferred_date} @ {self.city}'


class SiteVisit(models.Model):
    """Page view tracking for admin PWA analytics."""
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    path       = models.CharField(max_length=500, default='/')
    user_agent = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
