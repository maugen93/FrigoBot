import os

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy.interpolate import make_interp_spline

import polars as pl

FONT_PATH = os.path.join('resources', 'font.otf')
fm.fontManager.addfont(FONT_PATH)
CUSTOM_FONT_NAME = fm.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams['font.family'] = CUSTOM_FONT_NAME


def save_hist(x, y, path):
    x_np = np.array(x)
    y_np = np.array(y)

    # max_index=np.argmax(x_np)
    # x_np=np.delete(x_np,max_index)
    # y_np=np.delete(y_np,max_index)

    plt.bar(x_np, y_np, width=1, color='blue', alpha=0.7)

    x_s = np.linspace(x_np.min(), x_np.max(), 300)
    spl = make_interp_spline(x_np, y_np, k=2)
    y_s = spl(x_s)

    plt.plot(x_s, y_s, 'r-')
    plt.xlabel('Weeks')
    plt.ylabel('F')

    plt.savefig(path)
    plt.close()


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
SISO_INK_MUTED = '#898781'
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