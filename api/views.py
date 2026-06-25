from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .models import Member, NewsletterSubscriber, DonationRequest, SiteVisit, TicketOrder, MeetGreetRequest
from .serializers import (
    MemberSignupSerializer, MemberResponseSerializer,
    AccessCodeVerifySerializer, ContactSerializer, NewsletterSerializer,
    DonationSerializer,
)
from .telegram import send_telegram, send_telegram_photo


def _send_approval_links(member: Member):
    """Send Telegram notification with proof screenshot, route, and correct price."""
    import secrets
    token = secrets.token_hex(32)
    member.approval_token = token
    member.save(update_fields=['approval_token'])

    base = settings.SITE_URL
    approve_url = f"{base}/api/members/approve/{token}/"
    reject_url  = f"{base}/api/members/reject/{token}/"

    # Detect route and price from member tier
    tier = (member.tier or '').lower()
    if 'pledge' in tier:
        route = 'Pledge Game  /pledge'
        price = '$500 USD'
    else:
        route = 'Direct Application  /fan-lounge'
        price = '$2,000 USD'

    caption = (
        f"PAYMENT PROOF — Back Road Nation\n\n"
        f"Name: {member.display_name}\n"
        f"Email: {member.email}\n"
        f"Amount: {price}\n"
        f"Route: {route}\n\n"
        f"[Approve & Send Fan Card]({approve_url})\n"
        f"[Reject]({reject_url})"
    )

    if member.proof_image:
        sent = send_telegram_photo(member.proof_image.path, caption)
        if sent:
            return

    send_telegram(caption)


def _send_membership_acknowledgment(member: Member):
    """Send simple acknowledgment — owner will follow up with PayPal details."""
    message = (
        f"Hey {member.display_name},\n\n"
        f"Thanks for applying to the Back Road Nation — Riley Green's exclusive inner circle!\n\n"
        f"We've received your application and our team will send you payment instructions "
        f"to this email address shortly. Please keep an eye on your inbox and check your spam folder.\n\n"
        f"Membership: Back Road Nation — $2,000 USD (one-time, lifetime)\n"
        f"Registered email: {member.email}\n\n"
        f"Once you've made payment, return to the website and upload your PayPal confirmation screenshot.\n\n"
        f"Back road and all the way,\n"
        f"— The Back Road Nation Team"
    )
    send_mail(
        subject='Back Road Nation — Application Received',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[member.email],
        fail_silently=True,
    )


def _send_fan_card_email(member: Member):
    """Send HTML fan card email to newly approved Back Road Nation member."""
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#080e08;font-family:'Georgia',serif;">
  <div style="max-width:560px;margin:0 auto;padding:40px 20px;">

    <div style="text-align:center;margin-bottom:32px;">
      <p style="color:#c8920a;font-size:11px;letter-spacing:4px;text-transform:uppercase;margin:0;">Official Membership Confirmation</p>
    </div>

    <div style="background:linear-gradient(135deg,#0d1a0d 0%,#111f11 50%,#0d1a0d 100%);border:1px solid #c8920a;border-radius:12px;padding:36px;position:relative;">
      <div style="border:1px solid rgba(200,146,10,0.3);border-radius:8px;padding:28px;text-align:center;">
        <p style="color:#c8920a;font-size:10px;letter-spacing:5px;text-transform:uppercase;margin:0 0 16px;">Back Road Nation</p>
        <h1 style="color:#f0ead0;font-size:28px;font-weight:900;margin:0 0 4px;letter-spacing:2px;">RILEY GREEN</h1>
        <p style="color:rgba(240,234,208,0.5);font-size:10px;letter-spacing:3px;margin:0 0 28px;">OFFICIAL FAN CLUB</p>

        <div style="background:rgba(200,146,10,0.08);border:1px solid rgba(200,146,10,0.25);border-radius:8px;padding:18px;margin-bottom:24px;">
          <p style="color:rgba(200,146,10,0.7);font-size:9px;letter-spacing:3px;text-transform:uppercase;margin:0 0 8px;">Your Access Code</p>
          <p style="color:#c8920a;font-size:26px;font-weight:700;letter-spacing:6px;margin:0;font-family:'Courier New',monospace;">{member.access_code}</p>
        </div>

        <p style="color:#f0ead0;font-size:14px;margin:0 0 4px;">Welcome, <strong>{member.display_name}</strong></p>
        <p style="color:rgba(240,234,208,0.5);font-size:11px;margin:0 0 20px;">Member since {member.approved_at.strftime('%B %Y') if member.approved_at else 'Today'}</p>

        <div style="border-top:1px solid rgba(200,146,10,0.2);padding-top:16px;">
          <p style="color:rgba(240,234,208,0.6);font-size:11px;line-height:1.8;margin:0;">
            Use your access code at <a href="{settings.SITE_URL}/riley-green/private" style="color:#c8920a;">{settings.SITE_URL}/riley-green/private</a><br>
            to enter the Back Road Lounge.
          </p>
        </div>
      </div>
    </div>

    <div style="text-align:center;margin-top:28px;">
      <p style="color:rgba(240,234,208,0.3);font-size:10px;letter-spacing:1px;margin:0;">
        This code is personal and non-transferable.<br>
        Keep it private — do not share.
      </p>
    </div>

  </div>
