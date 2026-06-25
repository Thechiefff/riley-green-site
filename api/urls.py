from django.urls import path
from . import views

urlpatterns = [
    path('health/',            views.health_check,         name='health'),
    path('members/signup/',    views.member_signup,         name='member-signup'),
    path('members/verify/',    views.verify_access_code,    name='verify-code'),
    path('members/logout/',    views.member_logout,         name='member-logout'),
    path('contact/',           views.contact_submit,        name='contact'),
    path('newsletter/',        views.newsletter_subscribe,  name='newsletter'),
    path('analytics/',         views.analytics,             name='analytics'),
    path('track/',             views.track_visit,           name='track-visit'),
    path('donate/',            views.donation_submit,       name='donate'),
    path('donate/upload-proof/<int:pk>/', views.donation_upload_proof, name='donate-upload-proof'),
    # Tickets
    path('tickets/order/',                           views.ticket_order,            name='ticket-order'),
    path('tickets/upload-proof/<str:order_ref>/',    views.ticket_upload_proof,     name='ticket-upload-proof'),
    path('tickets/webhook/',                         views.ticket_telegram_webhook, name='ticket-webhook'),
    path('tickets/submit-address/<str:order_ref>/',  views.ticket_submit_address,   name='ticket-submit-address'),
    path('tickets/status/<str:order_ref>/',          views.ticket_status,           name='ticket-status'),
    # Members proof upload (used by FanClub)
    path('members/upload-proof/<int:pk>/',           views.member_upload_proof,     name='member-upload-proof'),
    # Link-based approval
    path('members/approve/<str:token>/',             views.approve_member,          name='member-approve'),
    path('members/reject/<str:token>/',              views.reject_member,           name='member-reject'),
    # Meet & Greet
    path('meet-greet/',                              views.meet_greet_submit,       name='meet-greet'),
    # Admin PWA
    path('admin/members/',                           views.admin_list_members,      name='admin-members'),
    path('admin/generate-code/',                     views.admin_generate_code,     name='admin-generate-code'),
    path('admin/approve-member/<int:pk>/',           views.admin_approve_member,    name='admin-approve-member'),
    path('admin/clear-session/',                      views.admin_clear_session,     name='admin-clear-session'),
    path('fan-message/',                              views.fan_private_message,     name='fan-message'),
    path('admin/issue-code/',                        views.admin_issue_code,        name='admin-issue-code'),
    path('pledge/status/', views.pledge_status, name='pledge-status'),
    path('pledge/check/',  views.pledge_check,  name='pledge-check'),
    path('pledge/claim/',  views.pledge_claim,  name='pledge-claim'),
    path('pledge/submit/', views.pledge_submit, name='pledge-submit'),
    path('pledge/paypal-send/<str:token>/', views.pledge_paypal_send, name='pledge-paypal-send'),
]
