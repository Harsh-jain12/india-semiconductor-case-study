# Regenerates every chart used in the final report at its placed print size.
# No chart titles and no in-image source lines: the exhibit title and source line in the report do that job.
# Figure width = placed width (14 cm, two-panel 15.5 cm); all text 9-10 pt; one navy-based, colourblind-safe palette.
import math
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

# Paths are relative to the repo root, so the script runs from any working directory.
ROOT = Path(__file__).resolve().parent.parent
P5 = P6 = P7 = f'{ROOT / "data"}/'
OUT = f'{ROOT / "charts"}/'
Path(OUT).mkdir(exist_ok=True)
# The report's charts use Carlito (SIL Open Font License). It is bundled so they render the same on any machine.
font_manager.fontManager.addfont(ROOT / 'scripts' / 'fonts' / 'Carlito-Regular.ttf')
CM = 1 / 2.54
# Palette: navy (heading accent), mid blue, light blue, orange (CVD-safe contrast to blue), greys
NAVY, BLUE, LIGHT, ORANGE, GREY, LGREY, DARK = '#1F3864', '#4F81BD', '#B4C9E4', '#D9822B', '#7F7F7F', '#D9D9D9', '#404040'
plt.rcParams.update({'font.family': 'Carlito', 'font.size': 9.5, 'axes.labelsize': 9.5, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
                     'legend.fontsize': 9, 'axes.edgecolor': GREY, 'axes.linewidth': 0.6, 'xtick.color': DARK, 'ytick.color': DARK,
                     'axes.labelcolor': DARK, 'axes.spines.top': False, 'axes.spines.right': False, 'savefig.dpi': 300})
W = 14 * CM
def save(fig, name):
    fig.savefig(OUT + name, dpi=300, facecolor='white'); plt.close(fig); print('saved', name, fig.get_size_inches() / CM)

# ---------- Exhibit 2: trade ----------
tr = pd.read_csv(P7 + 'tradestat_with_ex_solar.csv')
ex = tr['hs8541_imports_usd_m'] * (1 - tr['solar_share_of_8541']) + tr['hs8542_imports_usd_m']
fig, ax = plt.subplots(figsize=(W, 5.9 * CM))
x = np.arange(len(tr))
ax.bar(x, tr['hs8542_imports_usd_m'] / 1000, color=NAVY, width=0.62, label='HS 8542 – integrated circuits')
ax.bar(x, tr['hs8541_imports_usd_m'] / 1000, bottom=tr['hs8542_imports_usd_m'] / 1000, width=0.62, color=LIGHT, label='HS 8541 – discretes and solar')
m = ex.notna()
ax.plot(x[m], ex[m] / 1000, 'D', color=ORANGE, ms=7, label='Chips ex-solar (FY24–25)', zorder=3)
ax.axhline(52, color=GREY, ls='--', lw=0.9)
ax.text(-0.35, 53.2, 'IESA chip consumption FY25: US$52B', fontsize=9, color=DARK)
ax.set_xticks(x); ax.set_xticklabels(tr['fiscal_year']); ax.set_ylabel('US$ billion'); ax.set_ylim(0, 60)
ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(0, 0.86))
fig.tight_layout(pad=0.4); save(fig, 'ex02_trade.png')

# ---------- Exhibit 8: Micron cycle ----------
q = pd.read_csv(P5 + 'micron_quarterly.csv')
q['gm'] = 100 * q['gross_margin_usd_m'] / q['revenue_usd_m']
fig, ax1 = plt.subplots(figsize=(W, 5.9 * CM))
x = np.arange(len(q))
ax1.bar(x, q['revenue_usd_m'] / 1000, color=LIGHT, width=0.8, label='Revenue (US$B, left)')
ax1.set_ylabel('Revenue (US$B)')
ax2 = ax1.twinx(); ax2.spines['right'].set_visible(True)
ax2.plot(x, q['gm'], color=NAVY, lw=1.8, label='Gross margin (%, right)')
ax2.axhline(0, color=GREY, lw=0.7); ax2.set_ylabel('Gross margin (%)')
i_min, i_max = q['gm'].idxmin(), q['gm'].idxmax()
for i, va, dx, dy, ha in [(i_min, 'center', 7, 0, 'left'), (i_max, 'bottom', -4, 3, 'right')]:
    ax2.annotate(f"{q.loc[i,'gm']:.0f}%", (i, q.loc[i, 'gm']), xytext=(dx, dy), textcoords='offset points', ha=ha, va=va, fontsize=9, color=NAVY)
