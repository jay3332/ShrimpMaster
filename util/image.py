from discord import Colour
from io import BytesIO
from PIL import (
    Image, ImageOps, ImageDraw, ImageChops,
    ImageSequence, ImageEnhance, ImageFont
)
from wand import image
from .gif import save_transparent_gif
from .util import random
from .path import route
from math import sin
from textwrap import wrap
import numpy as np
import colorsys

rgb_to_hsv = np.vectorize(colorsys.rgb_to_hsv)
hsv_to_rgb = np.vectorize(colorsys.hsv_to_rgb)


def _clamp(n, low, high):
    return min(high, max(low, n))


def shift_hue(arr, hout):
    r, g, b, a = np.rollaxis(arr, axis=-1)
    h, s, v = rgb_to_hsv(r, g, b)
    h = hout
    r, g, b = hsv_to_rgb(h, s, v)
    arr = np.dstack((r, g, b, a))
    return arr


def colorize(img, hue):
    img = img.convert('RGBA')
    arr = np.array(np.asarray(img).astype('float'))
    return Image.fromarray(shift_hue(arr, hue/360.).astype('uint8'), 'RGBA')


def _pil_image_from_bytes(b, mode='RGBA'):
    try:
        return Image.open(BytesIO(b), mode)
    except ValueError:
        return Image.open(BytesIO(b))


def _wand_image_from_bytes(b):
    return image.Image(file=BytesIO(b))


def _get_bytes_buffer(result, mode="png"):
    buffer = BytesIO()
    _mode = mode
    if isinstance(result, Image.Image):
        result.save(buffer, format="png")
    elif isinstance(result, image.Image):
        _mode = result.format
        result.save(buffer)
    buffer.seek(0)
    return buffer, _mode


def magik(b, intensity=2):
    im = _wand_image_from_bytes(b)
    im.alpha_channel = True
    im.transform(resize='600x600>')
    im.liquid_rescale(
        width=int(im.width*0.5),
        height=int(im.height*0.5),
        delta_x=int(0.5*intensity),
        rigidity=0
    )
    im.liquid_rescale(
        width=int(im.width*1.5),
        height=int(im.height*1.5),
        delta_x=intensity,
        rigidity=0
    )
    return _get_bytes_buffer(im)


def swirl(b, intensity=240):
    im = _wand_image_from_bytes(b)
    im.swirl(intensity)
    return _get_bytes_buffer(im)


def sepia(b):
    im = _wand_image_from_bytes(b)
    im.transform(resize="512x512>")
    im.sepia_tone()
    return _get_bytes_buffer(im, im.format)


def rainbow(b):
    im = _wand_image_from_bytes(b)
    im.function("sinusoid", (3, -90, 0.2, 0.7))
    return _get_bytes_buffer(im)


def grayscale(b):
    im = _wand_image_from_bytes(b)
    im.transform_colorspace("gray")
    return _get_bytes_buffer(im)


def solarize(b):
    im = _wand_image_from_bytes(b)
    im.solarize(threshold=im.quantum_range/2)
    return _get_bytes_buffer(im)


def posterize(b, intensity=2):
    im = _wand_image_from_bytes(b)
    im.posterize(intensity)
    return _get_bytes_buffer(im)


