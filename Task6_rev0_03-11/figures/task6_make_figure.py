import pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import os; F=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","results")+"/"
NAMES=[("ML_Blend_v1.3","Blend v1.3 (final model)"),("ML_Chronos_v1.3","Chronos-Bolt v1.3"),("ML_ChronosGBM_v1.3","ChronosGBM v1.3"),
       ("ML_GBM_v1.3","Gradient boosting v1.3"),("ML_RandomForest","Random Forest"),("ML_Linear","Linear Regression"),
       ("B3_persistence","Baseline C (persistence)"),("B2_weekday_hour_median","Baseline B (weekday × hour)"),
       ("B1_last_week","Baseline A (last week)")]
HZ=[("+1h","+1 h"),("+6h","+6 h"),("day-ahead","Day-ahead")]
m=pd.read_csv(F+"task6_test_16circuits/metrics_with_CI.csv"); m=m[m.scope=="all circuits"].set_index(["model","horizon"])
INK,MUTED,GRID="#0b0b0b","#52514e","#e4e3df"; ML,FINAL,BASE="#2a78d6","#eb6834","#9a9994"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9})
fig,axes=plt.subplots(1,3,figsize=(10,4.2),sharey=True)
ys=list(range(len(NAMES)))[::-1]
for ax,(h,hl) in zip(axes,HZ):
    best=min(m.loc[(k,h),"MAE_Wh"] for k,_ in NAMES)
    for y,(k,lab) in zip(ys,NAMES):
        r=m.loc[(k,h)]; c=FINAL if k=="ML_Blend_v1.3" else (BASE if k.startswith("B") else ML)
        ax.plot([r.MAE_lo,r.MAE_hi],[y,y],color=c,lw=2,solid_capstyle="round",alpha=.55)
        ax.plot(r.MAE_Wh,y,"o",ms=7,color=c,mec="white",mew=1.5,zorder=3)
        ax.text(r.MAE_hi+1.2,y,f"{r.MAE_Wh:.1f}",va="center",fontsize=8,color=INK if k=="ML_Blend_v1.3" else MUTED,
                fontweight="bold" if k=="ML_Blend_v1.3" else "normal")
    ax.set_title(hl,fontsize=10,color=INK,loc="left",fontweight="bold")
    ax.set_xlim(0,85); ax.grid(axis="x",color=GRID,lw=.8); ax.set_axisbelow(True)
    for s in ["top","right","left"]: ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID); ax.tick_params(colors=MUTED,length=0)
    ax.set_xlabel("Test MAE (Wh), dot = value, line = 95% CI",color=MUTED,fontsize=8)
axes[0].set_yticks(ys,[lab for _,lab in NAMES]); axes[0].tick_params(axis="y",colors=INK)
fig.suptitle("Test week (29 Sep – 5 Oct 2025), all 16 circuits, same 1,911 hours per horizon for every model",
             x=0.01,ha="left",fontsize=10,color=INK)
from matplotlib.lines import Line2D
fig.legend(handles=[Line2D([],[],marker="o",ls="",color=FINAL,label="Final model"),Line2D([],[],marker="o",ls="",color=ML,label="Other ML models"),
                    Line2D([],[],marker="o",ls="",color=BASE,label="Baselines")],loc="lower center",ncol=3,frameon=False,fontsize=8,bbox_to_anchor=(0.6,-0.01))
fig.tight_layout(rect=(0,0.05,1,0.95)); fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)),"task6_test_mae_16circuits.png"),dpi=200,facecolor="white")