first = q.index[q['fiscal_quarter'] == 1]
ax1.set_xticks(first); ax1.set_xticklabels(['FY' + str(y)[2:] for y in q.loc[first, 'fiscal_year']])
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, frameon=False, loc='upper left')
ax2.set_ylim(-45, 100)
fig.tight_layout(pad=0.4); save(fig, 'ex08_micron_cycle.png')

# ---------- Exhibit 10: Sanand Monte Carlo (Phase 7A method) ----------
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
def tri_inv(u, a, c, b):
    f = (c - a) / (b - a)
    return np.where(u < f, a + np.sqrt(u * (b - a) * (c - a)), b - np.sqrt((1 - u) * (b - a) * (b - c)))
def corr_uniforms(rho, n, rng):
    z1 = rng.standard_normal(n); e = rng.standard_normal(n)
    return Phi(z1), Phi(rho * z1 + math.sqrt(max(1 - rho ** 2, 0)) * e)
si = pd.read_csv(P7 + 'sanand_inputs.csv').set_index('input')
tr_ = lambda k, u: tri_inv(u, *si.loc[k, ['low', 'mode', 'high']].astype(float))
CAP = float(si.loc['capacity_units', 'mode'])
vpu = lambda d, s, a, b, c: d * a + (1 - d - s) * b + s * c
vals = {}
for rho in [0.0, 0.7]:
    rng = np.random.default_rng(42); uu, up = corr_uniforms(rho, 10_000, rng); o = rng.random((3, 10_000))
    vals[rho] = tr_('utilisation_2030', uu) * CAP * vpu(tr_('dram_share_units', o[0]), tr_('ssd_share_units', o[1]),
        tr_('dram_value_per_chip_usd', up), tr_('nand_value_per_package_usd', up), tr_('ssd_value_per_unit_usd', up)) / 1000
    print('Sanand rho', rho, np.percentile(vals[rho], [10, 50, 90]).round(2))
fig, ax = plt.subplots(figsize=(W, 5.9 * CM))
bins = np.arange(0, 14.01, 0.25)
ax.hist(vals[0.0], bins=bins, color=LIGHT, label='ρ = 0: independent')
ax.hist(vals[0.7], bins=bins, histtype='step', lw=1.8, color=NAVY, label='ρ = 0.7: move together')
for rho, col, yy in [(0.0, GREY, 690), (0.7, NAVY, 750)]:
    p10, p50, p90 = np.percentile(vals[rho], [10, 50, 90])
    ax.plot([p10, p90], [yy, yy], color=col, lw=2); ax.plot(p50, yy, 'o', color=col, ms=5)
    ax.text(p90 + 0.2, yy, f'P10–P90 US${p10:.1f}–{p90:.1f}B', va='center', fontsize=9, color=col)
ax.axvline(4.65, color=ORANGE, ls='--', lw=1.2)
ax.text(4.5, 630, 'Hand-built base US$4.7B', ha='right', fontsize=9, color=ORANGE)
ax.set_xlabel('Sanand throughput value, 2030 (US$B, normal-cycle prices)'); ax.set_ylabel('Runs (of 10,000)')
ax.set_xlim(0, 14); ax.set_ylim(0, 800)
ax.legend(frameon=False, loc='center right', bbox_to_anchor=(1, 0.42), title='Utilisation vs price', title_fontsize=9)
fig.tight_layout(pad=0.4); save(fig, 'ex10_sanand_mc.png')

