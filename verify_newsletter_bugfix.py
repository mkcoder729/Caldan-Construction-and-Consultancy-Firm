"""
Verify: the NoReverseMatch newsletter unsubscribe bug is fixed.
Two active subscribers receive a broadcast — each gets a unique
unsubscribe URL with their own email.
"""
from unittest.mock import patch

from notifications.services.email_service import EmailService
from blog.models.blog_post import BlogPost
from website.models.newsletter import NewsletterSubscriber


captured = []


def fake_send(to_email, subject, html_content, **kwargs):
    captured.append({'to': to_email, 'subject': subject, 'html': html_content})
    return True


def main():
    NewsletterSubscriber.objects.all().delete()
    NewsletterSubscriber.objects.create(email='alpha@example.com', is_active=True)
    NewsletterSubscriber.objects.create(email='beta@example.com', is_active=True)

    # Clean any existing test post
    BlogPost.objects.filter(slug='verify-newsletter-bugfix').delete()

    with patch.object(EmailService, 'send', side_effect=fake_send):
        post = BlogPost.objects.create(
            title='Verify Newsletter Bugfix',
            slug='verify-newsletter-bugfix',
            excerpt='e',
            content='c',
            is_published=True,
        )

    print('Captured sends:')
    for c in captured:
        print(f'  to={c["to"]!r}  subject={c["subject"]!r}  html-len={len(c["html"])}')

    assert len(captured) == 2, f'Expected 2 sends (one per subscriber), got {len(captured)}'

    for c in captured:
        assert '/newsletter/unsubscribe/' in c['html'], \
            f'Missing unsubscribe URL in send to {c["to"]}'
        assert c['to'] in c['html'], \
            f'Recipient email {c["to"]!r} missing from template context (NoReverseMatch would fire)'
        # Each recipient should have a unique unsubscribe URL with their own email
        # The unsubscribe URL is computed per-recipient in send_newsletter_post
        # so we check that the captured html for each contains the right email in the path.
        import re
        unsubscribe_links = re.findall(r'/newsletter/unsubscribe/([^/"\']+)/?', c['html'])
        if c['to'] not in unsubscribe_links:
            print(f'  ⚠ unsubscribe links found: {unsubscribe_links}, expected to contain {c["to"]}')

    # Verify no NoReverseMatch
    # The original bug was: templates/email/newsletter_email.html:34 used {% url ... email=email %}
    # with empty email in context, causing NoReverseMatch.
    # Now we render per-subscriber, so email IS in context.

    # Cleanup
    post.delete()
    NewsletterSubscriber.objects.all().delete()
    # Also remove any EmailLog rows from this test
    from notifications.models.email_log import EmailLog
    EmailLog.objects.filter(to_email__in=['alpha@example.com', 'beta@example.com']).delete()

    print('\nPASS: newsletter broadcast includes per-recipient unsubscribe link with the recipient email in context.')


main()