"""Render the two README figures from the adjacent, sourced release ledger."""

from collections import defaultdict
from datetime import date
from itertools import accumulate
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

ASSETS = Path(__file__).resolve().parents[1] / "assets/data-trends"
CATEGORIES = {"Ego": "#245CB4", "Real robot": "#007764", "UMI": "#A44829"}
INK = "#17283E"
MUTED = "#4C6077"
GRID = "#DCE5EF"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def read_ledger():
    ledger = (ASSETS / "released-hours.md").read_text(encoding="utf-8")
    as_of = date.fromisoformat(re.search(r"checked on \*\*(\d{4}-\d{2}-\d{2})", ledger)[1])
    releases = {name: defaultdict(float) for name in CATEGORIES}
    demos = {"Real robot": [], "UMI": []}
    for line in ledger.splitlines():
        if not line.startswith("|"):
            continue
        fields = [cell.strip() for cell in line.strip("|").split("|")]
        if re.fullmatch(r"\d{4}-\d{2}", fields[0]):
            month, category, _, hours, _, _ = fields
            releases[category][date.fromisoformat(month + "-01")] += float(hours)
        elif re.fullmatch(r"\d{4}", fields[0]):
            year, real, umi = fields
            for name, count in zip(demos, (real, umi)):
                if count:
                    demos[name].append((int(year), int(count)))
    return as_of, releases, demos


def compact(number, _position=None):
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}".rstrip("0").rstrip(".") + "k"
    return f"{number:g}"


def style_axis(ax, max_ticks):
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0, pad=6)
    ax.yaxis.set_major_locator(MaxNLocator(max_ticks))
    ax.yaxis.set_major_formatter(FuncFormatter(compact))


def hours_plot(as_of, releases):
    fig, axes = plt.subplots(3, 2, figsize=(11, 7.2), width_ratios=(1, 1))
    fig.subplots_adjust(left=.09, right=.975, bottom=.105, top=.775, hspace=.76, wspace=.20)
    fig.text(.07, .93, "Released dataset hours", fontsize=24, fontweight="bold", color=INK)
    fig.text(.07, .878, f"Cumulative hours from documented releases  ·  Through {as_of:%d %b %Y}",
             fontsize=11, color=MUTED)
    fig.text(.09, .822, "Release history", fontweight="bold", color=INK)
    fig.text(.573, .822, f"{as_of.year} detail", fontweight="bold", color=INK)

    first_year = min(month.year for changes in releases.values() for month in changes)
    year_start = date(as_of.year, 1, 1)
    for row, (category, color) in zip(axes, CATEGORIES.items()):
        changes = releases[category]
        months = sorted(changes)
        total = sum(changes.values())
        for index, ax in enumerate(row):
            start = date(first_year, 1, 1) if index == 0 else year_start
            baseline = sum(hours for month, hours in changes.items() if month < start)
            shown = [month for month in months if month >= start]
            xs = [start, *shown, as_of]
            ys = list(accumulate([baseline, *(changes[month] for month in shown), 0]))
            style_axis(ax, 3)
            ax.fill_between(xs, ys, step="post", color=color, alpha=.10)
            ax.step(xs, ys, where="post", color=color, linewidth=2.15)
            ax.scatter(shown, ys[1:-1], s=13, color=color, zorder=3)
            ax.set_xlim(start, as_of)
            ax.set_ylim(0, total * 1.14)
            if index == 0:
                ax.xaxis.set_major_locator(mdates.YearLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
                ax.set_title(category, loc="left", color=color, fontweight="bold", pad=8)
            else:
                ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 3, 5, 7, 9, 11]))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
                ax.set_title(f"≈{round(total):,} h tracked", loc="right", color=color,
                             fontweight="bold", pad=8)
    fig.text(.07, .027, "Selected releases with documented durations. Known repackagings are excluded. See the source ledger for scope.",
             fontsize=9, color=MUTED)
    fig.savefig(ASSETS / "released-hours.png", dpi=165, facecolor="white")
    plt.close(fig)


def demos_plot(as_of, demos):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.55))
    fig.subplots_adjust(left=.085, right=.963, bottom=.23, top=.60, wspace=.23)
    fig.text(.07, .86, "Demonstration count trends", fontsize=22, fontweight="bold", color=INK)
    fig.text(.07, .745, f"Project website counts with verified additions  ·  {as_of:%d %b %Y}",
             fontsize=11, color=MUTED)
    for ax, (category, data) in zip(axes, demos.items()):
        years, values = zip(*data)
        color = CATEGORIES[category]
        style_axis(ax, 3)
        ax.fill_between(years, values, color=color, alpha=.10)
        ax.plot(years, values, color=color, marker="o", markersize=4, linewidth=2.15)
        ax.set_xticks(years)
        ax.set_xlim(years[0] - .18, years[-1] + .18)
        ax.set_ylim(0, values[-1] * 1.14)
        ax.set_title(f"{category}   ·   {compact(values[-1])} demos", loc="left",
                     color=color, fontweight="bold", pad=10)
    fig.text(.07, .045, "Cumulative catalogue demo counts by dataset year. See the source ledger for additions and coverage.",
             fontsize=9, color=MUTED)
    fig.savefig(ASSETS / "website-demo-counts.png", dpi=165, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    snapshot, released_hours, demo_counts = read_ledger()
    hours_plot(snapshot, released_hours)
    demos_plot(snapshot, demo_counts)
