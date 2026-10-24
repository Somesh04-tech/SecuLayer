"""Crop and compose the element screenshots into report figures. The boxes were chosen by
looking at the screenshots taken from commit 105fe24 (see screenshots.mjs).
Usage: python crop_figures.py <figures-dir>"""
import sys
from pathlib import Path

from PIL import Image, ImageChops

d = Path(sys.argv[1])


def load(name):
    return Image.open(d / f"{name}.png").convert("RGB")


def trim_white(im, pad=12):
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if not box:
        return im
    l, t, r, b = box
    return im.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, im.width), min(b + pad, im.height)))


def save(im, name):
    im.save(d / f"{name}.png", optimize=True)
    print(name, im.size)


def compose(top, left, right, gap=24):
    """`top` across the full width, then `left` and `right` side by side under it."""
    width = max(top.width, left.width + gap + right.width)
    height = top.height + gap + max(left.height, right.height)
    out = Image.new("RGB", (width, height), (255, 255, 255))
    out.paste(top, (0, 0))
    out.paste(left, (0, top.height + gap))
    out.paste(right, (width - right.width, top.height + gap))
    return out


save(trim_white(load("ui-home")), "fig-home")
save(trim_white(load("ui-lab-before")), "fig-lab-before")
save(trim_white(load("ui-lab-how-built")), "fig-lab-how-built")
save(trim_white(load("ui-lab-ai-reads")), "fig-ai-reads")
save(load("ui-lab-anatomy-without").crop((0, 0, 1190, 1150)), "fig-anatomy-without")
save(load("ui-lab-anatomy-with").crop((0, 965, 1190, 1590)), "fig-anatomy-with")

# Inbox: both banners, then the unprotected run's actions and attacker's-server panel (left)
# beside the protected run's layer verdicts (right).
inbox = load("ui-lab-inbox-runs")
save(compose(inbox.crop((0, 0, 1190, 420)), inbox.crop((0, 1440, 575, 2000)), inbox.crop((605, 420, 1190, 1000))),
     "fig-inbox-runs")
# Support chat: both banners, then the leaked reply's end and the attacker's-server panel (left)
# beside the protected run's layer verdicts (right).
support = load("ui-lab-support-runs")
save(compose(support.crop((0, 0, 1190, 440)), support.crop((0, 1225, 580, 1800)), support.crop((610, 445, 1190, 1000))),
     "fig-support-runs")
# The whole run areas, for the appendix.
save(inbox, "fig-inbox-runs-full")
save(support, "fig-support-runs-full")
