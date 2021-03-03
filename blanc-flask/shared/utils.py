def get_user_first_image(user):
    user_image = next(iter(user.user_images or []), None)
    image_url = user_image.url if user_image else ""
