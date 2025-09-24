# ========== Simple PNG to ICO Converter ==========

from PIL import Image
import os

def png_to_ico_simple(png_path, ico_path=None):
    """
    Convert PNG to ICO format (simple version)
    """
    if ico_path is None:
        ico_path = png_path.replace('.png', '.ico')
    
    try:
        # Open PNG image
        img = Image.open(png_path)
        
        # Convert to ICO format
        img.save(ico_path, format='ICO')
        
        print(f"✅ Successfully converted {png_path} to {ico_path}")
        return ico_path
        
    except Exception as e:
        print(f"❌ Error converting {png_path}: {e}")
        return None

# ========== Advanced PNG to ICO Converter (Multiple Sizes) ==========

def png_to_ico_advanced(png_path, ico_path=None, sizes=None):
    """
    Convert PNG to ICO with multiple sizes (recommended for favicons)
    """
    if ico_path is None:
        ico_path = png_path.replace('.png', '.ico')
    
    if sizes is None:
        sizes = [16, 32, 48, 64, 128, 256]  # Common favicon sizes
    
    try:
        # Open PNG image
        original_img = Image.open(png_path)
        
        # Create list of images in different sizes
        images = []
        
        for size in sizes:
            # Resize image
            resized_img = original_img.resize((size, size), Image.Resampling.LANCZOS)
            images.append(resized_img)
            print(f"📏 Created {size}x{size} version")
        
        # Save as ICO with multiple sizes
        original_img.save(ico_path, format='ICO', sizes=[(size, size) for size in sizes])
        
        print(f"✅ Successfully converted {png_path} to {ico_path} with {len(sizes)} sizes")
        return ico_path
        
    except Exception as e:
        print(f"❌ Error converting {png_path}: {e}")
        return None

# ========== Batch Converter ==========

def batch_convert_png_to_ico(directory, sizes=None):
    """
    Convert all PNG files in a directory to ICO format
    """
    if sizes is None:
        sizes = [16, 32, 48, 64, 128, 256]
    
    converted_count = 0
    
    for filename in os.listdir(directory):
        if filename.lower().endswith('.png'):
            png_path = os.path.join(directory, filename)
            ico_path = os.path.join(directory, filename.replace('.png', '.ico'))
            
            print(f"\n🔄 Converting {filename}...")
            
            if png_to_ico_advanced(png_path, ico_path, sizes):
                converted_count += 1
    
    print(f"\n🎉 Converted {converted_count} PNG files to ICO format")

# ========== Usage Examples ==========

if __name__ == "__main__":
    # Example 1: Simple conversion
    png_to_ico_simple("logo.png")
    
    # Example 2: Advanced conversion with custom sizes
    png_to_ico_advanced("logo.png", "favicon.ico", sizes=[16, 32, 48, 64])
    
    # Example 3: Custom paths
    png_to_ico_advanced("images/logo.png", "static/favicon.ico")
    
    # Example 4: Batch convert all PNGs in current directory
    # batch_convert_png_to_ico(".")

# ========== Installation Requirements ==========
"""
First install Pillow (PIL):

pip install Pillow

Then run this script with your PNG file:

python png_to_ico.py
"""

# ========== One-liner function for quick use ==========

def quick_convert(png_file):
    """Quick one-liner converter"""
    Image.open(png_file).save(png_file.replace('.png', '.ico'), format='ICO')
    print(f"Converted {png_file} to ICO!")

# ========== For Django Static Files ==========

def create_django_favicon(png_path, output_dir="static/images/"):
    """
    Create favicon files for Django project
    """
    import os
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create different favicon formats
    img = Image.open(png_path)
    
    # Standard favicon.ico
    favicon_path = os.path.join(output_dir, "favicon.ico")
    img.save(favicon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48)])
    
    # Apple touch icon
    apple_icon_path = os.path.join(output_dir, "apple-touch-icon.png")
    img.resize((180, 180), Image.Resampling.LANCZOS).save(apple_icon_path)
    
    # Android icons
    for size in [192, 512]:
        android_path = os.path.join(output_dir, f"android-chrome-{size}x{size}.png")
        img.resize((size, size), Image.Resampling.LANCZOS).save(android_path)
    
    print(f"✅ Created Django favicon files in {output_dir}")
    print("Add to your base.html:")
    print('<link rel="icon" type="image/x-icon" href="{% static \'images/favicon.ico\' %}">')
    print('<link rel="apple-touch-icon" sizes="180x180" href="{% static \'images/apple-touch-icon.png\' %}">')

# ========== Command Line Interface ==========

if __name__ == "__main__" and len(os.sys.argv) > 1:
    import sys
    
    if len(sys.argv) == 2:
        # Simple usage: python script.py image.png
        png_file = sys.argv[1]
        if os.path.exists(png_file):
            png_to_ico_advanced(png_file)
        else:
            print(f"❌ File not found: {png_file}")
    
    elif len(sys.argv) == 3:
        # Custom output: python script.py input.png output.ico
        png_file, ico_file = sys.argv[1], sys.argv[2]
        if os.path.exists(png_file):
            png_to_ico_advanced(png_file, ico_file)
        else:
            print(f"❌ File not found: {png_file}")
    
    else:
        print("Usage:")
        print("  python script.py input.png")
        print("  python script.py input.png output.ico")