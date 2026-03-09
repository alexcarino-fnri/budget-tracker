from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    # Create a new image with a white background
    img = Image.new('RGB', (size, size), color='#6366f1')
    d = ImageDraw.Draw(img)
    
    # Draw a simple "F" for FinTrack
    # Since we might not have a font, we'll draw a simple shape
    # Draw a white circle in the middle
    center = size // 2
    radius = size // 3
    d.ellipse([center - radius, center - radius, center + radius, center + radius], fill='white')
    
    # Draw a dollar sign or 'F' in the middle (simplified as a rectangle for now)
    rect_w = size // 6
    rect_h = size // 3
    d.rectangle([center - rect_w//2, center - rect_h//2, center + rect_w//2, center + rect_h//2], fill='#6366f1')

    # Ensure directory exists
    os.makedirs('static/images', exist_ok=True)
    
    # Save the image
    img.save(f'static/images/{filename}')
    print(f"Created {filename}")

if __name__ == "__main__":
    create_icon(192, 'icon-192x192.png')
    create_icon(512, 'icon-512x512.png')
