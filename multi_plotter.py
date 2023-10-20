import os
import re
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

from scipy.signal import find_peaks
from scipy.signal import savgol_filter

import tkinter as tk
from tkinter import filedialog

from bisect import bisect_right

def evaluation_function(ax, max_indices, min_indices, pos, force, average_force = 0):
    # for Mt. Hood, this function calculates the slope between the abs min and abs max

    # find the index of the absolute min and max
    min_idx = np.argmin(force[min_indices])
    max_idx = np.argmax(force[max_indices])

    # find the position of the absolute min and max
    min_pos = pos[min_indices][min_idx]
    max_pos = pos[max_indices][max_idx]

    if (min_pos >= max_pos):
        min_idx = min_indices[0]
        min_pos = pos[min_indices][min_idx]

    # find the min and max values
    min_val = force[min_indices][min_idx]
    max_val = force[max_indices][max_idx]

    # calculate the slope value
    x = [min_pos, max_pos]
    y = [min_val, max_val]

    slope = (y[1] - y[0]) / (x[1] - x[0])

    # plot the slope
    ax.plot(x, y, 'r--', label='Max Slope: ' + str(round(slope, 2)) + ' N/m')


    ### As an addendum, the following code will calculate the slope between the first min and max,
    ### if the absolute min and max are not the first min and max
    min_idx2 = min_indices[0]
    max_idx2 = max_indices[0]

    # if the first max is before or the absolute max, graph it
    if (max_idx2 < max_indices[max_idx]) :
        min_pos2 = pos[min_idx2]
        max_pos2 = pos[max_idx2]

        min_val2 = force[min_idx2]
        max_val2 = force[max_idx2]

        x2 = [min_pos2, max_pos2]
        y2 = [min_val2, max_val2]

        slope2 = (y2[1] - y2[0]) / (x2[1] - x2[0])

        #plot the slope
        ax.plot(x2, y2, 'b--', label='First Peak Slope: ' + str(round(slope2, 2)) + ' N/m')
    
    if (average_force == 0) : # default. plot linear regression line
        # Our model is y = a * x, so things are quite simple, in this case...
        # x needs to be a column vector instead of a 1D vector for this, however.
        x = pos[:,np.newaxis]
        a, _, _, _ = np.linalg.lstsq(x, force, rcond=None)

        ax.plot(x, a*x, linestyle='dashed', color='teal', label='Linear Regression Slope: ' + str(round(a[0], 2)) + ' N/m')
    else :
        ax.axhline(average_force, linestyle='dashed', color='teal', label='Average Force: ' + str(round(average_force)) + ' N')

def plot_penetration(filename, ax):
    # read in data
    data = travelerRead(filename)

    # find the maximum extension, cut off data after that
    end_i = np.argmax(data['position_y'])
    y_pos_ = data['position_y'][0:end_i]
    
    # find the minimum extension, cut off data before that
    i_start = np.argmin(y_pos_)
    idx = find_first_nonnegative_index(data['force_y'][i_start:])
    i_start = max(i_start, idx+i_start)

    # print('end_i: ', end_i)
    # print('i_start: ', i_start)
    print('Range of i: [ ', i_start, ', ', end_i, ' ]')
    # print('idx: ', idx)

    print('len of pos_y: ', len(y_pos_))

    if (i_start >= end_i):
        print('Ranging error: i_start >= end_i...')
        print('   correcting i_start to 0... ')
        i_start = 0
    
    y_pos_ = y_pos_[i_start:] - y_pos_[i_start]

    # find the corresponding force range
    penetration_ = data['force_y'][i_start:end_i]
    # y_pos_ = data['position_y'][i_start:end_i] - data['position_y'][i_start]

    y_pos, penetration_force = trim_data(y_pos_, penetration_) 

    max_indices, min_indices, smooth_pos, smooth_force, average_force = minmax_finder(y_pos, penetration_force)

    ax.plot(y_pos, penetration_force, '-', label="Raw Force", linewidth=2)
    ax.plot(smooth_pos[min_indices], smooth_force[min_indices], "v", label="Local Minima", markersize=10, markerfacecolor='r')
    ax.plot(smooth_pos[max_indices], smooth_force[max_indices], "^", label="Local Maxima", markersize=10, markerfacecolor='g')

    evaluation_function(ax, max_indices, min_indices, smooth_pos, smooth_force)


    ax.set_xlabel('Vertical Depth (meters)', fontsize=18)
    ax.set_ylabel('Penetration Force (N)', fontsize=18)
    title = generate_title(filename)
    ax.set_title(title, fontsize=24)
    ax.legend()
    ax.tick_params(labelsize=16)

    # Assuming you have a folder path for saving the plots
    plot_save_path = filename.rstrip('.csv')

    save_path_png = plot_save_path + '.png'
    save_path_fig = plot_save_path + '.fig'
    
    # plt.savefig(save_path_png, dpi=300, bbox_inches='tight', transparent=True)
    # plt.savefig(save_path_fig, bbox_inches='tight')


