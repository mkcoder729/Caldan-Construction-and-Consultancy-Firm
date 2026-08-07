"""
One-time script to upload logo images to Cloudinary.
Run: python scripts/upload_logos_to_cloudinary.py
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')
django.setup()

import cloudinary
import cloudinary.uploader
from django.conf import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=settings.CLOUDINARY_STORAGE['API_KEY'],
    api_secret=settings.CLOUDINARY_STORAGE['API_SECRET'],
    secure=True
)

# Logo files to upload
logos = [
    ('static/images/logo.png', 'caldan/logo.png'),
    ('static/images/logo_light.png', 'caldan/logo_light.png'),
    ('static/images/logo_dark.png', 'caldan/logo_dark.png'),
    ('static/images/favicon.png', 'caldan/favicon.png'),
    ('static/images/og-image.png', 'caldan/og-image.png'),
]


def upload_logos():
    print("🌤️ Uploading logos to Cloudinary...")

    for local_path, cloudinary_path in logos:
        if os.path.exists(local_path):
            try:
                result = cloudinary.uploader.upload(
                    local_path,
                    public_id=cloudinary_path.replace('.png', '').replace('.jpg', ''),
                    overwrite=True,
                    folder='caldan'
                )
                print(f"  ✅ Uploaded: {local_path}")
                print(f"     URL: {result['secure_url']}")
                print()
            except Exception as e:
                print(f"  ❌ Failed: {local_path} - {str(e)}")
        else:
            print(f"  ⚠️ File not found: {local_path}")


if __name__ == '__main__':
    upload_logos()
    print("✅ Done!")

