from force_analysis import *
from pick import pick
import csv
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib.colors as colorNorm
import plotly.express as px
from plotly.express.colors import sample_colorscale
import plotly.graph_objects as go



"""
    Class: FlexPlotter
    Description:
        This class gives the user the ability to select a
        base set of files (ideally of the same protocol), and
        then plot aggregate data from those files.

        The class processes all files from a chosen directory and then
        stores the following data for each file:
            - Brief ID string
            - Location
            - Transect
            - Flag Number
            - Force
            - Position
            - Time
            - Average Force
            - Average stiffness
            - Average stick-slip frequency

        The class then prompts the user if they want to plot continuous or aggregate
        data. 
        It then asks the user to select a variable for the x-axis and a variable for the y-axis.

        The options for the axes are:
            - Transect/Flag Number
            - Position
            - Time
            - Force
            - Average Force
            - Average stiffness
            - Average stick-slip frequency

        The class then plots the data and displays the plot to the user.
        The class then prompts the user if they want to:
            1. Save the plot
            2. Choose a different x-axis variable
            3. Choose a different y-axis variable

"""

class FlexPlotter(TravelerAnalysisBase):
    def __init__(self):
        super().__init__()
        
        # plt.ion()
        # self.fig, self.ax = plt.subplots(figsize=(12,6))
        self.fig = go.Figure()
        
        self.annot = None
        self.sc = None
        

        self.data_vector = []
        self.data_vector_2 = []
        self.aggregated_data = {}
        self.aggregated_data_2 = {}

        self.plot_mode = 0
        self.x_axis = ''
        self.y_axis = ''
        self.x_choice_idx = 0
        self.y_choice_idx = 0
        self.filenames = np.array([])
        
        self.feature_dict = {}
        self.highlight = 'None'
        self.intersection_IDs = []
        self.penetration_vs_shear = False
        
        self.continuous_options = ['Position', 'Time', 'Force']
        self.continuous_option_units = [' (meters)',
                                        ' (sec)',
                                        ' (N)']
        self.aggregate_options = ['Transect-Flag Number', 
                                  'Flag Number', 
                                  'Average Force', 
                                  'Average Stiffness', 
                                  'Average Stick-Slip Period', 
                                  'Average Yield']
        self.aggregate_option_units = ['',
                                       '',
                                       ' (N)',
                                       ' (N/m)',
                                       ' (m)',
                                       ' (N)']
        
        # units for penetration vs shear
        self.comparison_options = ['Average Force', 
                                  'Average Stiffness', 
                                  'Average Stick-Slip Period', 
                                  'Average Yield']
        self.comparison_option_units = [' (N)',
                                       ' (N/m)',
                                       ' (m)',
                                       ' (N)']

    def user_selection(self):
        self.filepath = self.select_directory()
        self.paths = self.traverse_csv_files()
        
        
    def process_file(self):
        print('\n\nProcessing file ', self.path_index, ' of ', len(self.paths), '...')
        self.curr_file_valid = True
        # Read data from path
        self.travelerRead()

        if (self.curr_file_valid):
            self.process_data()
        
        if (self.curr_file_valid):
            self.format_trial()

        
    def run(self):
        self.path_index = 0
        # process and store data from all trial data files
        for self.path in self.paths:
            self.process_file()
            self.path_index += 1
    
        self.aggregate_data()
        # self.output_data()

        # prompt the user for plot options
        mode, x_axis, y_axis = self.user_plot_options_prompt()

        while(True):
            # plot the data
            self.create_plot()
            
            self.menu_prompt()
 
    def calculate_metrics(self):
        max_indices = self.data_dict['max_indices']
        min_indices = self.data_dict['min_indices']
        unique_pos = self.data_dict['smoothed_pos']
        smoothed_force = self.data_dict['smoothed_force']
        
        # local maxima positions and values
        max_pos = unique_pos[max_indices]
        print('number of max pos: ', len(max_pos))
        max_force = smoothed_force[max_indices]

        # local minima positions and values
        min_pos = unique_pos[min_indices]
        min_force = smoothed_force[min_indices]

        slopes = []
        stickSlip = []
        average_yield = np.mean(max_force)

        for min_idx in range(len(min_pos)):
            # get the next maximum with a position greather than the current min,
            # but less than the next min.
            for max_idx in range(len(max_pos)):
                # if the position of the max is greater than the current min and less than the next min:
                # if (max_pos[max_idx] > min_pos[min_idx] and max_pos[max_idx] < min_pos[min_idx+1]):
                if (max_pos[max_idx] > min_pos[min_idx] and 
                    ((min_idx == len(min_pos) - 1) or (max_pos[max_idx] < min_pos[min_idx+1]))):
                    # calculate the tear length and the slope
                    tear = (max_pos[max_idx] - min_pos[min_idx])
                    curr_slope = (max_force[max_idx] - min_force[min_idx]) / tear

                    if (curr_slope > 25000): # this is a safeguard against outliers
                        print('Outlier Slope: ', curr_slope) 
                    else:
                        slopes.append(curr_slope)
                        stickSlip.append(tear)
                    break

        return slopes, stickSlip, average_yield
    
    def process_features(self, filename):
        # read the data from the file
        if (filename == ''):
            print('No file selected...')
            return None
        data = self.csvReader(filename)
        
        name = filename.split('/')[-1].strip('.csv')
        # add the filename to the list of aggregate options
        self.aggregate_options.append(name)
        self.aggregate_option_units.append('[unit]')
        
        self.feature_dict[name] = {} # creates new dictionary mapped to the feature file name

        # construct id column if not present
        if ('id' not in data.columns):
            id_col = []
            # check if there is a location, transect, and flag column
            if ('location' in data.columns and 'transect' in data.columns and 'flag' in data.columns):
                for index, row in data.iterrows():
                    id_col.append('L' + str(row['location']) + 'T' + str(row['transect']) + 'F' + str(row['flag']))
                data['id'] = id_col
            else:
                print('Error reading file! Malformatted Feature CSV File: ', filename)
                return None
            
        # extract a dictionary of ID:data pairs
        raw_dict = {}
        
        col = ''
        if ('tags' in data.columns):
            col = 'tags'
        elif ('data' in data.columns):
            col = 'data'