def plot_shear(filename, ax):
    data = travelerRead(filename) 
    data['force_x'] = -1 * data['force_x']
    position_max = data['position_x'].max()
    position_min = data['position_x'].min()
    threshold_max = 0.98 * (position_max - position_min) + position_min
    i_start = np.argmin(data['position_x'])
    
    for i in range(i_start, len(data['time'])):
        if data['position_x'][i] > threshold_max:
            break
    i_end = i

    idx = find_first_nonnegative_index(data['force_x'][i_start:i_end])

    i_start = max(i_start, (idx+i_start))
    
    shear_force_ = data['force_x'][i_start:i_end]
    x_pos_ = data['position_x'][i_start:i_end] - data['position_x'][i_start]
    

    x_pos, shear_force = trim_data(x_pos_, shear_force_)
    
    # find the local minima and maxima of the force curve
    TF_max, TF_min, smooth_pos, smooth_force, average_force = minmax_finder(x_pos, shear_force)

    ax.plot(x_pos, shear_force, '-', label="Raw Force", linewidth=2)
    ax.plot(smooth_pos[TF_min], smooth_force[TF_min], "v", label="Local Minima", markersize=10, markerfacecolor='r')
    ax.plot(smooth_pos[TF_max], smooth_force[TF_max], "^", label="Local Maxima", markersize=10, markerfacecolor='g')

    evaluation_function(ax, TF_max, TF_min, smooth_pos, smooth_force, average_force)

    ax.set_xlabel('Horizontal Position (meters)', fontsize=18)
    ax.set_ylabel('Shear Force (N)', fontsize=18)
    title = generate_title(filename)
    ax.set_title(title, fontsize=24)
    ax.legend()
    ax.tick_params(labelsize=16)

    # Assuming you have a folder path for saving the plots
    plot_save_path = filename.rstrip('.csv')

    save_path_png = plot_save_path + '.png'
    save_path_fig = plot_save_path + '.fig'
    
    # plt.savefig(save_path_png, dpi=300, bbox_inches='tight', transparent=True)
    # plt.savefig(save_path_fig, bbox_inches='tight')

def minmax_finder(position, force):
    # Sort the data based on x_pos values
    sorted_indices = np.argsort(position)
    position = position[sorted_indices]
    force = force[sorted_indices]

    # Remove duplicate x_pos values and correspondingly update the force values
    unique_indices = np.unique(position, return_index=True)[1]
    unique_pos = position[unique_indices]
    unique_force = force[unique_indices]

    # Smooth the force data using Savitzky-Golay filter
    smoothed_force = savgol_filter(unique_force, window_length=11, polyorder=3)

    # Calculate the average force for prominence threshold calculation
    average_force = np.trapz(unique_force, unique_pos) / unique_pos[-1]
    print('Average Force: ', average_force)
    prominence_threshold = np.abs(0.25 * average_force)

    # Find local maxima and minima x values using the prominence threshold
    pos_max, _ = find_peaks(smoothed_force, prominence=prominence_threshold)
    pos_min, _ = find_peaks(-1.0 * smoothed_force, prominence=prominence_threshold)

    # Insert a zero at the beginning of pos_min array
    pos_min = np.insert(pos_min, 0, 0)

    if (len(pos_max) == 0):
        pos_max = np.insert(pos_max, 0, len(unique_pos) - 1)

    # add the maximum force value if not present in the array
    max_force_idx = np.argmax(unique_force)
    if (max_force_idx not in pos_max):
        pos_max = np.insert(pos_max, len(pos_max), max_force_idx)

    max_indicesima = unique_force[pos_max]
    min_indicesima = unique_force[pos_min]

    # Create dictionaries for minima and maxima
    minima = dict(zip(pos_min, min_indicesima))
    maxima = dict(zip(pos_max, max_indicesima))

    return pos_max, pos_min, unique_pos, smoothed_force, average_force

def find_first_nonnegative_index(arr):
        index = bisect_right(arr, 0.2)
        if (index >= len(arr)):
            index = 0
        return index

# Function to remove any NaN or infinite values
def trim_data(x, y):
    mask = (~pd.isna(x)) & (~pd.isna(y))
    return x[mask], y[mask]