def petpet(b, intensity=0):
    im = _pil_image_from_bytes(b, "RGBA")
    im = im.convert("RGBA")

    size = im.size
    big = (size[0] * 3, size[1] * 3)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + big, fill=255)
    mask = mask.resize(size, Image.ANTIALIAS)
    mask = ImageChops.darker(mask, im.split()[-1])
    im.putalpha(mask)  # this makes it a circle

    position_mapping = (
        (27, 31, 86, 90),
        (22, 36, 91, 90),
        (18, 41, 95, 90),
        (22, 41, 91, 91),
        (27, 28, 86, 91)
    )
    intensity_mapping = (
        (0, 0, 0, 0),
        (-7, 22, 8, 0),
        (-8, 30, 9, 6),
        (-3, 21, 5, 9),
        (0, 0, 0, 0)
    )

    frames = []
    im = im.convert("RGBA")
    translation_mapping = (0, 20, 34, 21, 0)

    for frame_index in range(5):
        spec = list(position_mapping[frame_index])
        for j, s in enumerate(spec):
            spec[j] = int(s+intensity_mapping[frame_index][j]*intensity)

        hand = Image.open(route("assets", "petpet", f'{frame_index}.png')).convert("RGBA")
        im = im.resize((int((spec[2]-spec[0])*1.2), int((spec[3]-spec[1])*1.2)), Image.ANTIALIAS).convert("RGBA")

        gif_frame = Image.new('RGBA', (112, 112), (0, 0, 0, 0))
        gif_frame.paste(im, (spec[0], spec[1]), im)
        gif_frame.paste(hand, (0, int(intensity * translation_mapping[frame_index])), hand)

        frames.append(gif_frame.convert("RGBA"))

    buffer = BytesIO()
    save_transparent_gif(frames, 64, buffer)
    buffer.seek(0)
    return buffer


def invert(b):
    frames = []
    parent_image = _pil_image_from_bytes(b)

    for im in ImageSequence.Iterator(parent_image):
        im = im.convert("RGBA")
        if any(dimension > 612 for dimension in im.size):
            im = im.resize((512, 512))  # Odd limits but ok

        r, g, b_, a = im.split()
        rgb_image = Image.merge('RGB', (r, g, b_))
        rgb_image = ImageOps.invert(rgb_image)
        r, g, b_ = rgb_image.split()

        frame = Image.merge('RGBA', (r, g, b_, a))
        frames.append(frame)

    buffer = BytesIO()
    if len(frames) == 1:
        _format = "png"
        frames[0].save(buffer, format="PNG")
    else:
        _format = "gif"
        save_transparent_gif(frames, parent_image.info.get("duration", 64), buffer)
    buffer.seek(0)
    return buffer, _format


def spin(b, speed=64):
    im = _pil_image_from_bytes(b)
    if any(dimension>256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)
    im = im.convert("RGBA")

    frames = [im.rotate(degree, resample=Image.BICUBIC, expand=0) for degree in range(0, 360, 6)]

    buffer = BytesIO()
    save_transparent_gif(frames, speed, buffer)
    buffer.seek(0)
    return buffer


def shake(b, intensity=10):
    frames = []
    im = _pil_image_from_bytes(b)
    im = im.resize((400, 400), Image.ANTIALIAS)
    for _ in range(20):
        frame = Image.new("RGBA", (600, 600), (0, 0, 0, 0))
        x_offset = intensity*2*(random()-0.5)
        y_offset = intensity*2*(random()-0.5)
        frame.paste(im, (round(100+x_offset), round(100+y_offset)))
        frames.append(frame)

    buffer = BytesIO()
    save_transparent_gif(frames, 50, buffer)
    buffer.seek(0)
    return buffer


def circular(b):
    frames = []
    parent_image = _pil_image_from_bytes(b, "RGBA")

    for im in ImageSequence.Iterator(parent_image):
        im = im.convert("RGBA")
        if any(dimension > 612 for dimension in im.size):
            im = im.resize((512, 512))  # Odd limits but ok

        size = im.size
        big = (size[0] * 3, size[1] * 3)
        mask = Image.new("L", big, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + big, fill=255)
        mask = mask.resize(size, Image.ANTIALIAS)
        mask = ImageChops.darker(mask, im.split()[-1])
        im.putalpha(mask)
        frames.append(im)

    buffer = BytesIO()
    if len(frames) == 1:
        _format = "png"
        frames[0].save(buffer, format="PNG")
    else:
        _format = "gif"
        save_transparent_gif(frames, parent_image.info.get("duration", 64), buffer)
    buffer.seek(0)
    return buffer, _format


