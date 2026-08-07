"""
Verify: save a published blog post →
  * every admin gets an in-app Notification (bell) but NO email
  * every active subscriber gets the newsletter email
"""
from unittest.mock import patch, MagicMock

from notifications.services.email_service import EmailService
from notifications.services.router_service import NotificationRouter
from blog.models.blog_post import BlogPost
from website.models.newsletter import NewsletterSubscriber


email_calls = []


def fake_email_send(to_email, subject, html_content, to_name='', user=None, email_type='GENERAL', attachments=None):
    email_calls.append({"to": to_email, "subject": subject, "type": email_type})
    return True


def fake_send_newsletter_post(cls, blog_post, subscribers, user=None):
    email_calls.append({
        "to": list(subscribers),
        "subject": f"New Blog Post: {blog_post.title}",
        "type": "NEWSLETTER",
    })
    return {"sent": len(subscribers), "failed": 0, "total": len(subscribers)}


def main():
    # 2 active subscribers
    NewsletterSubscriber.objects.all().delete()
    NewsletterSubscriber.objects.create(email="alpha@example.com", is_active=True)
    NewsletterSubscriber.objects.create(email="beta@example.com", is_active=True)

    with patch.object(EmailService, "send", side_effect=fake_email_send), \
         patch.object(EmailService, "send_newsletter_post", classmethod(fake_send_newsletter_post)):
        email_calls.clear()
        post = BlogPost.objects.create(
            title="Verify Bell-Only",
            slug="verify-bell-only",
            excerpt="e",
            content="c",
            is_published=True,
        )

    print("All email sends captured:")
    for e in email_calls:
        print(f"  -> {e['to']!r}  type={e['type']}  subject={e['subject']!r}")

    # 1. Subscriber broadcast fired
    newsletter_sends = [e for e in email_calls if e["type"] == "NEWSLETTER"]
    assert len(newsletter_sends) == 1, f"Expected 1 newsletter broadcast, got {len(newsletter_sends)}"
    assert set(newsletter_sends[0]["to"]) == {"alpha@example.com", "beta@example.com"}, \
        f"Newsletter broadcast did not reach both subscribers: {newsletter_sends[0]['to']}"
    print("\nPASS: newsletter broadcast hit both subscribers")

    # 2. NO admin PROJECT_UPDATE email
    admin_emails = [e for e in email_calls if e["type"] != "NEWSLETTER"]
    project_update = [e for e in admin_emails if "New blog post" in e["subject"]]
    assert len(project_update) == 0, \
        f"Admin PROJECT_UPDATE email still fired: {project_update}"
    print("PASS: no admin PROJECT_UPDATE email fired (bell only)")

    # 3. In-app Notification for the admin still exists (bell)
    from notifications.models.notification import Notification
    bells = Notification.objects.filter(
        title__icontains="New blog post: Verify Bell-Only"
    )
    assert bells.exists(), "Expected at least one in-app bell notification"
    print(f"PASS: {bells.count()} in-app bell notification(s) created for admins")

    # Cleanup
    BlogPost.objects.filter(slug="verify-bell-only").delete()
    NewsletterSubscriber.objects.all().delete()
    Notification.objects.filter(title__icontains="Verify Bell-Only").delete()
    print("\nAll assertions passed.")


main()