# ---------- Exhibit 11: peers utilisation vs gross margin ----------
peers = pd.read_csv(P6 + 'foundry_peers.csv')
fit = peers.dropna(subset=['utilisation_pct', 'gross_margin_pct'])
b, a = np.polyfit(fit['utilisation_pct'], fit['gross_margin_pct'], 1)
r = np.corrcoef(fit['utilisation_pct'], fit['gross_margin_pct'])[0, 1]
F_FIXED = 0.639
be = fit[fit['year'] == 2025].copy(); g0 = be['gross_margin_pct'] / 100
be['be'] = be['utilisation_pct'] * F_FIXED * (1 - g0) / (1 - (1 - F_FIXED) * (1 - g0))
BE_MED = round(be['be'].median())
pq = pd.read_csv(P6 + 'psmc_quarterly.csv'); pf = pq[pq['quarter'].isin(['4Q24', '3Q25', '4Q25'])]
pb, pa = np.polyfit(pf['utilisation_pct'], pf['gross_margin_pct'], 1); BE_NEW = -pa / pb
print('peers r', round(r, 2), 'median BE', BE_MED, 'PSMC BE', round(BE_NEW))
style = {'UMC': (NAVY, 'o'), 'VIS': (BLUE, 's'), 'SMIC': (GREY, '^'), 'HuaHong': (DARK, 'v'), 'PSMC': (ORANGE, 'D')}
fig, ax = plt.subplots(figsize=(W, 6.8 * CM))
for c, g in fit.groupby('company'):
    col, mk = style.get(c, (GREY, 'o'))
    ax.scatter(g['utilisation_pct'], g['gross_margin_pct'], s=34, color=col, marker=mk, label=c.replace('HuaHong', 'Hua Hong'), zorder=3)
    for _, row in g.iterrows():
        off = (-15, -11) if (c == 'VIS' and row['year'] == 2025) else (4, 3)
        ax.annotate("'" + str(int(row['year']))[2:], (row['utilisation_pct'], row['gross_margin_pct']), textcoords='offset points', xytext=off, fontsize=9, color=DARK)
xs = np.linspace(55, 110, 50)
ax.plot(xs, a + b * xs, color=GREY, lw=1, ls=':', label=f'Pooled fit (r = {r:.2f})')
ax.scatter(pf['utilisation_pct'], pf['gross_margin_pct'], marker='D', s=30, facecolor='white', edgecolor=ORANGE, lw=1.4, zorder=4, label='PSMC quarters')
xs2 = np.linspace(65, 90, 20); ax.plot(xs2, pa + pb * xs2, color=ORANGE, lw=1.4)
ax.axhline(0, color=GREY, lw=0.7)
ax.axvline(BE_NEW, color=ORANGE, ls='--', lw=0.9); ax.text(BE_NEW + 1, -13.5, f'PSMC break-even ≈ {BE_NEW:.0f}%', fontsize=9, color=ORANGE, ha='left')
ax.axvline(BE_MED, color=NAVY, ls='--', lw=0.9); ax.text(BE_MED + 0.8, 46, f'Peer median ≈ {BE_MED:.0f}%', fontsize=9, color=NAVY)
ax.set_xlim(55, 110); ax.set_ylim(-16, 52)
ax.set_xlabel('Capacity utilisation (%)'); ax.set_ylabel('Gross margin (%)')
ax.legend(frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=4, columnspacing=1.2, handletextpad=0.4)
fig.tight_layout(pad=0.4); save(fig, 'ex11_peers.png')

# ---------- Exhibit 12: Dholera ramp ----------
mc = pd.read_csv(P6 + 'dholera_montecarlo_summary.csv'); mc['p'] = mc['scenario'].str.replace('MonteCarlo_', '')
YEARS = sorted(mc['year'].unique())
w = mc.pivot(index='year', columns='p', values='wafers_out_k'); v = mc.pivot(index='year', columns='p', values='illustrative_value_usd_m')
full_val = 570 * 2208 / 1000
fig, axes = plt.subplots(1, 2, figsize=(15.5 * CM, 5.7 * CM))
for ax, d, lab, cap, ctext in [(axes[0], w, "Wafers out ('000 a year)", 600, 'Full capacity'), (axes[1], v, 'Illustrative output value (US$M)', full_val, 'Full capacity, median price')]:
    ax.fill_between(d.index, d['P10'], d['P90'], color=LIGHT, label='P10–P90')
    ax.plot(d.index, d['P50'], color=NAVY, lw=1.8, marker='o', ms=4, label='P50')
    ax.axhline(cap, color=GREY, ls='--', lw=0.9); ax.text(2028, cap * 0.92, ctext, fontsize=9, color=DARK, va='top')
    ax.set_ylabel(lab); ax.set_xticks(YEARS); ax.set_ylim(0, cap * 1.08)
