from force_analysis import *
from pick import pick
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib.colors as colorNorm



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
        
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(12,6))
        
        self.annot = None
        self.sc = None
        

        self.data_vector = []
        self.aggregated_data = {}
        self.plot_mode = 0
        self.x_axis = ''
        self.y_axis = ''
        self.x_choice_idx = 0
        self.y_choice_idx = 0
        self.filenames = np.array([])
        
        self.feature_dict = {}
        self.lock_fig = False
        self.active_files = [] # list files that are shown in plot
        self.highlight = 'None'
        
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

    def user_selection(self):
        root = tk.Tk()
        root.withdraw()  # Hide the main window

        self.filepath = self.select_directory()
        self.paths = self.traverse_csv_files()

        # prompt the user to select feature files
        self.user_feature_prompt()
        
        root.destroy()


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
        # process the data from feature files (if any)
        for feature_file in self.feature_files:
            self.extract_tags(feature_file)

        # process and store data from all trial data files
        for self.path in self.paths:
            self.process_file()
            self.path_index += 1

        self.active_files = self.filenames # initially set all files to be shown   
    
        self.aggregate_data()

        # prompt the user for plot options
        mode, x_axis, y_axis = self.user_plot_options_prompt()

        while(True):
            # plot the data
            self.create_plot()
            
            self.user_continue_prompt()
 
    def calculate_features(self):
        max_indices = self.data_dict['max_indices']
        min_indices = self.data_dict['min_indices']
        unique_pos = self.data_dict['smoothed_pos']
        smoothed_force = self.data_dict['smoothed_force']
        
        # local maxima positions and values
        max_pos = unique_pos[max_indices]
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
                if (max_pos[max_idx] > min_pos[min_idx] and max_pos[max_idx] < min_pos[min_idx+1]):
                    # calculate the tear length and the slope
                    tear = (max_pos[max_idx] - min_pos[min_idx])
                    curr_slope = (max_force[max_idx] - min_force[min_idx]) / tear

                    if (curr_slope > 25000): # this is a safeguard against outliers
                        print('Slope: ', curr_slope) 
                    else:
                        slopes.append(curr_slope)
                        stickSlip.append(tear)
                    break

        # check for max value after the last minima
        for max_idx in range(len(max_pos)):
            if (max_pos[max_idx] > min_pos[-1]):
                tear = (max_pos[max_idx] - min_pos[-1])
                curr_slope = (max_force[max_idx] - min_force[-1]) / tear
                slopes.append(curr_slope)
                stickSlip.append(tear)
                break

        return slopes, stickSlip, average_yield
    
    def extract_tags(self, filename):
        # read the data from the file
        data = self.csvReader(filename)

        # construct id column if not present
        if ('id' not in data.columns):
            id_col = []
            # check if there is a location, transect, and flag column
            if ('location' in data.columns and 'transect' in data.columns and 'flag' in data.columns):
                for index, row in data.iterrows():
                    id_col.append('L' + str(row['location']) + 'T' + str(row['transect']) + 'F' + str(row['flag']))
                data['id'] = id_col
            else:
                print('Malformatted Feature CSV File: ', filename)
                return None
        
        if ('tags' in data.columns):
            # ID is in form 'L#T#F#'
            # construct a tag dictionary, mapping tags to a list of IDs
            for index, row in data.iterrows():
                tag_list = row['tags'].replace(" ", '').split(',') # remove trailing quotes, spaces and split by comma
                for tag in tag_list:
                    if (tag not in self.feature_dict):
                        self.feature_dict[tag] = []
                    self.feature_dict[tag].append(row['id'])
            
            print(self.feature_dict.keys())
        


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

        stiffness, stick_slip, average_yield = self.calculate_features()

        # store the data in a dictionary
        trial_dict = {
            'filename' : self.path.split('/')[-1],
            'trial_ID': trial_ID,
            'location': location,
            'transect': transect,
            'flag_number': flag_number,
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
        numericTags = []
        trial_IDs = []
        flagNums = []
        avgForce = []
        avgStiffness = []
        avgStickSlip = []
        avgYield = []

        counter = 0
        # iterate through the data vector and collect the data
        for trial in self.data_vector:
            # aggregate only the active files
            if trial['filename'] in self.active_files:
                # ! Very arbitrary way of setting a unique tag for each trial
                trial_IDs.append(trial['trial_ID'])
                # numericTags.append((trial['location'] - 1) * location_weight + (trial['transect'] - 1) * transect_weight + trial['flag_number'] * flag_weight)
                numericTags.append(counter)
                counter += 1
                flagNums.append(trial['flag_number'])
                avgForce.append(trial['avg_force'])
                avgStiffness.append(np.mean(trial['stiffness']))
                avgStickSlip.append(np.mean(trial['stick_slip']))
                avgYield.append(trial['average_yield'])
            
        
        self.aggregated_data = {
            'trial_IDs': trial_IDs,
            'numericTags': numericTags,
            'flagNums': flagNums,
            'avgForce': avgForce,
            'avgStiffness': avgStiffness,
            'avgStickSlip': avgStickSlip,
            'avgYield': avgYield
        }


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
        self.ax.clear()
        x_axis = self.x_axis
        y_axis = self.y_axis

        # get the data
        x_data, y_data = self.parse_axis_choice()

        if (self.plot_mode == 0):
            print('\nPlotting continuous data...')
            colormap = cm.get_cmap('viridis')
            counter = 0
    
            normalizer = colorNorm.Normalize(vmin=0, vmax=len(self.aggregated_data['numericTags']))

            for trial in self.data_vector:
                if (trial['filename'] in self.active_files):
                    color_ = colormap(normalizer(counter))
                    counter += 1
                    self.sc = self.ax.plot(trial[x_data], trial[y_data], color=color_)
                    # self.sc = self.ax.scatter(trial[x_data], trial[y_data], color=color_, s=3)
                    self.annot = self.ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
            
            self.annot.set_visible(False)
            self.fig.canvas.mpl_connect("motion_notify_event", self.hover)
            
            # set x and y axis labels for aggregate data
            self.ax.set_xlabel(x_axis + self.continuous_option_units[self.x_choice_idx], fontsize=18)
            self.ax.set_ylabel(y_axis + self.continuous_option_units[self.y_choice_idx], fontsize=18)
            self.ax.tick_params(labelsize=16)  
            
        else: # plotting aggreate data based on chosen x and y axes
            print('\nPlotting aggregate data...')

            print('Selected Axes: ', x_axis, ' vs. ', y_axis)

            # get the colormap for the data depending on highlight state, otherwise default to viridis based on numeric tag
            colors = self.aggregated_data['numericTags']
            colormap = 'viridis'
            if (self.highlight != 'None'):
                highlightIDs = self.feature_dict[self.highlight]
                colors = np.zeros(len(self.aggregated_data['trial_IDs']))
                for i in range(len(self.aggregated_data['trial_IDs'])):
                    if (self.aggregated_data['trial_IDs'][i] in highlightIDs):
                        colors[i] = 1
                    else:
                        colors[i] = 0.5
                dummy_cmap = cm.get_cmap('viridis')
                dummy_norm = colorNorm.Normalize(vmin=0, vmax=1000)
                highlight_color = dummy_cmap(dummy_norm(1000))
                highlight_patch = mpatches.Patch(color=highlight_color, label=self.highlight)
                self.ax.legend(handles=[highlight_patch])


            self.sc = self.ax.scatter(x_data, y_data, c=colors, cmap=colormap, norm="linear")
            self.ax.set_title(x_axis + ' vs. ' + y_axis, fontsize=20)
            self.annot = self.ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                    bbox=dict(boxstyle="round", fc="w"),
                    arrowprops=dict(arrowstyle="->"))
            self.annot.set_visible(False)
            self.fig.canvas.mpl_connect("motion_notify_event", self.hover)

            # set x and y axis labels for aggregate data
            self.ax.set_xlabel(x_axis + self.aggregate_option_units[self.x_choice_idx], fontsize=18)
            self.ax.set_ylabel(y_axis + self.aggregate_option_units[self.y_choice_idx], fontsize=18)
            self.ax.tick_params(labelsize=16)  

        if (self.lock_fig == False):  
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
        else:
            plt.show()


    def user_mode_prompt(self):
        title = 'Do you want to plot continuous or aggregate data? '
        options = ['Continuous', 'Aggregate']
        mode, index = pick(options, title)
        self.plot_mode = index # continuous is 0, aggreate is 1
        return mode
    
    def user_feature_prompt(self):
        index = 0
        while (index == 0):
            title = 'Do you want to add a feature file? '
            options = ['Yes', 'No']
            choice, index = pick(options, title)
            if (index == 0):
                file = self.select_file()
                self.feature_files.append(file)
        
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
    
    def user_continue_prompt(self):
        title = 'What do you want to do? '
        options = ['Save Plot', 
                   'Change Horizontal-Axis Variable', 
                   'Change Vertical-Axis Variable', 
                   'Swap Axes', 
                   'Highlight Feature', 
                   'Toggle Experiments',
                   'Inspect Figure', 
                   'Quit']
        choice, index = pick(options, title)

        if (index == 0):
            self.save_plot()
        elif (index == 1 and self.plot_mode == 0):
            self.user_x_axis_prompt_continuous()
        elif (index == 2 and self.plot_mode == 0):
            self.user_y_axis_prompt_continuous()
        elif (index == 1 and self.plot_mode == 1):
            self.user_x_axis_prompt_aggregate()
        elif (index == 2 and self.plot_mode == 1):
            self.user_y_axis_prompt_aggregate()
        elif (index == 3):
            # swap axes
            print('Swapping Axes...')
            self.x_axis, self.y_axis = self.y_axis, self.x_axis
        elif (index == 4):
            # highlight feature
            print('Highlighting Feature...')
            self.highlight_feature()
        elif (index == 5):
            # bring up trial multi selection
            print('Selecting Data to Plot')
            self.choose_files()
        elif (index == 6):
            self.lock_fig = True
            plt.ioff()
        
        else:
            exit()

        return choice, index
    
    def highlight_feature(self):
        title = 'Choose Feature to Highlight: '
        options = list(self.feature_dict.keys())
        options.append('Back')
        feature, index = pick(options, title)
        if (feature != 'Back'):
            self.highlight = feature
        else:
            self.highlight = 'None'

    def choose_files(self):
        title = "Choose trials to plot (use space to select)"
        options = self.filenames
        selected = pick(options, title, multiselect=True, min_selection_count=1)
        self.active_files = [item[0] for item in selected]

        if (self.plot_mode == 0):
            self.aggregate_data() # reaggregate data if active files changes
    
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

        else: # aggregate plotting
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
        
        return x_data, y_data
    
    
    def save_plot(self, fig_folder='figures'):
        filename = self.path.split('/')[-1]
        parent_path = self.path.rstrip(filename)
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
        # print('Saving figure as file: ' + save_path_png)
        self.fig.savefig(save_path_png, bbox_inches='tight', transparent=False, dpi=300)

    def update_annot(self, ind):
        pos = self.sc.get_offsets()[ind["ind"][0]]
        self.annot.xy = pos
        text = "{}".format(" ".join([self.filenames[n] for n in ind["ind"]]))
        self.annot.set_text(text)
        self.annot.get_bbox_patch().set_facecolor('teal')
        self.annot.get_bbox_patch().set_alpha(0.4)
        
    def hover(self, event):
        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            cont, ind = self.sc.contains(event)
            if cont:
                self.update_annot(ind)
                self.annot.set_visible(True)
                self.fig.canvas.draw_idle()
            else:
                if vis:
                    self.annot.set_visible(False)
                    self.fig.canvas.draw_idle()
        
    
if __name__ == "__main__":
    plotter = FlexPlotter()
    plotter.run()



