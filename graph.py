from datetime import datetime
import os

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from scipy.ndimage import gaussian_filter1d

import polars as pl

FONT_PATH = os.path.join('resources', 'font.otf')
fm.fontManager.addfont(FONT_PATH)
CUSTOM_FONT_NAME = fm.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams['font.family'] = CUSTOM_FONT_NAME


def save_hist(x, y, path, current_week=None, week_start_dates=None, week_durations=None,
              n_weeks=None):
    x_np = np.asarray(x, dtype=float)
    y_np = np.asarray(y, dtype=float)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_facecolor(SISO_SURFACE)
    ax.set_facecolor(SISO_SURFACE)

    if len(x_np):
        order = np.argsort(x_np)
        x_np, y_np = x_np[order], y_np[order]
        colors = [SISO_BASELINE] * len(x_np)
        legend_handles = []

        # Keep the current week's bar out of the trend and color coding: it is
        # still in progress and its count is not comparable to completed weeks.
        trend_mask = np.ones(len(x_np), dtype=bool)
        if current_week is not None:
            trend_mask &= x_np != current_week
        trend_x, trend_y = x_np[trend_mask], y_np[trend_mask]
        if len(trend_x) > 1:
            order = np.argsort(trend_x)
            trend_x, trend_y = trend_x[order], trend_y[order]
            # Interpolate onto a dense weekly timeline, then blur by roughly 1.5
            # weeks. Unlike a spline through every bar, this reveals the broad trend.
            x_s = np.linspace(trend_x.min(), trend_x.max(), max(300, len(trend_x) * 30))
            y_s = np.interp(x_s, trend_x, trend_y)
            samples_per_week = (len(x_s) - 1) / max(trend_x.max() - trend_x.min(), 1)
            y_s = gaussian_filter1d(y_s, sigma=max(samples_per_week * 1.5, 1), mode='nearest')
            # Smooth and classify against the complete history even when only
            # the latest weeks are shown.
            if n_weeks is not None:
                end_week = current_week if current_week is not None else x_np.max()
                first_week = end_week - n_weeks + 1
                trend_visible = (x_s >= first_week) & (x_s <= end_week)
                plot_x_s, plot_y_s = x_s[trend_visible], y_s[trend_visible]
            else:
                plot_x_s, plot_y_s = x_s, y_s
            ax.plot(plot_x_s, plot_y_s, color='#5e8fa8', linewidth=2.5,
                    solid_capstyle='round', zorder=3, label='Andazzo smussato')

            trend_at_weeks = np.interp(x_np, x_s, y_s)
            good, bad = '#a8c9ad', '#d9aaa3'
            for i, (week, count, baseline) in enumerate(zip(x_np, y_np, trend_at_weeks)):
                if current_week is not None and week == current_week:
                    continue
                margin = max(2, baseline * 0.25)
                if count >= baseline + margin:
                    colors[i] = good
                elif count <= baseline - margin:
                    colors[i] = bad

            if good in colors:
                legend_handles.append(Patch(facecolor=good, label='Settimana buona'))
            if bad in colors:
                legend_handles.append(Patch(facecolor=bad, label='Settimana fiacca'))
            legend_handles.append(plt.Line2D([], [], color='#5e8fa8', linewidth=2.5,
                                             label='Andazzo smussato'))

        if n_weeks is not None:
            end_week = current_week if current_week is not None else x_np.max()
            first_week = end_week - n_weeks + 1
            visible = (x_np >= first_week) & (x_np <= end_week)
            plot_x, plot_y = x_np[visible], y_np[visible]
            plot_colors = [color for color, keep in zip(colors, visible) if keep]
            ax.set_xlim(first_week - 0.5, end_week + 0.5)
        else:
            plot_x, plot_y, plot_colors = x_np, y_np, colors
            ax.set_xlim(x_np.min() - 0.5, x_np.max() + 0.5)

        ax.bar(plot_x, plot_y, width=0.8, color=plot_colors, alpha=0.75, zorder=2)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, min_n_ticks=1))
        if week_durations:
            annotations = [
                (week, days) for week, days in sorted(week_durations)
                if days > 8 and (n_weeks is None or first_week <= week <= end_week)
            ]
            annotation_weeks = {week for week, _ in annotations}
            for week, days in annotations:
                # Consecutive long weeks share the space above the bars. Alternate
                # their labels between above and inside the bin to keep them clear.
                run_start = week
                while run_start - 1 in annotation_weeks:
                    run_start -= 1
                inside = (week - run_start) % 2 == 1
                count = np.interp(week, x_np, y_np)
                if inside:
                    ax.annotate('{}gg'.format(days), xy=(week, count), xytext=(-1, -4),
                                textcoords='offset points', ha='center', va='top',
                                rotation=90, fontsize=7, color=SISO_INK_MUTED_2,
                                fontfamily=CUSTOM_FONT_NAME, zorder=4)
                else:
                    ax.annotate('{}gg'.format(days), xy=(week, count), xytext=(-1, 5),
                                textcoords='offset points', ha='center', va='bottom',
                                rotation=90, fontsize=7, color=SISO_INK_MUTED_2,
                                fontfamily=CUSTOM_FONT_NAME, zorder=4)
        if legend_handles:
            ax.legend(handles=legend_handles, frameon=False, labelcolor=SISO_INK_MUTED,
                      fontsize=8)
        # Mark each quarter's first available visible week, using Italian month names.
        if week_start_dates:
            month_names = ('Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                           'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic')
            quarter_ticks = []
            seen_quarters = set()
            for week, start_date in sorted(week_start_dates):
                if n_weeks is not None and not (first_week <= week <= end_week):
                    continue
                try:
                    date = datetime.strptime(start_date, '%d/%m/%y')
                except (TypeError, ValueError):
                    continue
                quarter = (date.year, (date.month - 1) // 3)
                if quarter in seen_quarters:
                    continue
                seen_quarters.add(quarter)
                quarter_month = quarter[1] * 3 + 1
                quarter_ticks.append((week, '{}-{:02d}'.format(
                    month_names[quarter_month - 1], date.year % 100
                )))
            if quarter_ticks:
                tick_weeks, tick_labels = zip(*quarter_ticks)
                quarter_ax = ax.twiny()
                quarter_ax.set_xlim(ax.get_xlim())
                quarter_ax.set_xticks(tick_weeks)
                quarter_ax.set_xticklabels(tick_labels, rotation=90, ha='center', va='top')
                quarter_ax.xaxis.set_ticks_position('bottom')
                quarter_ax.xaxis.set_label_position('bottom')
                quarter_ax.spines['bottom'].set_position(('outward', 34))
                quarter_ax.spines['bottom'].set_color(SISO_BASELINE)
                quarter_ax.spines['top'].set_visible(False)
                quarter_ax.patch.set_visible(False)
                quarter_ax.tick_params(axis='x', colors=SISO_INK_MUTED, labelsize=8,
                                       length=0, pad=3)
                for label in quarter_ax.get_xticklabels():
                    label.set_rotation(90)
                    label.set_fontfamily(CUSTOM_FONT_NAME)

    ax.set_title('Andazzo — frigo giocate per settimana', color=SISO_INK_PRIMARY,
                 fontsize=14, loc='left', pad=14, fontfamily=CUSTOM_FONT_NAME)
    ax.set_xlabel('Settimane', color=SISO_INK_MUTED, fontsize=9, fontfamily=CUSTOM_FONT_NAME)
    ax.xaxis.set_label_coords(0.5, -0.29 if week_start_dates else -0.08)
    ax.set_ylabel('Frigo giocate', color=SISO_INK_MUTED, fontsize=9, fontfamily=CUSTOM_FONT_NAME)
    ax.grid(axis='y', color=SISO_GRID, linewidth=0.8, zorder=0)
    ax.grid(axis='x', visible=False)
    for spine in ('top', 'right', 'left'):
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color(SISO_BASELINE)
    ax.spines['bottom'].set_linewidth(0.8)
    ax.tick_params(axis='both', colors=SISO_INK_MUTED, labelsize=8, length=0)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(CUSTOM_FONT_NAME)

    fig.tight_layout()
    if week_start_dates:
        fig.subplots_adjust(bottom=0.24)
    plt.savefig(path, facecolor=SISO_SURFACE)
    plt.close(fig)


PLAYER_COLORS = {
    'fraraga': '#d58484',
    'tridello': '#e6ab98',
    'chris': '#e6b68a',
    'cappiello': '#d5c291',
    'coniglio': '#e6e28a',
    'defava': '#d6e698',
    'mule': '#b2d584',
    'dubious': '#b1e698',
    'eughe': '#92e68a',
    'felaco': '#91d59c',
    'fanelli': '#8ae6af',
    'eppol': '#98e6ca',
    'giompy': '#98dde6',
    'marviglio': '#8ac5e6',
    'ilfato': '#91acd5',
    'kadaber': '#8a99e6',
    'grimama': '#9f98e6',
    'remokon': '#9e84d5',
    'peppedallap': '#c498e6',
    'deltempo': '#d38ae6',
    'spite': '#d591d3',
    'sergio': '#e68acc',
    'texwilly': '#e698bd',
    'bot': '#d58498',
}
DEFAULT_PLAYER_COLOR = '#8f8d86'
MAX_HIGHLIGHTED = 8

SISO_SURFACE = "#ededde"
SISO_INK_PRIMARY = "#242424"
SISO_INK_MUTED = "#637C83"
SISO_INK_MUTED_2 = "#857457"
SISO_GRID = '#e1e0d9'
SISO_BASELINE = '#c3c2b7'
SISO_BG_LINE = '#c3c2b7'


def siso_progression(progression, path, season_name):
    '''progression: dict player -> list of cumulative siso scores (index 0 = start of season).'''
    n = max((len(v) for v in progression.values()), default=1) - 1
    x = list(range(n + 1))

    ranked = sorted(progression.items(), key=lambda kv: kv[1][-1], reverse=True)
    highlighted = ranked[:MAX_HIGHLIGHTED]
    background = ranked[MAX_HIGHLIGHTED:]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_facecolor(SISO_SURFACE)
    ax.set_facecolor(SISO_SURFACE)

    for _, values in background:
        ax.plot(x, values, color=SISO_BG_LINE, linewidth=1, alpha=0.5, zorder=1)

    for name, values in highlighted:
        color = PLAYER_COLORS.get(name, DEFAULT_PLAYER_COLOR)
        ax.plot(x, values, color=color, linewidth=2, zorder=2, solid_capstyle='round')

    ax.set_xlim(x[0], x[-1] * 1.16 if x[-1] else 1)
    y_min = min(min(v) for v in progression.values()) if progression else 0
    y_max = max(max(v) for v in progression.values()) if progression else 1
    y_range = max(y_max - y_min, 1)
    min_gap = y_range * 0.045

    label_ys = [values[-1] for _, values in highlighted]
    for i in range(1, len(label_ys)):
        if label_ys[i - 1] - label_ys[i] < min_gap:
            label_ys[i] = label_ys[i - 1] - min_gap

    for (name, values), label_y in zip(highlighted, label_ys):
        color = PLAYER_COLORS.get(name, DEFAULT_PLAYER_COLOR)
        ax.text(x[-1] + x[-1] * 0.02 + 0.3, label_y, name, color=color,
                 fontsize=10, va='center', ha='left',
                 fontfamily=CUSTOM_FONT_NAME)

    ax.set_title('Andamento Siso — {}'.format(season_name), color=SISO_INK_PRIMARY,
                  fontsize=14, loc='left', pad=14,
                  fontfamily=CUSTOM_FONT_NAME)
    ax.set_xlabel('Frigo giocate in stagione', color=SISO_INK_MUTED, fontsize=9,
                  fontfamily=CUSTOM_FONT_NAME)
    ax.set_ylabel('Punteggio (5-1)', color=SISO_INK_MUTED, fontsize=9,
                  fontfamily=CUSTOM_FONT_NAME)

    ax.grid(axis='y', color=SISO_GRID, linewidth=0.8, zorder=0)
    ax.grid(axis='x', visible=False)
    for spine in ('top', 'right', 'left'):
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color(SISO_BASELINE)
    ax.spines['bottom'].set_linewidth(0.8)

    ax.tick_params(axis='both', colors=SISO_INK_MUTED, labelsize=8, length=0)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily(CUSTOM_FONT_NAME)
    ax.axhline(0, color=SISO_BASELINE, linewidth=0.8, zorder=0)

    fig.tight_layout()
    plt.savefig(path, facecolor=SISO_SURFACE)
    plt.close(fig)


def ladderTable(p, r, rd, path):
    rating = [int(rt) for rt in r]
    rds = [int(rt) for rt in rd]
    df = pl.DataFrame({
        'Frigante': p,
        'Rating': rating,
        'RD': rds
    })

    df = df.sort('Rating', descending=True)
    df = df.with_columns(pl.Series('Pos', range(1, len(df) + 1))).select(['Pos', 'Frigante', 'Rating', 'RD'])

    fig, ax = plt.subplots(figsize=(8, 4))

    ax.axis('off')
    tbl = ax.table(cellText=df.rows(), colLabels=df.columns, loc='center', cellLoc='center',
                    colWidths=[0.1] * len(df.columns))

    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1.2, 1.2)

    for cell in tbl.get_celld().values():
        cell.get_text().set_fontfamily(CUSTOM_FONT_NAME)

    plt.savefig(path, bbox_inches='tight')
    plt.close()