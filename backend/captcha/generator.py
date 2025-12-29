# services/captcha_service.py
import random
import string
from PIL import Image, ImageDraw, ImageFont , ImageFilter
import io
import math
import base64
from django.conf import settings
import os

class CaptchaGenerator:
    def __init__(self):
        self.width = 200
        self.height = 80
        self.length = 5
        
    def generate_text(self):
        """Generate random text for CAPTCHA"""
        # Exclude confusing characters like 0, O, I, l, 1
        chars = 'A2B9C4D8E6F7G8H6J3K5L5M4N7P3Q9R2S3TUVW4X2YZA'
        return ''.join(random.choice(chars) for _ in range(self.length))
    
    def generate_image(self, text) -> Image:
        """Generate a simpler, more user-friendly CAPTCHA image"""
        # Create image
        image: Image = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(image)

        # Try to load a font, fallback to default if not found
        font_paths = [
            os.path.join(settings.BASE_DIR, "fonts", "dejavu-sans.bold.ttf"),
            os.path.join(settings.BASE_DIR, "fonts", "tomnr.ttf"),
            os.path.join(settings.BASE_DIR, "fonts", "ARIAL.TTF"),
        ]

        # Reduced background noise - fewer dots
        for _ in range(80):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            draw.point((x, y), fill=(
                random.randint(150, 220),
                random.randint(150, 220),
                random.randint(150, 220)
            ))

        # Fewer and lighter geometric shapes
        for _ in range(3):
            x = random.randint(5, self.width - 15)
            y = random.randint(5, self.height - 15)
            size = random.randint(4, 6)
            
            color = (random.randint(230, 245), random.randint(230, 245), random.randint(230, 245))
            
            if random.choice([True, False]):
                draw.ellipse([x, y, x + size, y + size], fill=color)
            else:
                draw.rectangle([x, y, x + size, y + size], fill=color)

        # Draw text with minimal rotation and jitter
        for i, char in enumerate(text):
            # Create a separate image for each char
            char_img = Image.new('RGBA', (50, 50), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_img)

            # Darker, more readable colors
            color = (
                random.randint(0, 80),
                random.randint(0, 80),
                random.randint(0, 80)
            )

            font_path = random.choice(font_paths)
            try:
                # Larger, bolder-looking font size
                font_size = random.randint(44, 48)
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()

            char_draw.text((5, 5), char, font=font, fill=color, stroke_width=1, stroke_fill=color)

            # Reduced rotation angle
            angle = random.randint(-15, 15)
            rotated_char = char_img.rotate(angle, expand=1)

            # Less jitter - characters more aligned
            x = 20 + i * 30 + random.randint(-5, 5)
            y = 15 + random.randint(-5, 5)
            image.paste(rotated_char, (x, y), rotated_char)

        # Fewer and lighter lines
        for _ in range(2):
            start = (random.randint(0, self.width), random.randint(0, self.height))
            end = (random.randint(0, self.width), random.randint(0, self.height))
            draw.line([start, end], fill=(
                random.randint(150, 200),
                random.randint(150, 200),
                random.randint(150, 200)
            ), width=1)

        # Very light blur
        image = image.filter(ImageFilter.GaussianBlur(radius=0.3))

        return image

    
    def image_to_base64(self, image:Image) -> str:
        """Convert PIL image to base64 string"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()