def pixelate(b, across=12):
    frames = []
    parent_image = _pil_image_from_bytes(b, "RGBA")

    for im in ImageSequence.Iterator(parent_image):
        im = im.convert("RGBA")
        if any(dimension > 612 for dimension in im.size):
            im = im.resize((512, 512))  # Odd limits but ok

        old_size = im.size
        frame = im.resize((int(im.size[0]/across), int(im.size[1]/across)), resample=Image.BICUBIC)
        frames.append(frame.resize(old_size, resample=Image.NEAREST))

    buffer = BytesIO()
    if len(frames) == 1:
        _format = "png"
        frames[0].save(buffer, format="PNG")
    else:
        _format = "gif"
        save_transparent_gif(frames, parent_image.info.get("duration", 64), buffer)
    buffer.seek(0)
    return buffer, _format


def stretch(b):
    frames = []
    im = _pil_image_from_bytes(b, "RGBA")
    if any(dimension > 256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)

    for i in range(10, 41, 3):
        factor = i/10
        width = int(im.size[0]*factor)
        new_size = (width, im.size[1])
        offset = int((width - im.size[0])/2)

        new = im.resize(new_size, Image.ANTIALIAS)
        new = new.crop((offset, 0, new.size[0] - offset, new.size[1]))
        frames.append(new)

    for i in range(39, 10, -2):
        factor = i / 10
        width = int(im.size[0]*factor)
        new_size = (width, im.size[1])
        offset = int((width - im.size[0])/2)

        new = im.resize(new_size, Image.ANTIALIAS)
        new = new.crop((offset, 0, new.size[0] - offset, new.size[1]))
        frames.append(new)

    frames.append(im)
    buffer = BytesIO()
    save_transparent_gif(frames, 72, buffer)
    buffer.seek(0)
    return buffer


def revolve(b):
    frames = []
    im = _pil_image_from_bytes(b, "RGBA")
    if any(dimension > 256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)

    for i in range(10, -1, -1):
        i /= 10
        new_width = max(2, round(im.width*i))
        frame = Image.new("RGBA", im.size, (0, 0, 0, 0))
        offset = round((frame.width-new_width)/2)
        resized = im.resize((new_width, im.height))
        frame.paste(resized, (offset, 0), resized.convert("RGBA"))
        frames.append(frame)

    for i in range(1, 10):
        i /= 10
        new_width = max(2, round(im.width*i))
        frame = Image.new("RGBA", im.size, (0, 0, 0, 0))
        offset = round((frame.width-new_width)/2)
        resized = im.resize((new_width, im.height))
        frame.paste(resized, (offset, 0), resized.convert("RGBA"))
        frames.append(ImageOps.mirror(frame))

    for i in range(10, -1, -1):
        i /= 10
        new_width = max(2, round(im.width * i))
        frame = Image.new("RGBA", im.size, (0, 0, 0, 0))
        offset = round((frame.width - new_width) / 2)
        resized = im.resize((new_width, im.height))
        frame.paste(resized, (offset, 0), resized.convert("RGBA"))
        frames.append(ImageOps.mirror(frame))

    for i in range(1, 10):
        i /= 10
        new_width = max(2, round(im.width*i))
        frame = Image.new("RGBA", im.size, (0, 0, 0, 0))
        offset = round((frame.width-new_width)/2)
        resized = im.resize((new_width, im.height))
        frame.paste(resized, (offset, 0), resized.convert("RGBA"))
        frames.append(frame)

    buffer = BytesIO()
    save_transparent_gif(frames, 72, buffer)
    buffer.seek(0)
    return buffer


