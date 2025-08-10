from urllib.parse import urlparse
import os

def get_cloudinary_public_id(avatar_url):
    """
    Extracts the public_id from a Cloudinary URL.
    """
    path = urlparse(avatar_url).path  # /<cloud_name>/image/upload/v1234567890/folder/filename.jpg
    parts = path.split("/")
    public_id = "/".join(parts[5:])  # folder/filename.jpg
    public_id = os.path.splitext(public_id)[0]  # folder/filename
    return public_id