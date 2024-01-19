import os
import re
import argparse
import math
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

from scipy.signal import find_peaks
from scipy.signal import savgol_filter

''' Data to plot:
location	EPS%	Stiffness(N/mm)	Avg Deformation (cm)
2	0.023801167	4.113256987	0.718428407
3	0.01018739	3.259432542	0.501393974
'''

fig, ax = plt.subplots(figsize=(12,6))

x = [0.718428407, 0.501393974]
y = [0.023801167, 0.01018739]

L2Eps = [
0.000606995,
0.019041251,
# 0.000606995, # no deformation metric
0.010791226,
0.02120585,
0.057345991,
0.045293973,
0.035517056
]

L3Eps = [
0.001612643,
0.005354328,
0.005093588,
# 0.005782035, # no deformation metric
0.007233015,
0.008439299,
0.006661314,
0.01437146,
0.007928869,
# 0.004349151, # no deformation metric
0.012071713,
0.013207455,
0.01640326,
# 0.044089796, # no deformation metric
# 0.014606092, # no deformation metric
0.010386595,
0.009474974,
0.008935176,
0.003873516,
0.003873516
]


L2Deformation = [
0.012501195,
0.002987668,
0.015273318,
# 0.000628322,
0.006733432,
0.001572236,
0.010593817
]  

L3Deformation = [
0.005764261,
0.003282443,
0.015399441,
0.000737995,
0.002072752,
0.006046265,
0.002163231,
0.000514358,
0.001432002,
0.005713254,
0.009269431,
0.004372075,
0.00551717,
0.001665443,
0.011258975
]

L2Deformation = [x * 100 for x in L2Deformation]
L3Deformation = [x * 100 for x in L3Deformation]

# calculate average EPS and std error
L2EPS_avg = np.mean(L2Eps)
L2EPS_std = np.std(L2Eps)

L3EPS_avg = np.mean(L3Eps)
L3EPS_std = np.std(L3Eps)

L2Deformation_avg = np.mean(L2Deformation)
L2Deformation_std = np.std(L2Deformation)

L3Deformation_avg = np.mean(L3Deformation)
L3Deformation_std = np.std(L3Deformation)

# calculate confidence interval
L2EPS_ci = 1.96 * L2EPS_std / math.sqrt(len(L2Eps))
L3EPS_ci = 1.96 * L3EPS_std / math.sqrt(len(L3Eps))
L2Deformation_ci = 1.96 * L2Deformation_std / math.sqrt(len(L2Deformation))
L3Deformation_ci = 1.96 * L3Deformation_std / math.sqrt(len(L3Deformation))

x = [L2Deformation_avg, L3Deformation_avg]
y = [L2EPS_avg, L3EPS_avg]

x_err = [L2Deformation_std, L3Deformation_std]
y_err = [L2EPS_std, L3EPS_std]

labels = ['Parabolic Interdune Crusts', 'Barchan Interdune Crusts']

ax.scatter(L2Deformation_avg, L2EPS_avg, marker='o', s=100, label=labels[0])
ax.scatter(L3Deformation_avg, L3EPS_avg, marker='o', s=100, label=labels[1])

# # you can use color ="r" for red or skip to default as blue
# ax.errorbar(L2Deformation_avg, L2EPS_avg, yerr=L2EPS_std, xerr=L2Deformation_std)
# ax.errorbar(L3Deformation_avg, L3EPS_avg, yerr=L3EPS_std, xerr=L3Deformation_std)

# you can use color ="r" for red or skip to default as blue
ax.errorbar(L2Deformation_avg, L2EPS_avg, yerr=L2EPS_ci, xerr=L2Deformation_ci)
ax.errorbar(L3Deformation_avg, L3EPS_avg, yerr=L3EPS_ci, xerr=L3Deformation_ci)


ax.set_xlabel('Average Deformation Before Failure (cm)', fontsize=22)
ax.set_ylabel('Average EPS weight %', fontsize=22)
ax.legend()
ax.tick_params(labelsize=20)

# save the figure
fig.tight_layout()

eps_save_name = 'paper_fig_test.eps'
# get the current working directory
cwd = os.getcwd()
fig.savefig(os.path.join(cwd, eps_save_name), format='eps', bbox_inches='tight',dpi=300)