axes[0].legend(frameon=False, loc='center left', bbox_to_anchor=(0, 0.55))
fig.tight_layout(pad=0.4, w_pad=1.5); save(fig, 'ex12_dholera_ramp.png')

# ---------- Exhibit 13: India 2030 local supply ----------
ind = pd.read_csv(P7 + 'india_2030_local_supply.csv')
fig, ax = plt.subplots(figsize=(W, 5.9 * CM))
xs = np.arange(3); wd = 0.26
for k, (col, pc, lab, colr) in enumerate([('a_made_or_packaged_usd_b', 'a_%', '(a) Made or packaged in India', NAVY),
                                          ('b_supplied_to_india_usd_b', 'b_%', '(b) Supplied to Indian buyers', ORANGE),
                                          ('c_value_added_usd_b', 'c_%', '(c) Value added in India', BLUE)]):
    ax.bar(xs + (k - 1) * wd, ind[col], wd, color=colr, label=lab)
    for x_, v_, p_ in zip(xs + (k - 1) * wd, ind[col], ind[pc]):
        ax.text(x_, v_ + 0.2, f'{p_:.1f}%', ha='center', fontsize=9, color=DARK)
ax.set_xticks(xs); ax.set_xticklabels([f'{s}\n(market US${m}B)' for s, m in zip(ind['scenario'], ind['market_usd_b'])])
ax.set_ylabel('US$ billion, 2030 (label = % of market)'); ax.set_ylim(0, 14)
ax.legend(frameon=False, loc='upper left')
fig.tight_layout(pad=0.4); save(fig, 'ex13_local_supply.png')

# ---------- Exhibit 15: reference fab break-even ----------
fb = pd.read_csv(P7 + 'fab_reference_cases.csv')
fig, ax = plt.subplots(figsize=(W, 6.8 * CM))
xs = np.arange(len(fb)); wd = 0.26
for k, (col, lab, colr) in enumerate([('GM_breakeven_loading_2030_%', '2030 (part-tooled)', ORANGE),
                                     ('GM_breakeven_loading_2033_%', '2033 (fully tooled)', NAVY),
                                     ('GM_breakeven_loading_2036_%', '2036 (older tools depreciated)', BLUE)]):
    ax.bar(xs + (k - 1) * wd, fb[col].clip(upper=200), wd, color=colr, label=lab, zorder=2)
    for x_, v_ in zip(xs + (k - 1) * wd, fb[col]):
        ax.text(x_, min(v_, 200) + 3, f'{v_:.0f}', ha='center', fontsize=9, color=DARK)
ax.axhspan(46, 88, color=LGREY, alpha=0.7, zorder=1, label='Peer break-even range 46–88%')
ax.axhline(100, color=DARK, lw=0.8, ls=':'); ax.text(4.45, 103, 'Full loading', fontsize=9, color=DARK, ha='right')
ax.set_xticks(xs); ax.set_xticklabels(['No support', 'Central\n50%', 'Semicon 2.0\n+ Gujarat\n56% of total', 'Semicon 2.0\n+ Gujarat\neligible capex', 'Semicon 1.0\n+ Gujarat\n~65% PV'])
ax.set_ylabel('Break-even loading of\ninstalled capacity (%)'); ax.set_ylim(0, 200)
ax.legend(frameon=False, loc='upper right', ncol=2, columnspacing=1.0)
fig.tight_layout(pad=0.4); save(fig, 'ex15_fab_breakeven.png')