</body>
</html>
"""
    plain = (
        f"Welcome to the Back Road Nation, {member.display_name}!\n\n"
        f"Your membership has been approved.\n\n"
        f"Your Access Code: {member.access_code}\n\n"
        f"Use this code at {settings.SITE_URL}/riley-green/private to enter the Back Road Lounge.\n\n"
        f"Keep this code private — it is personal and non-transferable.\n\n"
        f"Back road and all the way,\n— The Back Road Nation Team"
    )
    send_mail(
        subject='Welcome to the Back Road Nation — Your Access Code',
        message=plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[member.email],
        html_message=html,
        fail_silently=True,
    )


def _send_donation_instructions(donation: DonationRequest):
    """Email donation payment details privately."""
    message = (
        f"Dear {donation.name},\n\n"
        f"Your generosity means the world. Thank you deeply for choosing to support "
        f"Riley Green's charitable mission.\n\n"
        f"To complete your donation of {donation.amount}, please send payment via PayPal "
        f"using your email address as the reference:\n\n"
        f"  Reference: {donation.email}   ← include this so we can acknowledge your gift\n\n"
        f"Our team will send you PayPal payment details shortly.\n\n"
        f"Once you have completed payment, please upload a screenshot of your PayPal "
        f"confirmation on the website so we can process your donation quickly.\n\n"
        f"Thank you again, {donation.name}. Your support creates real change.\n\n"
        f"With deep gratitude,\n"
        f"— The Riley Green Team"
    )
    send_mail(
        subject='Thank You — Donation Instructions',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[donation.email],
        fail_silently=True,
    )


# ─── Membership ──────────────────────────────────────────────────────────────

@api_view(['POST'])
def member_signup(request):
    serializer = MemberSignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    first_name = serializer.validated_data['first_name'].strip().title()
    email      = serializer.validated_data['email']

    existing = Member.objects.filter(email=email).first()
    if existing:
        if existing.status == Member.STATUS_ACTIVE:
            return Response({
                'status': 'already_active',
                'message': f'Welcome back, {existing.display_name}! Check your inbox for your access code.',
            })
        else:
            _send_membership_acknowledgment(existing)
            send_telegram(
                f"🤠 *Back Road Nation — Re-application*\n\n"
                f"👤 Name: *{existing.display_name}*\n"
                f"📧 `{existing.email}`\n"
                f"💰 Amount: *$2,000 USD*\n\n"
                f"➡️ Reply to their email with your PayPal address."
            )
            return Response({
                'status': 'pending',
                'message': f'Your application is still pending, {existing.display_name}. Our team will resend payment instructions to {email} shortly.',
            })

    member = Member.objects.create(first_name=first_name, email=email)
    _send_membership_acknowledgment(member)
    send_telegram(
        f"🤠 *New Back Road Nation Application — Send PayPal Details!*\n\n"
        f"👤 Name: *{member.display_name}*\n"
        f"📧 `{member.email}`\n"
        f"💰 Amount: *$2,000 USD*\n\n"
        f"➡️ Reply to their email with your PayPal address and ask them to include their email as the payment note."
    )

    return Response({
        'status':     'pending',
        'member_id':  member.id,
        'first_name': first_name,
        'message': f'Welcome, {first_name}! Our team will send payment instructions to {email} shortly.',
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def verify_access_code(request):
    serializer = AccessCodeVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    code         = serializer.validated_data['code'].strip().upper()
    client_token = request.data.get('session_token', None)

    member = Member.objects.filter(
        access_code=code,
        status=Member.STATUS_ACTIVE,
        is_active=True,
    ).first()

    if not member:
        return Response({
            'status': 'invalid',
            'message': 'Invalid or inactive Back Road Nation code. Please check and try again.',
        }, status=status.HTTP_401_UNAUTHORIZED)

    from django.utils import timezone as tz
    import secrets
    SESSION_HOURS = 24

    if member.session_token and member.session_started_at:
        age_hours      = (tz.now() - member.session_started_at).total_seconds() / 3600
        session_active = age_hours < SESSION_HOURS
        token_matches  = (client_token == member.session_token)

        if session_active and not token_matches:
            return Response({
                'status': 'session_conflict',
                'message': 'This access code is currently in use on another device. Please sign out there first, or wait 24 hours for the session to expire.',
            }, status=status.HTTP_409_CONFLICT)

    new_token = secrets.token_hex(32)
    member.session_token      = new_token
    member.session_started_at = tz.now()
    member.save(update_fields=['session_token', 'session_started_at'])

    return Response({
        'status': 'valid',
        'session_token': new_token,
        'member': MemberResponseSerializer(member).data,
    })


@api_view(['POST'])
def member_logout(request):
    """Clear the session token so the code can be used on another device."""
    code  = request.data.get('code', '').strip().upper()
    token = request.data.get('session_token', '')

    member = Member.objects.filter(
        access_code=code,
        session_token=token,
        status=Member.STATUS_ACTIVE,
    ).first()

    if member:
        member.session_token      = None
        member.session_started_at = None
        member.save(update_fields=['session_token', 'session_started_at'])

    return Response({'status': 'logged_out'})


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def member_upload_proof(request, pk):
    """FanClub: Upload PayPal screenshot for a membership application."""
    member = Member.objects.filter(pk=pk).first()
    if not member:
        return Response({'error': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)

    proof = request.FILES.get('proof_image')
    if not proof:
        return Response({'error': 'No image provided.'}, status=status.HTTP_400_BAD_REQUEST)

    member.proof_image = proof
    member.save(update_fields=['proof_image'])

    _send_approval_links(member)

    return Response({'status': 'uploaded', 'message': 'Screenshot received. We will review shortly.'})


@api_view(['GET'])
def approve_member(request, token):
    """Admin taps Telegram link → member approved, fan card emailed."""
    from django.http import HttpResponse
    import secrets as sec

    member = Member.objects.filter(approval_token=token).first()
    if not member:
        return HttpResponse("<h2>Link invalid or already used.</h2>", status=404, content_type='text/html')

    if member.status == Member.STATUS_ACTIVE:
        return HttpResponse(
            f"<h2>Already approved.</h2><p>{member.display_name} ({member.email}) is already an active member.</p>",
            content_type='text/html'
        )

    for _ in range(10):
        code = Member.generate_code()
        if not Member.objects.filter(access_code=code).exists():
            break

    member.access_code    = code
    member.status         = Member.STATUS_ACTIVE
    member.is_active      = True
    member.approved_at    = timezone.now()
    member.approval_token = None
    member.save(update_fields=['access_code', 'status', 'is_active', 'approved_at', 'approval_token'])

    _send_fan_card_email(member)

    send_telegram(
        f"✅ *Back Road Nation Member Approved*\n\n"
        f"👤 {member.display_name} — `{member.email}`\n"
        f"🔑 Code: `{member.access_code}`\n"
        f"Fan card emailed successfully."
    )

    return HttpResponse(f"""
        <html><body style="font-family:sans-serif;padding:40px;background:#080e08;color:#f0ead0;">
        <h2 style="color:#c8920a;">✅ Approved!</h2>
        <p><strong>{member.display_name}</strong> ({member.email}) is now a Back Road Nation member.</p>
        <p>Access code <strong style="color:#c8920a;">{member.access_code}</strong> sent to their email.</p>
        </body></html>
    """, content_type='text/html')


@api_view(['GET'])
def reject_member(request, token):
    """Admin taps reject link → member notified."""
    from django.http import HttpResponse

    member = Member.objects.filter(approval_token=token).first()
    if not member:
        return HttpResponse("<h2>Link invalid or already used.</h2>", status=404, content_type='text/html')

    member.approval_token = None
    member.save(update_fields=['approval_token'])

    send_mail(
        subject='Back Road Nation — Application Update',
        message=(
            f"Hi {member.display_name},\n\n"
            f"Unfortunately we were unable to verify your payment for your Back Road Nation membership.\n\n"
            f"If you believe this is an error, please contact us via the Contact page.\n\n"
            f"— The Back Road Nation Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[member.email],
        fail_silently=True,
    )

    send_telegram(f"❌ *Rejected* — {member.display_name} (`{member.email}`). Rejection email sent.")

    return HttpResponse(f"""
        <html><body style="font-family:sans-serif;padding:40px;background:#080e08;color:#f0ead0;">
        <h2 style="color:#e55;">❌ Rejected</h2>
        <p>{member.display_name} ({member.email}) has been notified.</p>
        </body></html>
    """, content_type='text/html')


# ─── Donation ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
def donation_submit(request):
    serializer = DonationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    donation = serializer.save()

    _send_donation_instructions(donation)

    send_telegram(
        f"💝 *New Donation Request — Back Road Nation!*\n\n"
        f"👤 Name: *{donation.name}*\n"
        f"📧 `{donation.email}`\n"
        f"💰 Amount: *{donation.amount}*\n"
        f"💬 _{donation.message[:200] if donation.message else 'No message'}_\n\n"
        f"Payment details emailed to donor."
    )

    return Response({
        'status':      'success',
        'donation_id': donation.id,
        'message': f'Thank you, {donation.name}. Donation instructions have been sent to {donation.email}.',
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def donation_upload_proof(request, pk):
    try:
        donation = DonationRequest.objects.get(pk=pk)
    except DonationRequest.DoesNotExist:
        return Response({'error': 'Donation not found.'}, status=status.HTTP_404_NOT_FOUND)

    proof = request.FILES.get('proof_image')
    if not proof:
        return Response({'error': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

    donation.proof_image = proof
    donation.save(update_fields=['proof_image'])

    send_telegram(
        f"📸 *Donation Proof Uploaded — Back Road Nation!*\n\n"
        f"👤 *{donation.name}*\n"
        f"📧 `{donation.email}`\n"
        f"💰 Amount: *{donation.amount}*"
    )

    send_mail(
        subject='Your Donation Has Been Received — Thank You',
        message=(
            f"Dear {donation.name},\n\n"
            f"We received your payment confirmation and our hearts are full.\n\n"
            f"You are extraordinary. In a world where so many look the other way, you chose to "
            f"reach out and make a difference — and that says everything about who you are.\n\n"
            f"Riley personally believes that the people who support causes beyond themselves are the "
            f"ones who truly keep the world moving forward. You are one of those people.\n\n"
            f"Your donation of {donation.amount} will go directly toward the communities, veterans, "
            f"and conservation efforts that Riley champions. Thank you for being a part of something "
            f"bigger than a concert or a song — you are part of the Back Road Nation family.\n\n"
            f"With so much gratitude,\n"
            f"— Riley Green & The Back Road Nation Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[donation.email],
        fail_silently=True,
    )

    return Response({'status': 'received', 'message': 'Thank you! Your donation has been received.'})


# ─── Contact ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
def contact_submit(request):
    serializer = ContactSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    contact = serializer.save()

    send_telegram(
        f"📩 *New Contact Message — Riley Green*\n\n"
        f"👤 Name: {contact.name}\n"
        f"📧 `{contact.email}`\n"
        f"📌 Subject: {contact.subject or 'None'}\n\n"
        f"💬 _{contact.message[:300]}_"
    )

    return Response({
        'status': 'success',
        'message': "Your message has been received. We'll get back to you shortly.",
    }, status=status.HTTP_201_CREATED)


# ─── Newsletter ───────────────────────────────────────────────────────────────

@api_view(['POST'])
def newsletter_subscribe(request):
    serializer = NewsletterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data['email']

    sub, created = NewsletterSubscriber.objects.get_or_create(email=email)
    if not created:
        return Response({'status': 'already_subscribed', 'message': "You're already subscribed!"})

    send_telegram(f"📰 *New Newsletter Signup — Riley Green*\n📧 `{email}`")

    return Response({
        'status': 'success',
        'message': "Welcome! You're now subscribed to updates.",
    }, status=status.HTTP_201_CREATED)


# ─── Analytics ────────────────────────────────────────────────────────────────

@api_view(['GET'])
def analytics(request):
    """Returns aggregated stats for the admin PWA dashboard."""
    from datetime import timedelta

    now      = timezone.now()
    today    = now.date()
    week_ago = now - timedelta(days=7)

    try:
        total_visits  = SiteVisit.objects.count()
        today_visits  = SiteVisit.objects.filter(created_at__date=today).count()
        week_visits   = SiteVisit.objects.filter(created_at__gte=week_ago).count()
        unique_total  = SiteVisit.objects.values('ip_address').distinct().count()
        unique_today  = SiteVisit.objects.filter(created_at__date=today).values('ip_address').distinct().count()
    except Exception:
        total_visits = today_visits = week_visits = unique_total = unique_today = 0

    members_total   = Member.objects.count()
    members_active  = Member.objects.filter(status=Member.STATUS_ACTIVE).count()
    members_pending = Member.objects.filter(status=Member.STATUS_PENDING).count()
    subscribers     = NewsletterSubscriber.objects.filter(is_active=True).count()
    donations_count = DonationRequest.objects.count()

    return Response({
        'status':    'healthy',
        'timestamp': now.isoformat(),
        'visits': {
            'total':        total_visits,
            'today':        today_visits,
            'unique_today': unique_today,
            'this_week':    week_visits,
            'unique_total': unique_total,
        },
        'members': {
            'total':   members_total,
            'active':  members_active,
            'pending': members_pending,
        },
        'subscribers': subscribers,
        'donations':   donations_count,
    })


@api_view(['POST'])
def track_visit(request):
    """Records a page view from the frontend SPA."""
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if ip:
        ip = ip.split(',')[0].strip()[:45]
    try:
        SiteVisit.objects.create(
            ip_address=ip or None,
            path=request.data.get('path', '/')[:500],
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
    except Exception:
        pass
    return Response({'ok': True})


# ─── Health ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
def health_check(request):
    return Response({
        'status': 'ok',
        'service': 'Riley Green Archive API',
        'members': Member.objects.count(),
        'pending': Member.objects.filter(status=Member.STATUS_PENDING).count(),
        'active':  Member.objects.filter(status=Member.STATUS_ACTIVE).count(),
    })


# ─── Tickets ──────────────────────────────────────────────────────────────────

TICKET_TIERS = {
    'vip-gold':     {'name': 'VIP Gold',     'price': 500},
    'floor-access': {'name': 'Floor Access', 'price': 200},
    'general':      {'name': 'General',      'price': 75},
    'family-pack':  {'name': 'Family Pack',  'price': 250},
}


def _send_ticket_acknowledgment_email(order: TicketOrder):
    total = order.price * order.quantity
    message = (
        f"Hey {order.first_name},\n\n"
        f"We've received your ticket request — thanks for choosing Back Road Nation!\n\n"
        f"  Order Ref:  {order.order_ref}\n"
        f"  Ticket:     {order.ticket_name} x{order.quantity}\n"
        f"  Total:      ${total:.2f} USD\n\n"
        f"Our team will send you payment instructions to this email address shortly. "
        f"Please keep an eye on your inbox (and check your spam folder just in case).\n\n"
        f"Once you've made the payment, come back to the site and upload your confirmation screenshot.\n\n"
        f"Back road and all the way,\n"
        f"— The Back Road Nation Team"
    )
    send_mail(
        subject=f'Back Road Nation — Ticket Request Received ({order.order_ref})',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=True,
    )


def _send_ticket_approval_buttons(order: TicketOrder):
    import requests as req
    total = order.price * order.quantity
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    req.post(url, json={
        'chat_id':    settings.TELEGRAM_CHAT_ID,
        'parse_mode': 'Markdown',
        'text': (
            f"🎟 *New Ticket Payment Proof — Riley Green!*\n\n"
            f"📋 Order: `{order.order_ref}`\n"
            f"👤 Name: *{order.first_name}*\n"
            f"📧 `{order.email}`\n"
            f"🎫 Ticket: *{order.ticket_name}* x{order.quantity}\n"
            f"💰 Total: *${total:.2f} USD*\n\n"
            f"Review the payment screenshot and approve or reject."
        ),
        'reply_markup': {
            'inline_keyboard': [[
                {'text': '✅ Approve & Send Address Form', 'callback_data': f'tkt_approve_{order.id}'},
                {'text': '❌ Reject',                      'callback_data': f'tkt_reject_{order.id}'},
            ]]
        }
    }, timeout=10)


def _send_ticket_address_email(order: TicketOrder):
    address_url = f"{settings.SITE_URL}/riley-green/tickets?ref={order.order_ref}&token={order.address_token}"
    message = (
        f"Hey {order.first_name},\n\n"
        f"Great news — your payment for {order.ticket_name} x{order.quantity} has been confirmed!\n\n"
        f"Order Ref: {order.order_ref}\n\n"
        f"To complete your order, we need to know where to mail your physical tickets.\n"
        f"Please click the link below and enter your shipping address:\n\n"
        f"  {address_url}\n\n"
        f"This link is unique to your order — please don't share it.\n\n"
        f"Your tickets will be prepared and shipped within 3–5 business days.\n\n"
        f"Can't wait to see you at the show,\n"
        f"— The Back Road Nation Team"
    )
    send_mail(
        subject=f'Back Road Nation — Payment Confirmed! Enter Your Shipping Address',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=True,
    )


def _send_ticket_rejection_email(order: TicketOrder):
    send_mail(
        subject=f'Back Road Nation — Ticket Order Update ({order.order_ref})',
        message=(
            f"Hey {order.first_name},\n\n"
            f"Unfortunately we were unable to verify your payment for order {order.order_ref}.\n\n"
            f"If you believe this is an error, please contact us via the Contact page with your order reference.\n\n"
            f"— The Back Road Nation Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=True,
    )


def _send_ticket_complete_email(order: TicketOrder):
    send_mail(
        subject=f'Back Road Nation — Tickets On Their Way! ({order.order_ref})',
        message=(
            f"Hey {order.first_name},\n\n"
            f"You're all set!\n\n"
            f"Order:       {order.order_ref}\n"
            f"Ticket:      {order.ticket_name} x{order.quantity}\n"
            f"Shipping to: {order.shipping_address}\n\n"
            f"Your tickets will be mailed within 3–5 business days.\n\n"
            f"See you out there,\n"
            f"— The Back Road Nation Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        fail_silently=True,
    )


@api_view(['POST'])
def ticket_order(request):
    tier_id    = request.data.get('ticket_tier', '').strip()
    first_name = request.data.get('first_name', '').strip().title()
    email      = request.data.get('email', '').strip().lower()
    quantity   = int(request.data.get('quantity', 1))

    if not tier_id or tier_id not in TICKET_TIERS:
        return Response({'error': 'Invalid ticket tier.'}, status=status.HTTP_400_BAD_REQUEST)
    if not first_name or not email:
        return Response({'error': 'Name and email are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if quantity < 1 or quantity > 10:
        return Response({'error': 'Quantity must be between 1 and 10.'}, status=status.HTTP_400_BAD_REQUEST)

    tier_info = TICKET_TIERS[tier_id]

    for _ in range(10):
        ref = TicketOrder.generate_ref()
        if not TicketOrder.objects.filter(order_ref=ref).exists():
            break

    order = TicketOrder.objects.create(
        order_ref   = ref,
        ticket_tier = tier_id,
        ticket_name = tier_info['name'],
        price       = tier_info['price'],
        quantity    = quantity,
        first_name  = first_name,
        email       = email,
    )

    _send_ticket_acknowledgment_email(order)

    send_telegram(
        f"🎟 *New Ticket Order — Send PayPal Details!*\n\n"
        f"📋 Order: `{order.order_ref}`\n"
        f"👤 Name: *{order.first_name}*\n"
        f"📧 Email: `{order.email}`\n"
        f"🎫 Ticket: *{order.ticket_name}* x{order.quantity}\n"
        f"💰 Total: *${order.price * order.quantity:.0f} USD*\n\n"
        f"➡️ Reply to their email with your PayPal address and tell them to include `{order.order_ref}` as the payment note."
    )

    return Response({
        'status':    'pending',
        'order_ref': order.order_ref,
        'message':   f'Payment instructions sent to {email}.',
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def ticket_upload_proof(request, order_ref):
    order = TicketOrder.objects.filter(order_ref=order_ref.upper()).first()
    if not order:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
    if order.status not in (TicketOrder.STATUS_PENDING, TicketOrder.STATUS_PROOF_UPLOADED):
        return Response({'error': 'This order cannot accept a proof upload.'}, status=status.HTTP_400_BAD_REQUEST)

    proof = request.FILES.get('proof_image')
    if not proof:
        return Response({'error': 'No image provided.'}, status=status.HTTP_400_BAD_REQUEST)

    order.proof_image = proof
    order.status      = TicketOrder.STATUS_PROOF_UPLOADED
    order.save(update_fields=['proof_image', 'status'])

    _send_ticket_approval_buttons(order)

    return Response({'status': 'uploaded', 'message': 'Screenshot received. We will review and notify you.'})


@api_view(['POST'])
def ticket_telegram_webhook(request):
    """Telegram bot webhook: handles Approve/Reject callback_query for ticket orders."""
    import secrets as sec
    import requests as req
    data = request.data
    callback = data.get('callback_query')
    if not callback:
        return Response({'ok': True})

    callback_id   = callback.get('id')
    callback_data = callback.get('data', '')
    chat_id       = callback.get('message', {}).get('chat', {}).get('id')
    message_id    = callback.get('message', {}).get('message_id')

    def answer(text):
        req.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
            json={'callback_query_id': callback_id, 'text': text},
            timeout=5,
        )

    def edit_message(text):
        req.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/editMessageText",
            json={
                'chat_id':    chat_id,
                'message_id': message_id,
                'text':       text,
                'parse_mode': 'Markdown',
            },
            timeout=5,
        )

    if callback_data.startswith('tkt_approve_'):
        order_id = int(callback_data.replace('tkt_approve_', ''))
        order = TicketOrder.objects.filter(id=order_id).first()
        if not order:
            answer('Order not found.')
            return Response({'ok': True})

        token = sec.token_hex(32)
        order.address_token = token
        order.status        = TicketOrder.STATUS_APPROVED
        order.approved_at   = timezone.now()
        order.save(update_fields=['address_token', 'status', 'approved_at'])

        _send_ticket_address_email(order)
        answer('✅ Approved! Address form link sent to buyer.')
        edit_message(
            f"✅ *APPROVED*\n\n"
            f"📋 `{order.order_ref}` — {order.first_name}\n"
            f"Address form sent to `{order.email}`."
        )

    elif callback_data.startswith('tkt_reject_'):
        order_id = int(callback_data.replace('tkt_reject_', ''))
        order = TicketOrder.objects.filter(id=order_id).first()
        if not order:
            answer('Order not found.')
            return Response({'ok': True})

        order.status = TicketOrder.STATUS_REJECTED
        order.save(update_fields=['status'])

        _send_ticket_rejection_email(order)
        answer('❌ Rejected. Buyer notified.')
        edit_message(
            f"❌ *REJECTED*\n\n"
            f"📋 `{order.order_ref}` — {order.first_name}"
        )

    return Response({'ok': True})


@api_view(['POST'])
def ticket_submit_address(request, order_ref):
    token   = request.data.get('token', '').strip()
    address = request.data.get('address', '').strip()

    if not address:
        return Response({'error': 'Shipping address is required.'}, status=status.HTTP_400_BAD_REQUEST)

    order = TicketOrder.objects.filter(
        order_ref=order_ref.upper(),
        address_token=token,
        status__in=[TicketOrder.STATUS_APPROVED, TicketOrder.STATUS_ADDRESS_NEEDED],
    ).first()

    if not order:
        return Response({'error': 'Invalid or expired link.'}, status=status.HTTP_404_NOT_FOUND)

    order.shipping_address = address
    order.status           = TicketOrder.STATUS_COMPLETE
    order.save(update_fields=['shipping_address', 'status'])

    _send_ticket_complete_email(order)

    send_telegram(
        f"📦 *Shipping Address Received — Riley Green!*\n\n"
        f"📋 `{order.order_ref}` — {order.first_name}\n"
        f"📧 `{order.email}`\n"
        f"🎫 {order.ticket_name} x{order.quantity}\n\n"
        f"📬 Address:\n_{order.shipping_address}_"
    )

    return Response({'status': 'complete', 'message': 'Shipping address saved. Tickets will be mailed shortly!'})


@api_view(['GET'])
def ticket_status(request, order_ref):
    token = request.GET.get('token', '')
    order = TicketOrder.objects.filter(order_ref=order_ref.upper()).first()
    if not order:
        return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if order.address_token and token == order.address_token:
        return Response({
            'status':      order.status,
            'order_ref':   order.order_ref,
            'ticket_name': order.ticket_name,
            'quantity':    order.quantity,
            'first_name':  order.first_name,
        })

    return Response({
        'status':    order.status,
        'order_ref': order.order_ref,
    })


# ─── Meet & Greet ─────────────────────────────────────────────────────────────

@api_view(['POST'])
def meet_greet_submit(request):
    """Back Road Nation members submit a meet & greet booking request."""
    data = request.data

    required = ['member_name', 'member_email', 'preferred_date', 'time_slot', 'city']
    for field in required:
        if not data.get(field, '').strip():
            return Response({'error': f'{field} is required.'}, status=status.HTTP_400_BAD_REQUEST)

    booking = MeetGreetRequest.objects.create(
        member_name      = data.get('member_name', '').strip(),
        member_email     = data.get('member_email', '').strip().lower(),
        preferred_date   = data.get('preferred_date', '').strip(),
        time_slot        = data.get('time_slot', '').strip(),
        city             = data.get('city', '').strip(),
        hotel_name       = data.get('hotel_name', '').strip(),
        hotel_room_type  = data.get('hotel_room_type', '').strip(),
        group_size       = data.get('group_size', '').strip(),
        vip_extras       = data.get('vip_extras', '').strip(),
        special_requests = data.get('special_requests', '').strip(),
    )

    extras_line = f"\nVIP Extras requested: {booking.vip_extras}" if booking.vip_extras else ''
    send_mail(
        subject='🤠 Back Road Nation — Meet & Greet Request Received!',
        message=(
            f"Hey {booking.member_name},\n\n"
            f"Well, I'll be — you're about to meet Riley! Your request is in and we couldn't be more excited.\n\n"
            f"Here's what we've got on file:\n\n"
            f"  Date Requested:  {booking.preferred_date}\n"
            f"  Time Slot:       {booking.time_slot}\n"
            f"  City:            {booking.city}\n"
            f"  Hotel:           {booking.hotel_name or 'TBD'}\n"
            f"  Room Type:       {booking.hotel_room_type or 'TBD'}\n"
            f"  Group Size:      {booking.group_size or 'Just me'}"
            f"{extras_line}\n\n"
            f"Our team will review your request and reach out within 5–7 business days "
            f"to confirm the details and finalize your experience.\n\n"
            f"Sit tight, partner — this is going to be something special.\n\n"
            f"Back Road forever,\n"
            f"— The Back Road Nation Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.member_email],
        fail_silently=True,
    )

    extras_str = booking.vip_extras or 'None'
    send_telegram(
        f"🤝 *New Meet & Greet Request!*\n\n"
        f"👤 *{booking.member_name}*\n"
        f"📧 `{booking.member_email}`\n"
        f"📅 Date: *{booking.preferred_date}* ({booking.time_slot})\n"
        f"📍 City: *{booking.city}*\n"
        f"🏨 Hotel: {booking.hotel_name or 'TBD'} ({booking.hotel_room_type or 'any'})\n"
        f"👥 Group: {booking.group_size or 'Solo'}\n"
        f"⭐ Extras: {extras_str}\n"
        f"💬 Notes: _{booking.special_requests[:200] if booking.special_requests else 'None'}_"
    )

    return Response({
        'status':  'received',
        'message': f"Your request is in, {booking.member_name}! We'll be in touch within 5–7 business days."
    }, status=status.HTTP_201_CREATED)


# ─── Admin PWA ────────────────────────────────────────────────────────────────

ADMIN_SECRET = settings.TELEGRAM_BOT_TOKEN.split(':')[0]  # first part of bot token as simple secret


def _check_admin(request):
    token = request.META.get('HTTP_X_ADMIN_TOKEN', '') or request.GET.get('token', '')
    return token == ADMIN_SECRET


@api_view(['GET'])
def admin_list_members(request):
    """PWA: List all members with their status, sorted newest first."""
    if not _check_admin(request):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    members = Member.objects.all().order_by('-joined_at')
    data = []
    for m in members:
        data.append({
            'id':          m.id,
            'first_name':  m.first_name or m.email.split('@')[0],
            'email':       m.email,
            'access_code': m.access_code,
            'status':      m.status,
            'tier':        m.tier,
            'joined_at':   m.joined_at.isoformat(),
            'approved_at': m.approved_at.isoformat() if m.approved_at else None,
            'is_active':   m.is_active,
        })
    return Response({'members': data, 'total': len(data)})


@api_view(['POST'])
def admin_generate_code(request):
    """PWA: Generate a new unique RG- access code (does NOT assign to a member)."""
    if not _check_admin(request):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    for _ in range(20):
        code = Member.generate_code()
        if not Member.objects.filter(access_code=code).exists():
            return Response({'code': code, 'status': 'generated'})

    return Response({'error': 'Could not generate unique code'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def admin_approve_member(request, pk):
    """PWA: Approve a pending member — generates code, marks active, sends fan card email."""
    if not _check_admin(request):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    member = Member.objects.filter(pk=pk).first()
    if not member:
        return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)

    if member.status == Member.STATUS_ACTIVE:
        return Response({'status': 'already_active', 'access_code': member.access_code})

    for _ in range(10):
        code = Member.generate_code()
        if not Member.objects.filter(access_code=code).exists():
            break

    member.access_code  = code
    member.status       = Member.STATUS_ACTIVE
    member.is_active    = True
    member.approved_at  = timezone.now()
    member.save(update_fields=['access_code', 'status', 'is_active', 'approved_at'])

    _send_fan_card_email(member)

    send_telegram(
        f"✅ *Member Approved via PWA*\n\n"
        f"👤 {member.display_name} — `{member.email}`\n"
        f"🔑 Code: `{member.access_code}`"
    )

    return Response({'status': 'approved', 'access_code': code, 'email': member.email})


@api_view(['POST'])
def admin_issue_code(request):
    """PWA: Directly create an active member+code — works immediately in the Private Lounge."""
    if not _check_admin(request):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    email      = request.data.get('email', '').strip().lower()
    first_name = request.data.get('first_name', '').strip().title() or 'Member'

    if not email:
        return Response({'error': 'email is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # Generate a unique code
    for _ in range(20):
        new_code = Member.generate_code()
        if not Member.objects.filter(access_code=new_code).exists():
            break
    else:
        return Response({'error': 'Could not generate a unique code. Try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Create member if not exists, otherwise update
    member, created = Member.objects.get_or_create(email=email)
    member.first_name  = first_name
    member.access_code = new_code
    member.status      = Member.STATUS_ACTIVE
    member.is_active   = True
    if not member.approved_at:
        member.approved_at = timezone.now()
    member.save()

    action = 'Created' if created else 'Updated'
    send_telegram(
        f"\U0001f511 *Admin-Issued Code ({action})*\n\n"
        f"\U0001f464 *{member.display_name}*\n"
        f"\U0001f4e7 `{member.email}`\n"
        f"\U0001f511 Code: `{member.access_code}`"
    )

    return Response({
        'status':  'issued',
        'code':    new_code,
        'email':   email,
        'created': created,
        'message': f'Code {new_code} is now active for {email}.',
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def fan_private_message(request):
    """Fan sends a private message directly to Riley — forwarded to owner's Telegram."""
    member_email = request.data.get('member_email', '').strip()
    member_name  = request.data.get('member_name', '').strip()
    subject      = request.data.get('subject', '').strip()
    message      = request.data.get('message', '').strip()

    if not message:
        return Response({'error': 'Message cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

    send_telegram(
        f"\U0001f48c *Private Message from Back Road Nation*\n\n"
        f"\U0001f464 *{member_name or 'A Member'}*\n"
        f"\U0001f4e7 `{member_email}`\n"
        f"\U0001f4cc Subject: _{subject or 'No subject'}_\n\n"
        f"\U0001f4ac *Message:*\n{message[:1500]}"
    )

    return Response({
        'status':  'sent',
        'message': 'Your message has been delivered privately to Riley. He reads these personally.',
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def admin_clear_session(request):
    """PWA: Force-clear a member's session so they can log in from any device."""
    if not _check_admin(request):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
    code  = request.data.get('code', '').strip().upper()
    email = request.data.get('email', '').strip().lower()
    if code:
        qs = Member.objects.filter(access_code=code)
    elif email:
        qs = Member.objects.filter(email=email)
    else:
        return Response({'error': 'Provide code or email'}, status=status.HTTP_400_BAD_REQUEST)
    updated = qs.update(session_token=None, session_started_at=None)
    if updated:
        m = qs.first()
        return Response({'status': 'cleared', 'email': m.email if m else '', 'code': m.access_code if m else ''})
    return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)


# ── PLEDGE SPOTS ────────────────────────────────────────────
import json as _json
import random as _random
import os as _os
import threading as _threading

_PLEDGE_FILE = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'data', 'pledge.json')
_TOTAL_SPOTS = 15
_pledge_lock = _threading.Lock()

def _read_data():
    try:
        with open(_PLEDGE_FILE) as f:
            return _json.load(f)
    except Exception:
        return {'claimed': 0, 'emails': []}

def _read_claimed():
    return _read_data().get('claimed', 0)

def _write_data(data):
    with open(_PLEDGE_FILE, 'w') as f:
        _json.dump(data, f)

def _write_claimed(n):
    data = _read_data()
    data['claimed'] = n
    _write_data(data)


@api_view(['GET'])
def pledge_status(request):
    """Return spots remaining and whether to show 'try again tomorrow'."""
    claimed = _read_claimed()
    spots   = max(0, _TOTAL_SPOTS - claimed)

    return Response({
        'spots':           spots,
        'available':       spots > 0,
        'retry_tomorrow':  spots == 0,
    })


@api_view(['GET'])
def pledge_check(request):
    """Check if an email has already pledged (JSON file or Django Member record)."""
    email = request.query_params.get('email', '').strip().lower()
    if not email:
        return Response({'pledged': False})
    # Check JSON counter file
    data = _read_data()
    if email in [e.lower() for e in data.get('emails', [])]:
        return Response({'pledged': True})
    # Also check Django Member model (created by pledge_submit)
    try:
        if Member.objects.filter(email__iexact=email).exists():
            return Response({'pledged': True})
    except Exception:
        pass
    return Response({'pledged': False})


@api_view(['POST'])
def pledge_claim(request):
    """Decrement the spots counter and record email when a pledge is submitted."""
    email = request.data.get('email', '').strip().lower()
    with _pledge_lock:
        data = _read_data()
        claimed = data.get('claimed', 0)
        emails  = data.get('emails', [])

        # Reject duplicate email
        if email and email in [e.lower() for e in emails]:
            return Response({'ok': False, 'duplicate': True, 'message': 'You have already pledged.'}, status=status.HTTP_409_CONFLICT)

        if claimed >= _TOTAL_SPOTS:
            return Response({'ok': False, 'spots': 0, 'message': 'All spots claimed.'}, status=status.HTTP_410_GONE)

        if email:
            emails.append(email)
        data['claimed'] = claimed + 1
        data['emails']  = emails
        _write_data(data)
        spots = max(0, _TOTAL_SPOTS - claimed - 1)
    return Response({'ok': True, 'spots': spots})


# ── PLEDGE SUBMIT ────────────────────────────────────────────
@api_view(['POST'])
def pledge_submit(request):
    """
    Full pledge form submission:
    1. Creates a pending Member record
    2. Sends Telegram message to admin with one-click APPROVE / REJECT links
    Admin clicks APPROVE → fan receives a $500 payment invitation email
    Admin clicks fan's proof upload → fan receives access code fan card
    """
    import secrets as _sec

    name     = request.data.get('name', '').strip()
    email    = request.data.get('email', '').strip().lower()
    city     = request.data.get('city', '').strip()
    score    = request.data.get('quiz_score', '0/3')
    pledges  = request.data.get('pledges', '')
    personal = request.data.get('personal_pledge', '')
    source   = request.data.get('source', '')

    if not email:
        return Response({'error': 'Email required'}, status=status.HTTP_400_BAD_REQUEST)

    # Reject duplicate email
    if Member.objects.filter(email__iexact=email).exists():
        return Response({'ok': False, 'duplicate': True, 'message': 'Already pledged.'})

    # Create pending member
    member = Member(
        first_name=name,
        email=email,
        status=Member.STATUS_PENDING,
        tier='Back Road Nation — Pledge Applicant',
        is_active=False,
    )
    member.save()

    # Generate one-time approval token
    token = _sec.token_hex(32)
    member.approval_token = token
    member.save(update_fields=['approval_token'])

    base         = settings.SITE_URL
    approve_url  = f"{base}/api/pledge/paypal-send/{token}/"
    reject_url   = f"{base}/api/members/reject/{token}/"

    score_tag = ' — PERFECT SCORE' if score == '3/3' else (' — 2/3' if '2' in score else ' — 1/3 or less')

    msg = (
        f"*NEW BACK ROAD NATION PLEDGE*\n\n"
        f"Name: {name}\n"
        f"Email: `{email}`\n"
        f"City: {city or '—'}\n"
        f"Source: {source or '—'}\n\n"
        f"Quiz Score: *{score}*{score_tag}\n\n"
        f"Pledges made:\n{pledges}\n\n"
        f"Personal pledge:\n_{personal or '—'}_\n\n"
        f"[Invite & Send Payment Request]({approve_url}) — sends $500 payment email to fan\n"
        f"[Reject]({reject_url})"
    )
    send_telegram(msg)

    # ── Send exclusive Telegram reward email to the pledger ──
    from django.core.mail import send_mail as _send_mail
    display_name = name or email.split('@')[0]
    html_reward = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f0e8;font-family:'Georgia',serif;">
  <div style="max-width:540px;margin:0 auto;padding:52px 32px;">

    <p style="font-size:11px;letter-spacing:5px;text-transform:uppercase;color:#9a7b3f;margin:0 0 36px">
      Back Road Nation
    </p>

    <h1 style="font-size:30px;font-weight:400;color:#0f0c08;margin:0 0 8px;line-height:1.1">
      You took the pledge.
    </h1>
    <p style="font-size:12px;letter-spacing:3px;text-transform:uppercase;color:#b8a898;margin:0 0 36px">
      Here's your reward.
    </p>

    <p style="font-size:15px;color:#4a3c28;line-height:1.85;margin:0 0 20px">
      Hey {display_name},
    </p>
    <p style="font-size:15px;color:#4a3c28;line-height:1.85;margin:0 0 28px">
      Because you participated in the Back Road Nation pledge, you've earned something 
      most fans will never get — direct access to Riley Green's private Telegram.
    </p>

    <div style="background:#0f0c08;padding:28px 32px;margin:0 0 32px">
      <p style="font-size:10px;letter-spacing:4px;text-transform:uppercase;color:#9a7b3f;margin:0 0 12px">
        Your Exclusive Access
      </p>
      <a href="https://t.me/RileyGreenTgram"
        style="font-size:22px;color:#c4a96a;font-family:'Georgia',serif;font-weight:400;text-decoration:none;display:block;margin:0 0 8px">
        t.me/RileyGreenTgram
      </a>
      <p style="font-size:12px;color:rgba(245,240,232,0.45);margin:0">
        Riley Green's private Telegram — for Back Road Nation members only
      </p>
    </div>

    <p style="font-size:14px;color:#4a3c28;line-height:1.85;margin:0 0 36px">
      This is not shared publicly. You're getting it because you showed up, took the quiz, 
      and made your pledge. That's exactly what Back Road Nation is about.
    </p>

    <p style="font-size:12px;color:#b8a898;border-top:1px solid #e0d8cc;padding-top:24px;line-height:1.7;margin:0">
      Keep this between us. This link is shared exclusively with pledge participants.<br>
      &mdash; The Back Road Nation Team
    </p>

  </div>
</body>
</html>"""

    _send_mail(
        subject='You took the pledge — here\'s your reward',
        message=(
            f"Hey {display_name},\n\n"
            f"Because you participated in the Back Road Nation pledge, you\'ve earned "
            f"direct access to Riley Green\'s private Telegram.\n\n"
            f"Your exclusive link: https://t.me/RileyGreenTgram\n\n"
            f"This is not shared publicly. Keep it between us.\n\n"
            f"— The Back Road Nation Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        html_message=html_reward,
        fail_silently=True,
    )

    return Response({'ok': True})


@api_view(['GET'])
def pledge_approve_invite(request, token):
    """
    Admin clicks the Telegram approve link.
    Fan receives a $500 payment invitation — NOT the access code yet.
    Access code is only issued AFTER payment proof is verified.
    """
    from django.http import HttpResponse
    from django.core.mail import send_mail as _send_mail

    member = Member.objects.filter(approval_token=token).first()
    if not member:
        return HttpResponse('<h2>Link invalid or already used.</h2>', status=404, content_type='text/html')

    if member.status == Member.STATUS_ACTIVE:
        return HttpResponse(
            f'<h2>Already active.</h2><p>{member.display_name} ({member.email}) is already a member.</p>',
            content_type='text/html'
        )

    # Move to pending_payment
    member.status = Member.STATUS_PENDING
    member.approval_token = None
    member.save(update_fields=['status', 'approval_token'])

    # Build the proof upload URL
    proof_url = f"{settings.SITE_URL}/api/members/upload-proof/{member.pk}/"
    lounge_url = f"{settings.SITE_URL}/upload-proof.html?id={member.pk}&ref=BRNATION-{member.pk:05d}"

    # Send payment invitation email
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f0e8;font-family:'Georgia',serif;">
  <div style="max-width:560px;margin:0 auto;padding:48px 32px;">

    <p style="font-size:11px;letter-spacing:4px;text-transform:uppercase;color:#9a7b3f;margin:0 0 40px;">Back Road Nation</p>

    <h1 style="font-size:36px;font-weight:400;color:#0f0c08;margin:0 0 8px;line-height:1.1;">
      Your pledge has been accepted.
    </h1>
    <p style="font-size:13px;letter-spacing:3px;text-transform:uppercase;color:#b8a898;margin:0 0 40px;">
      One step to go.
    </p>

    <p style="font-size:16px;color:#4a3c28;line-height:1.8;margin:0 0 24px;">
      Hey {member.display_name},
    </p>
    <p style="font-size:16px;color:#4a3c28;line-height:1.8;margin:0 0 24px;">
      Riley's team has reviewed your pledge and selected you for the Back Road Nation.
    </p>
    <p style="font-size:16px;color:#4a3c28;line-height:1.8;margin:0 0 40px;">
      There is one final step. The Back Road Nation carries a <strong>one-time lifetime membership fee of $500 USD</strong>. This grants you permanent access to the private fan lounge — exclusive photos, priority meet &amp; greet booking, early ticket access, and a direct line to Riley's team. No recurring charges, ever.
    </p>

    <div style="background:#0f0c08;padding:32px;margin:0 0 40px;">
      <p style="font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#9a7b3f;margin:0 0 16px;">Payment</p>
      <p style="font-size:22px;font-weight:400;color:#f5f0e8;margin:0 0 8px;">$500.00 USD</p>
      <p style="font-size:13px;color:rgba(245,240,232,0.5);margin:0 0 20px;line-height:1.6;">
        One-time · Lifetime membership · Non-refundable after access is issued
      </p>
      <p style="font-size:13px;color:rgba(245,240,232,0.6);line-height:1.6;margin:0;">
        Send payment via PayPal to: <strong style="color:#c8920a;">rileygreenzion@gmail.com</strong><br>
        Reference: <strong style="color:#c8920a;">BRNATION-{member.pk:05d}</strong>
      </p>
    </div>

    <p style="font-size:15px;color:#4a3c28;line-height:1.8;margin:0 0 16px;">
      Once you have made payment, upload your PayPal confirmation screenshot below. Your Back Road Nation fan card and access code will be issued within 24 hours of verification.
    </p>

    <a href="{lounge_url}" style="display:inline-block;background:#9a7b3f;color:#f5f0e8;text-decoration:none;padding:14px 32px;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin-bottom:40px;">
      Upload Payment Proof
    </a>

    <p style="font-size:12px;color:#b8a898;line-height:1.7;border-top:1px solid #e0d8cc;padding-top:24px;margin:0;">
      This invitation is personal and non-transferable. If you have any questions, reply to this email.<br><br>
      — The Back Road Nation Team
    </p>

  </div>
</body>
</html>"""

    _send_mail(
        subject='You\'ve been selected — Back Road Nation Membership',
        message=(
            f"Hey {member.display_name},\n\n"
            f"Your pledge has been accepted. To complete your Back Road Nation membership, "
            f"please send $500 USD via PayPal to rileygreenzion@gmail.com "
            f"with reference BRNATION-{member.pk:05d}.\n\n"
            f"Then upload your payment proof at: {lounge_url}\n\n"
            f"Your access code will be issued within 24 hours of verification.\n\n"
            f"— The Back Road Nation Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[member.email],
        html_message=html,
        fail_silently=True,
    )

    # Notify admin on Telegram
    send_telegram(
        f"Payment invitation sent to *{member.display_name}* ({member.email}).\n"
        f"Waiting for $500 payment proof upload."
    )

    return HttpResponse(f"""
        <html><body style="font-family:sans-serif;padding:48px;background:#f5f0e8;color:#0f0c08;max-width:500px;margin:0 auto">
        <p style="font-size:11px;letter-spacing:4px;text-transform:uppercase;color:#9a7b3f;margin:0 0 32px">Back Road Nation</p>
        <h2 style="font-size:28px;font-weight:400;margin:0 0 16px">Payment invitation sent.</h2>
        <p style="font-size:15px;color:#6b5c4a;line-height:1.7;margin:0 0 8px">
          <strong>{member.display_name}</strong> ({member.email}) has received a $500 payment invitation.
        </p>
        <p style="font-size:13px;color:#9a7b3f;letter-spacing:2px;text-transform:uppercase;margin-top:32px">
          Their access code will be issued after payment proof is verified.
        </p>
        </body></html>
    """, content_type='text/html')

# ── PAYPAL SEND — minimal message box ───────────────────────
from django.views.decorators.csrf import csrf_exempt as _csrf_exempt
@_csrf_exempt
def pledge_paypal_send(request, token):
    """
    GET  → Shows a minimal message-box style page with a single PayPal address field.
    POST → Sends the PayPal address to the fan's email and notifies admin on Telegram.
    """
    from django.http import HttpResponse
    from django.core.mail import send_mail as _send_mail

    member = Member.objects.filter(approval_token=token).first()

    if not member:
        return HttpResponse(
            '<html><body style="font-family:sans-serif;padding:32px;background:#f5f0e8;color:#6b5c4a;text-align:center;">'
            '<p>Link already used or invalid.</p>'
            '</body></html>',
            status=404, content_type='text/html'
        )

    # ── GET: minimal message box ──
    if request.method == 'GET':
        page = (
            '<!DOCTYPE html>'
            '<html><head>'
            '<meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">'
            '<title>Send PayPal Address</title>'
            '<style>'
            '*{box-sizing:border-box;margin:0;padding:0}'
            'html,body{height:100%;background:#0f0c08}'
            'body{display:flex;align-items:center;justify-content:center;padding:20px;font-family:Georgia,serif}'
            '.box{background:#f5f0e8;width:100%;max-width:400px;padding:28px;}'
            '.fan{font-family:sans-serif;font-size:11px;letter-spacing:3px;text-transform:uppercase;'
            'color:#9a7b3f;margin-bottom:12px}'
            '.name{font-size:18px;font-weight:400;color:#0f0c08;margin-bottom:4px}'
            '.email{font-family:sans-serif;font-size:13px;color:#b8a898;margin-bottom:24px}'
            '.divider{height:1px;background:#e0d8cc;margin-bottom:24px}'
            'label{display:block;font-family:sans-serif;font-size:10px;font-weight:600;'
            'letter-spacing:3px;text-transform:uppercase;color:#9a7b3f;margin-bottom:8px}'
            'input{display:block;width:100%;background:#fff;border:none;border-bottom:2px solid #0f0c08;'
            'font-family:Georgia,serif;font-size:18px;padding:8px 0;color:#0f0c08;outline:none;'
            'margin-bottom:24px}'
            'button{display:block;width:100%;background:#0f0c08;color:#f5f0e8;border:none;'
            'font-family:sans-serif;font-size:11px;font-weight:600;letter-spacing:3px;'
            'text-transform:uppercase;padding:14px;cursor:pointer}'
            'button:disabled{opacity:.4;cursor:default}'
            '.sent{display:none;text-align:center;padding:8px 0}'
            '.sent p{font-family:sans-serif;font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#9a7b3f}'
            '</style>'
            '</head>'
            '<body>'
            '<div class="box">'
            f'<p class="fan">Back Road Nation</p>'
            f'<p class="name">{member.display_name}</p>'
            f'<p class="email">{member.email}</p>'
            '<div class="divider"></div>'
            '<form id="f">'
            '<label>PayPal Address</label>'
            '<input type="email" id="pp" placeholder="your@paypal.com" value="rileygreenzion@gmail.com" required autofocus>'
            '<button type="submit" id="btn">Send to Fan</button>'
            '</form>'
            '<div class="sent" id="sent"><p>Sent.</p></div>'
            '</div>'
            '<script>'
            'document.getElementById("f").addEventListener("submit",async function(e){'
            'e.preventDefault();'
            'var btn=document.getElementById("btn");'
            'btn.disabled=true;btn.textContent="Sending...";'
            'var pp=document.getElementById("pp").value.trim();'
            'try{'
            'var r=await fetch(window.location.href,{'
            'method:"POST",'
            'headers:{"Content-Type":"application/x-www-form-urlencoded"},'
            'body:"paypal_email="+encodeURIComponent(pp)'
            '});'
            'if(r.ok){'
            'document.getElementById("f").style.display="none";'
            'document.getElementById("sent").style.display="block";'
            '}else{'
            'btn.disabled=false;btn.textContent="Send to Fan";alert("Error — try again.");'
            '}'
            '}catch(err){btn.disabled=false;btn.textContent="Send to Fan";}'
            '});'
            '</script>'
            '</body></html>'
        )
        return HttpResponse(page, content_type='text/html')

    # ── POST: send the PayPal address to the fan ──
    paypal_email = request.POST.get('paypal_email', '').strip()
    if not paypal_email:
        return HttpResponse('Missing PayPal address.', status=400, content_type='text/plain')

    # Clear token so link can't be reused
    member.status = Member.STATUS_PENDING
    member.approval_token = None
    member.save(update_fields=['status', 'approval_token'])

    lounge_url = f"{settings.SITE_URL}/upload-proof.html?id={member.pk}&ref=BRNATION-{member.pk:05d}"

    html_email = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#f5f0e8;font-family:Georgia,serif;">'
        '<div style="max-width:520px;margin:0 auto;padding:48px 32px;">'
        '<p style="font-size:11px;letter-spacing:4px;text-transform:uppercase;color:#9a7b3f;margin:0 0 32px">Back Road Nation</p>'
        '<h1 style="font-size:32px;font-weight:400;color:#0f0c08;margin:0 0 8px;line-height:1.1">Your pledge has been accepted.</h1>'
        '<p style="font-size:12px;letter-spacing:3px;text-transform:uppercase;color:#b8a898;margin:0 0 32px">One step remaining.</p>'
        f'<p style="font-size:15px;color:#4a3c28;line-height:1.8;margin:0 0 20px">Hey {member.display_name},</p>'
        '<p style="font-size:15px;color:#4a3c28;line-height:1.8;margin:0 0 32px">'
        "Riley's team has reviewed your pledge and selected you for the Back Road Nation. "
        'Complete your membership with a one-time fee of <strong>$500 USD</strong> — lifetime access, no recurring charges.'
        '</p>'
        '<div style="background:#0f0c08;padding:28px;margin:0 0 32px">'
        '<p style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#9a7b3f;margin:0 0 12px">Send Payment To</p>'
        f'<p style="font-size:22px;color:#f5f0e8;margin:0 0 4px;font-family:Georgia,serif">{paypal_email}</p>'
        '<p style="font-size:12px;color:rgba(245,240,232,0.45);margin:0 0 20px">via PayPal</p>'
        f'<p style="font-size:13px;color:rgba(245,240,232,0.6);margin:0">Reference: <strong style="color:#c8920a;letter-spacing:2px">BRNATION-{member.pk:05d}</strong></p>'
        '</div>'
        '<p style="font-size:14px;color:#4a3c28;line-height:1.8;margin:0 0 24px">'
        'Once paid, upload your PayPal confirmation screenshot at the link below. '
        'Your Back Road Nation access code will be issued within 24 hours.'
        '</p>'
        f'<a href="{lounge_url}" style="display:inline-block;background:#9a7b3f;color:#f5f0e8;'
        'text-decoration:none;padding:14px 32px;font-size:11px;letter-spacing:2px;text-transform:uppercase">Upload Payment Proof</a>'
        '<p style="font-size:11px;color:#b8a898;line-height:1.7;border-top:1px solid #e0d8cc;padding-top:24px;margin:40px 0 0">'
        'This invitation is personal and non-transferable. &mdash; The Back Road Nation Team'
        '</p>'
        '</div></body></html>'
    )

    _send_mail(
        subject="You've been selected — Back Road Nation",
        message=(
            f"Hey {member.display_name},\n\n"
            f"Your pledge has been accepted. Send $500 USD via PayPal to:\n\n"
            f"  {paypal_email}\n\n"
            f"Reference: BRNATION-{member.pk:05d}\n\n"
            f"Then upload your payment proof at: {lounge_url}\n\n"
            f"-- The Back Road Nation Team"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[member.email],
        html_message=html_email,
        fail_silently=True,
    )

    send_telegram(
        f"PayPal address sent to *{member.display_name}* ({member.email}).\n"
        f"Address used: `{paypal_email}`"
    )

    return HttpResponse('ok', content_type='text/plain')
