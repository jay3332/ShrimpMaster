from scipy.interpolate import make_interp_spline
from util.util import in_executor
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
from matplotlib.patches import Polygon
import numpy as np
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter
import discord


def get_buffer(fig, axes):
    fig.delaxes(axes)
    fig.add_axes(axes)
    buffer = BytesIO()
    fig.savefig(buffer, transparent=True, bbox_inches="tight")
    axes.clear()
    fig.clf()
    plt.close(fig)
    return buffer


def create_gradient_array(color, *, alpha_min=0, alpha_max=1):
    z = np.empty((100, 1, 4), dtype=float)
    z[:, :, :3] = mcolors.colorConverter.to_rgb(color)
    z[:, :, -1] = np.linspace(alpha_min, alpha_max, 100)[:, None]
    return z


@in_executor()
def create_graph(x, y, **kwargs):
    color = str(kwargs.get("color"))
    fig, axes = plt.subplots()

    date_arr = np.array(sorted(x))
    value_arr = np.array(y)
    date_num = mdates.date2num(date_arr)

    date_num_smooth = np.linspace(date_num.min(), date_num.max(), 100) 
    spline = make_interp_spline(date_num, value_arr, k=1)
    value_np_smooth = spline(date_num_smooth)

    line, = axes.plot(mdates.num2date(date_num_smooth), value_np_smooth, color=color)

    if (alpha := line.get_alpha()) is None:
        alpha = 1.0
    z = create_gradient_array(color, alpha_max=alpha)
    offset = value_arr.max() * 0.20
    xmin, xmax, ymin, ymax = date_num.min(), date_num.max(), value_arr.min(), value_arr.max() + offset
    payload = dict(aspect='auto', extent=(xmin, xmax, ymin, ymax), origin='lower', zorder=line.get_zorder())
    im = axes.imshow(z, **payload)

    xy = np.column_stack((date_num_smooth, value_np_smooth))
    xy = np.vstack(((xmin, ymin), xy, (xmax, ymin), (xmin, ymin)))
    clip_path = Polygon(xy, facecolor='none', edgecolor='none', closed=True)
    axes.add_patch(clip_path)
    im.set_clip_path(clip_path)

    for side in 'bottom', 'top', 'left', 'right':
        axes.spines[side].set_color('white')

    for side, name in zip(("x", "y"), ("Date/Time", kwargs.get("y_axis"))):
        getattr(axes, side + 'axis').label.set_color('white')
        axes.tick_params(axis=side, colors=color)
        getattr(axes, f"set_{side}label")(name, fontsize=14, weight='bold')

    axes.get_xaxis().set_major_formatter(mdates.DateFormatter('%m/%d'))
    axes.grid(True)
    axes.autoscale(True)
    value = get_buffer(fig, axes)

    del im
    del clip_path
    del axes
    del line
    return value


@in_executor()
def process_image(avatar_bytes, target):
    with Image.open(avatar_bytes).convert('RGBA') as avatar, Image.open(target) as target:
        side = max(avatar.size)
        avatar = avatar.crop((0, 0, side, side))
        w, h = target.size
        avatar = avatar.resize((w, w))
        avatar = avatar.crop((0, 0, w, h+10))

        reducer = ImageEnhance.Brightness(avatar)
        background = reducer.enhance(0.25)
        background = background.filter(ImageFilter.GaussianBlur(12))

        gray_back = Image.new('RGBA', avatar.size, (*discord.Color.dark_theme().to_rgb(), 255))
        gray_back.paste(background, (0, 0), background)
        background = gray_back
        background.paste(target, (0, 0), target)

        to_send = BytesIO()
        background.save(to_send, format="PNG")
        gray_back.close()
        to_send.seek(0)
        return to_send


async def send_graph_to(destination, target, *graph_args, filename=None, content=None, embed=None, **graph_kwargs):
    filename = filename or 'graph.png'
    graph = await create_graph(*graph_args, **graph_kwargs)
    buffer = await process_image(target, graph)
    await destination.send(content, embed=embed, file=discord.File(buffer, filename))