def bonk(b):
    frames = []
    im = _pil_image_from_bytes(b).resize((156, 156), Image.ANTIALIAS)
    im = im.convert("RGBA")

    size = im.size
    big = (size[0] * 3, size[1] * 3)
    mask = Image.new("L", big, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + big, fill=255)
    mask = mask.resize(size, Image.ANTIALIAS)
    mask = ImageChops.darker(mask, im.split()[-1])
    im.putalpha(mask)

    im = im.convert("RGBA")
    hammer = Image.open(route("assets", "bonk", "0.png")).convert("RGBA")
    frame = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    frame.paste(hammer, (0, 0), hammer)
    frame.paste(im.convert("RGBA"), (90, 90), im.convert("RGBA"))
    frames.append(frame)

    hammer = Image.open(route("assets", "bonk", "1.png")).convert("RGBA")
    frame = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    frame.paste(hammer, (0, 0), hammer)
    im = im.resize((im.width, 106), Image.ANTIALIAS).convert("RGBA")
    frame.paste(im, (90, 140), im)
    frames.append(frame)

    buffer = BytesIO()
    save_transparent_gif(frames, 300, buffer)
    buffer.seek(0)
    return buffer


def breathe(b):
    frames = []
    im = _pil_image_from_bytes(b, "RGBA")
    if any(dimension > 256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)

    for i in range(31):
        frame = Image.new("RGBA", im.size, (0, 0, 0, 0))
        factor = 0.1*sin(i/4.8)+0.9
        new_size = (
            round(im.size[0] * factor),
            round(im.size[1] * factor)
        )
        resized = im.resize(new_size)
        box = (
            round((im.size[0]-new_size[0])/2),
            round((im.size[1]-new_size[1])/2)
        )
        frame.paste(resized, box, resized.convert("RGBA"))
        frames.append(frame)

    buffer = BytesIO()
    save_transparent_gif(frames, 50, buffer)
    buffer.seek(0)
    return buffer


def fade(b):
    frames = []
    im = _pil_image_from_bytes(b, "RGBA")
    if any(dimension > 256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)

    im = im.convert("RGBA")

    for i in range(21):
        with Image.new('RGBA', im.size, (0, 0, 0, 0)) as parent:
            frame = im.copy()
            enhancer = ImageEnhance.Brightness(frame)
            result = enhancer.enhance(1 - i/20)
            parent.alpha_composite(result, (0, 0))
            frames.append(parent.convert("RGBA"))

    buffer = BytesIO()
    save_transparent_gif(frames, 50, buffer)
    buffer.seek(0)
    return buffer


def bounce(b):
    frames = []
    im = _pil_image_from_bytes(b, "RGBA")
    if any(dimension > 256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)

    for i in range(25):
        frame = Image.new("RGBA", (im.width, round(im.height*1.6)), (0, 0, 0, 0))
        factor = ((0.25*i)+(-0.01*i**2))/2.2
        height_up = round(im.height*factor)
        difference = frame.height - im.height
        y = difference - height_up

        # calculate "squish factor"
        if factor < .2:
            height_ratio = 1-(.2-factor)
            new_height = round(im.height * height_ratio)
            new = im.resize((im.width, new_height))
            height_offset = im.height - new_height
            frame.paste(new, (0, y+height_offset), new.convert("RGBA"))
        else:
            frame.paste(im, (0, y), im.convert("RGBA"))

        frames.append(frame)

    buffer = BytesIO()
    save_transparent_gif(frames, 50, buffer)
    buffer.seek(0)
    return buffer


def disco(b):
    frames = []
    im = _pil_image_from_bytes(b, "RGBA")
    if any(dimension > 256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)

    for _ in range(15):
        r, g, blue = Colour.random().to_rgb()
        overlay = Image.new("RGBA", im.size, (r, g, blue, 40))
        frame = Image.new("RGBA", im.size, (0, 0, 0, 0))
        try:
            frame.paste(im, (0, 0), im)
        except ValueError:
            frame.paste(im, (0, 0))

        frame.paste(overlay, (0, 0), overlay)
        frames.append(frame)

    buffer = BytesIO()
    save_transparent_gif(frames, 200, buffer)
    buffer.seek(0)
    return buffer


