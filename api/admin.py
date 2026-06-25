from django.contrib import admin
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Member, ContactMessage, NewsletterSubscriber
from .telegram import send_telegram


def approve_members(modeladmin, request, queryset):
    """Admin action: approve selected pending members, generate codes, email them."""
    approved = 0
    for member in queryset.filter(status=Member.STATUS_PENDING):
        # Generate unique code
        code = Member.generate_code()
        while Member.objects.filter(access_code=code).exists():
            code = Member.generate_code()

        member.access_code = code
        member.status      = Member.STATUS_ACTIVE
        member.is_active   = True
        member.approved_at = timezone.now()
        member.save()
        approved += 1

        # Email access code to member
        try:
            send_mail(
                subject='🎭 Your Brotherhood Access Code — Antonio Banderas Archive',
                message=(
                    f"Dear {member.email.split('@')[0]},\n\n"
                    f"Your payment has been verified. Welcome to The Brotherhood of the Mask!\n\n"
                    f"Your exclusive access code is:\n\n"
                    f"    {code}\n\n"
                    f"Use this code at: http://localhost:5173/private\n\n"
                    f"Inside you will find:\n"
                    f"  • Exclusive behind-the-scenes footage\n"
                    f"  • Unreleased director's commentary\n"
                    f"  • VIP event access & reservations\n"
                    f"  • Direct link to the private Telegram community\n\n"
                    f"Welcome to the inner circle.\n\n"
                    f"— The Antonio Banderas Archive Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[member.email],
                fail_silently=True,
            )
        except Exception:
            pass

        # Telegram confirmation to owner
        send_telegram(
            f"✅ *Member Approved!*\n\n"
            f"📧 `{member.email}`\n"
            f"🔑 Code: `{code}`\n"
            f"📨 Access code email sent."
        )

    modeladmin.message_user(request, f'{approved} member(s) approved and emailed their access codes.')


approve_members.short_description = '✅ Approve selected members & send access codes'


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display  = ['email', 'status', 'access_code', 'tier', 'joined_at', 'approved_at']
    list_filter   = ['status', 'is_active', 'joined_at']
    search_fields = ['email', 'access_code']
    readonly_fields = ['access_code', 'joined_at', 'approved_at']
    actions       = [approve_members]

    # Highlight pending members in red in list view
    def get_list_display(self, request):
        return self.list_display


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'subject', 'created_at', 'is_read']
    list_filter   = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'message']


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display  = ['email', 'subscribed_at', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['email']
