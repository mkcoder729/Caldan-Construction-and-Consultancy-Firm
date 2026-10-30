from django.urls import path
from .views.public_views import (
    index,
    about,
    services,
    service_detail,
    projects,
    project_detail,
    contact,
    quote_request,
    thank_you,
    legal_privacy,
    legal_terms,
    legal_refunds,
    legal_cookies,
    newsletter_subscribe,
    newsletter_unsubscribe,
    blog,
    blog_detail,
)

app_name = "website"

urlpatterns = [
    # Main pages
    path("", index, name="index"),
    path("about/", about, name="about"),
    path("services/", services, name="services"),
    path("services/<slug:slug>/", service_detail, name="service_detail"),
    path("projects/", projects, name="projects"),
    path("projects/<int:project_id>/", project_detail, name="project_detail"),
    path("contact/", contact, name="contact"),
    path("quote/", quote_request, name="quote_request"),
    path("thank-you/", thank_you, name="thank_you"),

    # Blog pages
    path("blog/", blog, name="blog"),
    path("blog/<slug:slug>/", blog_detail, name="blog_detail"),

    # Legal pages
    path("legal/privacy/", legal_privacy, name="legal_privacy"),
    path("legal/terms/", legal_terms, name="legal_terms"),
    path("legal/refunds/", legal_refunds, name="legal_refunds"),
    path("legal/cookies/", legal_cookies, name="legal_cookies"),

    # Newsletter
    path("newsletter/subscribe/", newsletter_subscribe, name="newsletter_subscribe"),
    path("newsletter/unsubscribe/<str:email>/", newsletter_unsubscribe, name="newsletter_unsubscribe"),
]