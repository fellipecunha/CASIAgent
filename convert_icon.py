from PIL import Image
import os

img = Image.open('c:\\CASI_agent\\casi_icon.png')
# Save as ICO
img.save('c:\\CASI_agent\\casi_icon.ico')
print("Successfully converted nearly to ICO.")
