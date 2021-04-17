from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plot
from io import BytesIO
import typing


def render_profile(
    username: str,
    discriminator: str,
    shrimp: int,
    vault: int,
    vault_space: int,
    level: int,
    xp: int
):
    pass  # Will work on this later


def line_graph(title, data, x_axis, y_axis):
    data = dict(sorted(list(data.items()), key=lambda _: _[0]))

    plot.plot(list(data.keys()), list(data.values()))
    plot.title(title)
    plot.xlabel(x_axis)
    plot.ylabel(y_axis)

    buffer = BytesIO()
    plot.savefig(buffer, format="png")
    buffer.seek(0)
    plot.close()
    return buffer