def shine(b):
    frames = []
    im = _pil_image_from_bytes(b, "RGBA")
    if any(dimension > 256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)

    width = max(2, int(im.size[0]/14.5))

    im = im.convert("RGBA")
    for box in range(0, im.width*2+1, round(im.width/8)):
        im_clone = im.resize(im.size, Image.ANTIALIAS)
        frame = Image.new("RGBA", im.size, (0, 0, 0, 0))
        pen = ImageDraw.Draw(frame)
        pen.line((-5, box+5, box+5, -5), fill=(256, 256, 256), width=width)
        composite = Image.composite(frame, im_clone, im_clone)
        im_clone.paste(composite, mask=composite)
        frames.append(im_clone)
    frames.append(im)

    buffer = BytesIO()
    durations = [60]*len(frames)
    durations[-1] = 2000
    save_transparent_gif(frames, durations, buffer)
    buffer.seek(0)
    return buffer


def huerotate(b):
    im = _pil_image_from_bytes(b, "RGBA")
    if any(dimension > 256 for dimension in im.size):
        im = im.resize((256, 256), Image.ANTIALIAS)

    frames = [colorize(im, degree) for degree in range(0, 360, 8)]

    buffer = BytesIO()
    save_transparent_gif(frames, 64, buffer)

    del frames
    buffer.seek(0)
    return buffer


def type_(message):
    frames = []
    buffer = ""
    message = message[:300].replace("\u200b", "")
    font = ImageFont.truetype(BytesIO(open(route("assets", "font.ttf"), "rb").read()), 24)
    wrapped = wrap(message, 30)
    height = (len(wrapped)*28 + 8) - 2
    message = '\n'.join(wrapped)

    frames.append(Image.new("RGBA", (440, height)))
    for char in message:
        buffer += char
        with Image.new("RGBA", (440, height)) as canvas:
            draw = ImageDraw.Draw(canvas)
            draw.text((4, 4), buffer, (255, 255, 255), font)
            frames.append(canvas)

    buffer = BytesIO()
    durations = [96]*len(frames)
    durations[-1] = 4000
    save_transparent_gif(frames, durations, buffer)
    buffer.seek(0)
    return buffer


def speed(b, factor):
    im = _pil_image_from_bytes(b)

    frames = []
    total_frames = 0
    total_delay = 0
    for frame in ImageSequence.Iterator(im):
        try:
            frames.append(frame.convert("RGBA"))
            total_delay += frame.info['duration']
            total_frames += 1
        except KeyError:
            buffer = BytesIO()
            frame.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer

    average_delay = total_delay/total_frames
    future_duration = average_delay/factor

    while future_duration<20:  # Because GIFs appear slow under this delay
        try:
            pop_index = random(1, len(frames)-2)
            frames.pop(pop_index)
        except (IndexError, KeyError, ValueError):
            break
        average_delay = total_delay/len(frames)
        future_duration = average_delay/factor

    buffer = BytesIO()
    save_transparent_gif(frames, future_duration, buffer)
    buffer.seek(0)
    return buffer


def seek(b, index=0):
    im = _pil_image_from_bytes(b)
    for i, frame in enumerate(ImageSequence.Iterator(im)):
        if i == index:
            buffer = BytesIO()
            frame.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
    return None


def explosion(b):
    im = _pil_image_from_bytes(b)
    png = False

    frames = [
        frame.resize((256, 256)).convert("RGBA")
        for frame in ImageSequence.Iterator(im)
    ]
    if len(frames) == 1:
        png = True
    frame_count = len(frames)

    bomb_frame_count = 0
    for i, frame in enumerate(ImageSequence.Iterator(Image.open(route("assets", "bomb.gif")))):
        if i == 0:
            continue
        frames.append(frame.resize((256, 256)).convert("RGBA"))
        bomb_frame_count += 1

    durations = (
        [600, *([100] * bomb_frame_count)] if png
        else [im.info.get("duration", 64)] * frame_count + [100] * bomb_frame_count
    )

    buffer = BytesIO()
    save_transparent_gif(frames, durations, buffer)
    buffer.seek(0)
    return buffer