# ! THIS SOLUTION DOES NOT ACCOUNT FOR MULTIPLE DATA ENTRIES PER ID
        for index, row in data.iterrows():
            raw_dict[row['id']] = row[col]

        # output a vector matched to the order of the aggregated data
        self.feature_dict[name] = self.match_data(self.aggregated_data['trial_IDs'], raw_dict)
        

        # # process tags column if present
        # if ('tags' in data.columns):
        #     # ID is in form 'L#T#F#'
        #     # construct a tag dictionary, mapping tags to a list of IDs
        #     for index, row in data.iterrows():
        #         tag_list = row['tags'].replace(" ", '').split(',') # remove trailing quotes, spaces and split by comma
        #         for tag in tag_list:
        #             if (tag not in self.feature_dict[name]):
        #                 self.feature_dict[name][tag] = []
        #             self.feature_dict[name][tag].append(row['id'])
            
        #     print(self.feature_dict.keys())
        
        # # process the feature file as numeric data associated with IDs
        # if ('data' in data.columns):
        #     # make a dictionary that maps ids to data entries
        #     for index, row in data.iterrows():
        #         data_elements = float(row['data'].replace(" ", '').split(',')) # remove trailing quotes, spaces and split by comma and then cast to float
        #         id = row['id']
        #         for element in data_elements:
        #             if (id not in self.feature_dict[name]):
        #                 self.feature_dict[name][id] = []
        #             self.feature_dict[name][id].append(data_elements)
            
        #     print(self.feature_dict.keys())

    def match_data(self, ref_vec, match_dict):
        # produces an output vector with the data in match_dict corresponding
        # to the key order presented in ref_vec. Fills in None if no match is found
        out = []
        for ref in ref_vec:
            if ref in match_dict.keys():
                out.append(match_dict[ref]) # assume value is a single element
            else:
                out.append(None)
        return out

    """
    Function: format_trial()
    Description:
        reformats the data in data_dict and stores it in data_vector
        stores the following:
            - trial ID string
            - Location
            - Transect
            - Flag Number
            - Force
            - Position
            - Time
            - Average Force
            - Average stiffness
            - Average stick-slip frequency
    """
    def format_trial(self):
        trial_ID = self.data_dict['trial_ID']
        
        # get the location and transect from the trial ID, which is in form 'L#T#F#'
        location = int(trial_ID[1])
        transect = int(trial_ID[3])
        flag_number = int(trial_ID[5:])

        force = self.data_dict['trimmed_force']
        pos = self.data_dict['trimmed_pos']
        time = self.data_dict['trimmed_time']
        avg_force = self.data_dict['average_force']

        stiffness, stick_slip, average_yield = self.calculate_metrics()
        print('Number of Stiffnes Measurements: ', len(stiffness))
        print('Number of Stick-Slip Measurements: ', len(stick_slip))

        # store the data in a dictionary
        trial_dict = {
            'filename' : self.path.split('/')[-1],
            'trial_ID': trial_ID,
            'location': location,
            'transect': transect,
            'flag_number': flag_number,
            'mode': self.data_dict.get('mode'),
            'force': force,
            'pos': pos,
            'time': time,
            'avg_force': avg_force,
            'stiffness': stiffness,
            'stick_slip': stick_slip,
            'average_yield': average_yield
        }

        # append the dictionary for the trial to the data vector
        self.data_vector.append(trial_dict)

        # add trial to the filenames vector
        self.filenames = np.append(self.filenames, self.path.split('/')[-1])

    def aggregate_data(self):
        ## TAG WEIGHTS:
        location_weight = 30
        transect_weight = 0
        flag_weight = 1
        
        # create empty vectors
        filenames = []
        numericTags = []
        trial_IDs = []
        locations = []
        flagNums = []
        avgForce = []
        avgStiffness = []
        avgStickSlip = []
        avgYield = []

        counter = 0
        # iterate through the data vector and collect the data
        for trial in self.data_vector:
            # aggregate only the active files
            filenames.append(trial['filename'])
            # ! Very arbitrary way of setting a unique tag for each trial
            trial_IDs.append(trial['trial_ID'])
            # numericTags.append((trial['location'] - 1) * location_weight + (trial['transect'] - 1) * transect_weight + trial['flag_number'] * flag_weight)
            numericTags.append(counter)
            counter += 1
            flagNums.append(trial['flag_number'])
            locations.append(trial['location'])
            avgForce.append(trial['avg_force'])
            avgStiffness.append(np.mean(trial['stiffness']))
            avgStickSlip.append(np.mean(trial['stick_slip']))
            avgYield.append(trial['average_yield'])
        
        
        self.aggregated_data = {
            'filenames': filenames,
            'trial_IDs': trial_IDs,
            'numericTags': numericTags,
            'locations': locations,
            'flagNums': flagNums,
            'avgForce': avgForce,
            'avgStiffness': avgStiffness,
            'avgStickSlip': avgStickSlip,
            'avgYield': avgYield
        }

    def output_data(self):
        # Assuming all vectors in the dictionary are of the same length
        num_rows = len(next(iter(self.aggregated_data.values())))

        # Transpose the data for CSV writing
        transposed_data = [list(row) for row in zip(*self.aggregated_data.values())]

        with open('output.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            
            # Write the keys as the first row
            writer.writerow(self.aggregated_data.keys())
            
            # Write the transposed data
            for row in transposed_data:
                writer.writerow(row)


    def user_plot_options_prompt(self):
        # prompt the user to select a variable for the x-axis and y-axis
        mode = self.user_mode_prompt()

        if (mode == 'Continuous'):
            x_axis = self.user_x_axis_prompt_continuous()
            y_axis = self.user_y_axis_prompt_continuous()
            return mode, x_axis, y_axis
        else:
            x_axis = self.user_x_axis_prompt_aggregate()
            y_axis = self.user_y_axis_prompt_aggregate()
            return mode, x_axis, y_axis

    def create_plot(self):
        # clear the figure
        self.fig.data = []

        x_axis = self.x_axis
        y_axis = self.y_axis

        # get the data
        x_data, y_data = self.parse_axis_choice()

        if (self.plot_mode == 0):
            self.plot_continuous(x_axis, x_data, y_axis, y_data)
            
        elif (self.plot_mode == 1): # plotting aggreate data based on chosen x and y axes
            self.plot_aggregate(x_axis, x_data, y_axis, y_data)

        elif (self.plot_mode == 2):
            self.plot_penetration_vs_shear(x_axis, x_data, y_axis, y_data)

        self.fig.show()

    def plot_continuous(self, x_axis, x_data, y_axis, y_data):
        print('\nPlotting continuous data...')
        counter = 0

        vec = np.linspace(0, 1, len(self.aggregated_data['numericTags']))
        c1 = sample_colorscale('viridis', list(vec))
        c2 = sample_colorscale('dense', list(vec))
        c3 = sample_colorscale('speed', list(vec))

        for trial in self.data_vector:
            if (self.highlight != 'None'): # highlight
                highlightIDs = self.feature_dict[self.highlight]
                if (trial['trial_ID'] not in highlightIDs): # non highlighted group
                    self.fig.add_trace(go.Scatter(x=trial[x_data], y=trial[y_data], mode='lines',
                        legendgroup="others",
                        legendgrouptitle_text='~'+self.highlight,
                        name=trial['trial_ID'],
                        text=trial['filename'],
                        line=dict(color=c3[counter], width=2),
                        connectgaps=True,
                    ))
                else: # highlighted group (plotted after so they go on top)
                    self.fig.add_trace(go.Scatter(x=trial[x_data], y=trial[y_data], mode='lines',
                        legendgroup="highlight",
                        legendgrouptitle_text=self.highlight,
                        name=trial['trial_ID'],
                        text=trial['filename'],
                        line=dict(color=c2[counter], width=3),
                        connectgaps=True,
                    ))
            else:
                self.fig.add_trace(go.Scatter(x=trial[x_data], y=trial[y_data], mode='lines',
                        name=trial['trial_ID'],
                        text=trial['filename'],
                        line=dict(color=c1[counter], width=2),
                        connectgaps=True,
                    ))
            counter += 1

        # # Edit the layout
        # set x and y axis labels for aggregate data
        self.fig.update_layout(
                            xaxis_title=x_axis + self.continuous_option_units[self.x_choice_idx],
                            yaxis_title=y_axis + self.continuous_option_units[self.y_choice_idx],
                            font=dict(
                                family="Arial",
                                size=18,
                                color="Black"
                            ))

    def plot_aggregate(self, x_axis, x_data, y_axis, y_data):
        print('\nPlotting aggregate data...')

        print('Selected Axes: ', x_axis, ' vs. ', y_axis)

        # plotting a highlighted group (2 groups)
        if (self.highlight != 'None'):
            highlight_x = []
            highlight_y = []
            highlight_labels = []
            base_x = []
            base_y = []
            base_labels = []

            highlightIDs = self.feature_dict[self.highlight]
            
            for i in range(len(self.aggregated_data['trial_IDs'])):
                if (self.aggregated_data['trial_IDs'][i] in highlightIDs):
                    highlight_x.append(x_data[i])
                    highlight_y.append(y_data[i])
                    highlight_labels.append(self.filenames[i])
                else:
                    base_x.append(x_data[i])
                    base_y.append(y_data[i])
                    base_labels.append(self.filenames[i])
            
            # plot highlighted dataset
            self.fig.add_trace(go.Scatter(x=highlight_x, y=highlight_y, mode='markers',
                                    name=self.highlight,
                                    text=highlight_labels,
                                    showlegend=True,
                                    marker=dict(
                                    size=16,
                                    color='gold',
                                    showscale=False
                                )))
            
            # plot rest of dataset
            self.fig.add_trace(go.Scatter(x=base_x, y=base_y, mode='markers',
                                    name='~' + self.highlight,
                                    text=base_labels,
                                    showlegend=True,
                                    marker=dict(
                                    size=16,
                                    color='slategray',
                                    showscale=False
                                )))
        
        else: 
            self.fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='markers',
                                    text=self.filenames,
                                    showlegend=False,
                                    marker=dict(
                                    size=16,
                                    color=self.aggregated_data['flagNums'], #set color equal to a variable
                                    colorscale='hot', # one of plotly colorscales
                                    showscale=False
                                )))

        # # Edit the layout
        # set x and y axis labels for aggregate data
        self.fig.update_layout(
                            title=x_axis + ' vs. ' + y_axis,
                            xaxis_title=x_axis + self.aggregate_option_units[self.x_choice_idx],
                            yaxis_title=y_axis + self.aggregate_option_units[self.y_choice_idx],
                            font=dict(
                                family="Arial",
                                size=18,
                                color="Black"
                            ),
                            coloraxis_showscale=True
                            )
    
    def plot_penetration_vs_shear(self, x_axis, x_data, y_axis, y_data):
        print('\nPlotting penetration vs shear data...')

        # loop through data_vector
        plot_x = []
        plot_y = []
        plot_IDs = []
        plot_tags = []

        for i in range(len(self.aggregated_data['trial_IDs'])):
            curr_ID = self.aggregated_data['trial_IDs'][i]
            if (curr_ID in self.intersection_IDs):
                # add data to x series
                for j in range(len(self.aggregated_data_2['trial_IDs'])):
                    if (curr_ID == self.aggregated_data_2['trial_IDs'][j]):
                        plot_x.append(self.aggregated_data[x_data][i])
                        plot_y.append(self.aggregated_data_2[y_data][j])
                        plot_IDs.append(curr_ID)
                        plot_tags.append(self.aggregated_data['numericTags'][i])
        
        self.fig.add_trace(go.Scatter(x=plot_x, y=plot_y, mode='markers',
                text=plot_IDs,
                showlegend=False,
                marker=dict(
                    size=16,
                    color=plot_tags, #set color equal to a variable
                    colorscale='Viridis', # one of plotly colorscales
                    showscale=False
            )))

        if(self.data_vector[0]['mode'] == 0):
            # data_vector has penetration data
            x_label = 'Penetration '
            y_label = 'Shear '
        else:
            # data_vector_2 has penetration data
            x_label = 'Shear '
            y_label = 'Penetration '


        # # Edit the layout
        # set x and y axis labels for aggregate data
        self.fig.update_layout(
            title='Penetration vs Shear Comparison',
            xaxis_title=x_label + x_axis + self.comparison_option_units[self.x_choice_idx],
            yaxis_title=y_label + y_axis + self.comparison_option_units[self.y_choice_idx],
            font=dict(
                family="Arial",
                size=18,
                color="Black"
            ))

    def user_mode_prompt(self):
        title = 'Do you want to plot continuous or aggregate data? '
        options = ['Continuous', 'Aggregate']
        mode, index = pick(options, title)
        self.plot_mode = index # continuous is 0, aggreate is 1
        return mode
    
    def user_feature_prompt(self):
        index = 0
        while (index == 0):
            file = self.select_file()
            self.feature_files.append(file)

            title = 'Do you want to add another feature file? '
            options = ['Yes', 'No']
            choice, index = pick(options, title)
        
        # process the data from feature files (if any)
        for feature_file in self.feature_files:
            self.process_features(feature_file)

        return choice, index

    def user_x_axis_prompt_continuous(self):
        title = 'What do you want to plot on the X-Axis? '
        self.x_axis, self.x_choice_idx = pick(self.continuous_options, title)
        return self.x_axis
    
    def user_y_axis_prompt_continuous(self):
        title = 'What do you want to plot on the Y-Axis? '
        self.y_axis, self.y_choice_idx = pick(self.continuous_options, title)
        return self.y_axis

    def user_x_axis_prompt_aggregate(self):
        title = 'Choose Horizontal-Axis Variable: '
        self.x_axis, self.x_choice_idx = pick(self.aggregate_options, title)
        return self.x_axis
    
    def user_y_axis_prompt_aggregate(self):
        title = 'Choose Vertical-Axis Variable: '
        self.y_axis, self.y_choice_idx = pick(self.aggregate_options, title)
        return self.y_axis
    
    def user_x_axis_prompt_compare(self):
        title = 'Choose Horizontal-Axis Variable: '
        self.x_axis, self.x_choice_idx = pick(self.comparison_options, title)
        return self.x_axis
    
    def user_y_axis_prompt_compare(self):
        title = 'Choose Vertical-Axis Variable: '
        self.y_axis, self.y_choice_idx = pick(self.comparison_options, title)
        return self.y_axis
    
    def menu_prompt(self):
        title = 'What do you want to do? '
        options = ['Save Plot', 
                   'Change Horizontal-Axis Variable', 
                   'Change Vertical-Axis Variable', 
                   'Swap Axes', 
                   'Highlight Feature', 
                   'Add Feature File'
                   ]
        if (self.plot_mode != 2):
            options.append('Add Force Dataset')
        options.append('Quit')
        choice, index = pick(options, title)

        if (index == 0):
            self.save_plot()
        elif(index == 1):
            if (self.plot_mode == 0):
                self.user_x_axis_prompt_continuous()
            elif (self.plot_mode == 1):
                self.user_x_axis_prompt_aggregate()
            else:
                self.user_x_axis_prompt_compare()
        elif (index == 2):
            if (self.plot_mode == 0):
                self.user_y_axis_prompt_continuous()
            elif (self.plot_mode == 1):
                self.user_y_axis_prompt_aggregate()
            else:
                self.user_y_axis_prompt_compare()
        elif (index == 3):
            # swap axes
            print('Swapping Axes...')
            self.x_axis, self.y_axis = self.y_axis, self.x_axis
        elif (index == 4):
            # highlight feature
            print('Highlighting Feature...')
            self.highlight_feature()
        elif (index == 5):
            # prompt user for feature file(s)
            self.user_feature_prompt()  
        elif (index == 6 and self.plot_mode != 2): # only give option if first time
            # bring up trial multi selection
            print('Adding force data...')
            self.add_directory()
        else:
            exit()

        return choice, index
    
    def highlight_feature(self):
        title = 'Choose Feature to Highlight: '
        options = list(self.feature_dict.keys())
        options.append('None')
        feature, index = pick(options, title)
        if (feature != 'None'):
            self.highlight = feature
        else:
            self.highlight = 'None'

    def add_directory(self):
        # copy the current data_vector and aggregate_data
        self.data_vector_2 = self.data_vector.copy()
        self.aggregated_data_2 = self.aggregated_data.copy()

        # clear old vectors so they can be filled again
        self.data_vector.clear()
        self.aggregated_data.clear()

        new_dir = self.select_directory(override=True)
        self.paths = self.traverse_csv_files(override=True, filepath=new_dir)


        self.path_index = 0
        # process and store data from all trial data files
        for self.path in self.paths:
            self.process_file()
            self.path_index += 1
    
        self.aggregate_data()

        # append the new data to the old data if they are the same protocol
        if (self.data_vector[0]['mode'] == self.data_vector_2[0]['mode']):
            self.data_vector_2.extend(self.data_vector)
            print('Additional force data is same protocol. Adding to previous dataset...')
        else: # the two force datasets are different protocols 
            # find the trial_ID intersection between the two datasets
            self.intersection_IDs = list(set(self.aggregated_data['trial_IDs']) & set(self.aggregated_data_2['trial_IDs']))
            
            self.penetration_vs_shear = True
            self.plot_mode = 2

            print('Additional data is of different protocol. Adding to new dataset...')
            x_axis = self.user_x_axis_prompt_compare()
            y_axis = self.user_y_axis_prompt_compare()

    def parse_axis_choice(self):
        x_axis = self.x_axis
        y_axis = self.y_axis
        
        if (self.plot_mode == 0): # continuous plotting
            if (x_axis == 'Time'):
                x_data = 'time'
            elif (x_axis == 'Position'):
                x_data = 'pos'
            elif (x_axis == 'Force'):
                x_data = 'force'
            
            if (y_axis == 'Time'):
                y_data = 'time'
            elif (y_axis == 'Position'):
                y_data = 'pos'
            elif (y_axis == 'Force'):
                y_data = 'force'

        elif (self.plot_mode == 1): # aggregate plotting
            if (x_axis == 'Transect-Flag Number'):
                x_data = self.aggregated_data['numericTags']
            elif (x_axis == 'Flag Number'):
                x_data = self.aggregated_data['flagNums']
            elif (x_axis == 'Average Force'):
                x_data = self.aggregated_data['avgForce']
            elif (x_axis == 'Average Stiffness'):
                x_data = self.aggregated_data['avgStiffness']
            elif (x_axis == 'Average Stick-Slip Period'):
                x_data = self.aggregated_data['avgStickSlip']
            elif (x_axis == 'Average Yield'):
                x_data = self.aggregated_data['avgYield']
            else: 
                # assume that this case is the choice of one of the added feature vectors
                x_data = self.feature_dict[x_axis]

            if (y_axis == 'Transect-Flag Number'):
                y_data = self.aggregated_data['numericTags']
            elif (y_axis == 'Flag Number'):
                y_data = self.aggregated_data['flagNums']
            elif (y_axis == 'Average Force'):
                y_data = self.aggregated_data['avgForce']
            elif (y_axis == 'Average Stiffness'):
                y_data = self.aggregated_data['avgStiffness']
            elif (y_axis == 'Average Stick-Slip Period'):
                y_data = self.aggregated_data['avgStickSlip']
            elif (y_axis == 'Average Yield'):
                y_data = self.aggregated_data['avgYield']
            else:
                # assume that this case is the choice of one of the added feature vectors
                y_data = self.feature_dict[y_axis]
        
        elif (self.plot_mode == 2): # penetration vs shear plotting
            if (x_axis == 'Average Force'):
                x_data = 'avgForce'
            elif (x_axis == 'Average Stiffness'):
                x_data = 'avgStiffness'
            elif (x_axis == 'Average Stick-Slip Period'):
                x_data = 'avgStickSlip'
            elif (x_axis == 'Average Yield'):
                x_data = 'avgYield'

            if (y_axis == 'Average Force'):
                y_data = 'avgForce'
            elif (y_axis == 'Average Stiffness'):
                y_data = 'avgStiffness'
            elif (y_axis == 'Average Stick-Slip Period'):
                y_data = 'avgStickSlip'
            elif (y_axis == 'Average Yield'):
                y_data = 'avgYield'
        
        return x_data, y_data
    
    
    def save_plot(self, fig_folder='figures'):
        parent_path = self.filepath
        figure_path = parent_path.replace('data/', '')
        path = os.path.join(figure_path, fig_folder)
        if not os.path.exists(path):
            os.mkdir(path)
        self.save_path = path
        plot_save_name = ''
        if (self.highlight == 'None'):
            plot_save_name = self.x_axis + '_vs_' + self.y_axis + '.png'
        else:
            plot_save_name = self.x_axis + '_vs_' + self.y_axis + '_highlight_' + self.highlight + '.png'
        # directory_path = '/home/qianlab/lassie-traveler/experiment_records/MH23_Data/'
        save_path_png = os.path.join(path, plot_save_name)
        
        print('Saving figure as file: ' + save_path_png)
        self.fig.write_image(save_path_png, scale=4, width=1080, height=720)
        
    
if __name__ == "__main__":
    plotter = FlexPlotter()
    plotter.run()