def travelerRead(filepath, mode = 0):
    print('Reading File...')
    with open(filepath, 'r') as file:
        # Read the header and variable names
        varNames = file.readline().strip().split(',')
        varValues = file.readline().strip().split(',')

    # Extract groundHeight value and store it in data.groundHeight
    groundHeight = float(varValues[-2]) / 100.0

    # Extract extrusionAngle value and store it
    extrusionAngle = float(varValues[2]) 

    print('Ground Height: ', groundHeight)

    # Read the rest of the data using Pandas
    data = pd.read_csv(filepath, skiprows=2)

    # Convert column names to lowercase for consistency
    data.columns = [col.lower() for col in data.columns]

    # Correct sign of position_y for plotting
    data['toe_position_y'] = (-data['toe_position_y']) - groundHeight

    data['toeforce_y'] = -data['toeforce_y']
    
    # Extract required columns and assign them to the data dictionary
    data_dict = {
        'time': data['time'].values,
        'position_x': data['toe_position_x'].values,
        'position_y': data['toe_position_y'].values,
        'force_x': data['toeforce_x'].values,
        'force_y': data['toeforce_y'].values,
        'groundHeight': groundHeight,
        'extrusionAngle': extrusionAngle
    }

    return data_dict

def generate_title(filepath):
    # filenames are in form 'WS23_L3_T1_S_12_perp2_Sat_Mar_11....'
    filename = filepath.split('/')[-1]
    filename_args = filename.split('_')

    protocol = filename_args[3]
    protocol_string = ''
    if (protocol == 'S'):
        protocol_string = 'Shear'
    elif (protocol == 'P'):
        protocol_string = 'Penetration'

    location = filename_args[1]
    location = location.replace('L', 'Location ')

    transect = filename_args[2]
    transect = transect.replace('T', 'Transect ')

    flag = filename_args[4]
    flag = 'Flag ' + flag

    title = protocol_string + ': ' + location + ', ' + transect + ', ' + flag

    return title

def select_directory():
    directory = filedialog.askdirectory()
    if directory:
        print(f"Selected Directory: {directory}")
        # Add your file processing logic here, e.g., open the file and read its contents
    return directory

def traverse_csv_files(directory):
    paths = []
    for root, dirs, files in os.walk(directory):
        for file in sorted(files):
            # Check if the file has a .csv extension
            if file.endswith(".csv"):
                if "_T_" not in file:
                    # Print or process the CSV file
                    file_path = os.path.join(root, file)
                    print(file_path)
                    paths.append(file_path)
    print("Found {} CSV files in directory {}".format(len(paths), directory))
    print('Preparing to process files...')
    return paths

def process_file(filepath, ax):
    filename = filepath.split('/')[-1]

    print('Processing ', filename)

    filename_args = filename.split('_')

    protocol = filename_args[3]
    filename_args = filename.split('_')
    protocol = filename_args[3]
    print('Protocol: ', protocol)

    protocol = re.sub(r'\d+', '', protocol)
    
    plt.show(block=False)

    if (protocol == 'P' or protocol == 'AP' or protocol == 'RP'):
        plot_penetration(filepath, ax)
    elif (protocol == 'S'):
        plot_shear(filepath, ax)
    else:
        protocol = input('Type \'P\' for Penetration, \'S\' for Shear: ')
        if (protocol == 'P' or protocol == 'p'):
            plot_penetration(filepath, ax)
        elif (protocol == 'S' or protocol == 's'):
            plot_shear(filepath, ax)
    
    print()
    # save_plot(filepath)
    # plt.show()

def process_files(paths):
    # create a PdfPages object
    save_name = input('Enter a name for the PDF output file: ')
    if not save_name.endswith(".pdf"):
        save_name = save_name + ".pdf"
    pdf = PdfPages(save_name)

    # define here the dimension of your figure
    fig, ax = plt.subplots(figsize=(12, 6))

    for path in paths:
        process_file(path, ax)
        # save the current figure
        pdf.savefig(fig)

        # destroy the current figure
        # saves memory as opposed to create a new figure
        ax.clear()

    # remember to close the object to ensure writing multiple plots
    print('Processing complete. Saving PDF...')
    pdf.close()


def save_plot(filepath):
    filename = filepath.split('/')[-1]
    parent_path = filepath.rstrip(filename).rstrip('/data')
    figure_path = parent_path + '/figures/'
    print(figure_path)
    plot_save_name = filename.rstrip('.csv') + '.png'
    # directory_path = '/home/qianlab/lassie-traveler/experiment_records/MH23_Data/'
    save_path_png = figure_path + plot_save_name
    print(save_path_png)
    
    plt.savefig(save_path_png, bbox_inches='tight', transparent=False, dpi=300)

if __name__ == "__main__":
    # Create the ArgumentParser object
    parser = argparse.ArgumentParser(description='Force vs Displacement plotting script.\n Written by John Bush for RoboLAND Lab at USC.')

    # Add the --help option
    # parser.add_argument('--help', action='help', help='Show this help message and exit.')


    root = tk.Tk()
    root.withdraw()  # Hide the main window

    dir = select_directory()
    root.destroy()

    paths = traverse_csv_files(dir)

    process_files(paths)



    



    