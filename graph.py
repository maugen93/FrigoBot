import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import make_interp_spline

import polars as pl
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


def ladderTable(p,r,rd, path):
    rating=[int(rt)for rt in r]
    rds=[int(rt)for rt in rd]
    df=pl.DataFrame({
        'Frigante':p,
        'Rating':rating,
        'RD':rds
    })

    df=df.sort('Rating', descending=True)
    df=df.with_columns(pl.Series('Pos',range(1,len(df)+1))).select(['Pos','Frigante','Rating','RD'])

    fig,ax=plt.subplots(figsize=(8,4))

    ax.axis('off')
    tbl=ax.table(cellText=df.rows(),colLabels=df.columns,loc='center',cellLoc='center',colWidths=[0.1]*len(df.columns))

    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1.2,1.2)

    plt.savefig(path,bbox_inches='tight')
    plt.close()