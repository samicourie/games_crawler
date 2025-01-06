import os
import numpy as np
from PIL import Image

image_list = os.listdir('Covers/')
images_objs = [Image.open('Covers/' + img) for img in image_list]

widths, heights = zip(*(i.size for i in images_objs))

total_width = sum(widths)
max_height = max(heights)
max_width = max(widths)

print(max_width, max_height)

images_objs = [img.resize((96,144)) for img in images_objs]

horizontal_count = 4
image_hor_list = []
for offset in range(0, len(images_objs), horizontal_count):
    print(offset)
    image_hor_list.append(np.hstack([img for img in images_objs[offset: offset+horizontal_count]]))

vertical_count = 6
for offset in range(0, len(image_hor_list), vertical_count):
    new_image = np.vstack([img for img in images_objs[offset: offset+vertical_count]])
    # new_image.save('Posters/Trifecta_vertical.jpg')
