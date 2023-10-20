from force_analysis import *

class StiffnessAggregate(TravelerAnalysisBase):
    def __init__(self):
        super().__init__()
        # overwrite the axes definition in the base class
        self.fig, self.ax = plt.subplots(figsize=(12,6))

        self.multiplot, self.multiplot_ax = plt.subplots(figsize=(12,6))

        # create the aggregate figure
        self.aggregate_fig, self.aggregate_ax = plt.subplots(figsize=(12,6))

        self.save_path = None
        self.eval_mode = 1
        self.stiffness_values = []
        self.flag_numbers = []

    def process_file(self):
        super().process_file()
        if (self.curr_file_valid):
            self.evaluation_function()
            self.save_plot('aggregate_figures')
    
    def run(self):
        for self.path in self.paths:
            self.ax.clear()
            self.process_file()

            self.path_index += 1
            self.fig.show()
        
        # plot the aggregate figure
        self.aggregate_ax.scatter(self.flag_numbers, self.stiffness_values, marker='o')
        self.aggregate_ax.set_xlabel('Flag Number', fontsize=18)
        self.aggregate_ax.set_ylabel('Stiffness (N/m)', fontsize=18)
        self.aggregate_ax.set_title(self.data_dict['location'] + ' Crust Stiffness', fontsize=20)
        self.aggregate_ax.tick_params(labelsize=16)
        self.save_aggregate()

        print('Aggregate Data:')
        print(self.flag_numbers)
        print(self.stiffness_values)

        plt.show()

    def evaluation_function(self):
        # calculate the linear regression stiffness
        # for Mt. Hood, this function calculates the slope between the abs min and abs max
        pos = self.data_dict['trimmed_pos']
        force = self.data_dict['trimmed_force']
        
        # # convert to numpy arrays
        # pos = np.array(pos_list)
        # force = np.array(force_list)

        if (self.eval_mode == 1):
            # trim eval data range
            smooth_pos = self.data_dict['smoothed_pos']
            max_indices = self.data_dict['max_indices']
            min_indices = self.data_dict['min_indices'] 

            pos_min = smooth_pos[min_indices[0]]
            pos_max = smooth_pos[max_indices[0]]
            
            range_start = self.find_closest_index(pos, pos_min)
            range_end = self.find_closest_index(pos, pos_max)

            if (range_start > range_end):
                range_start = 0

            pos = pos[range_start:range_end]
            force = force[range_start:range_end]

        # Our model is y = a * x, so things are quite simple, in this case...
        # x needs to be a column vector instead of a 1D vector for this, however.
        x = pos[:,np.newaxis]
        a, _, _, _ = np.linalg.lstsq(x, force, rcond=None)

        self.ax.plot(x, a*x, linestyle='dashed', color='teal', label='Linear Regression Slope: ' + str(round(a[0], 2)) + ' N/m')

        self.stiffness_values.append(a[0])
        self.flag_numbers.append(self.data_dict['flag_number'])
    
    def plot_force(self):
        super().plot_force()
        flag = self.data_dict['flag_number']
        self.multiplot_ax.plot(self.data_dict['trimmed_pos'], self.data_dict['trimmed_force'], '-', label='Flag '+str(flag), linewidth=2)
        
        if (self.data_dict.get('mode') == 0):
            self.multiplot_ax.set_xlabel('Vertical Depth (meters)', fontsize=18)
            self.multiplot_ax.set_ylabel('Penetration Force (N)', fontsize=18)
        else:
            self.multiplot_ax.set_xlabel('Shear Length (meters)', fontsize=18)
            self.multiplot_ax.set_ylabel('Shear Force (N)', fontsize=18)
        
        self.multiplot_ax.set_title('Raw Force Along Transect', fontsize=24)
        self.multiplot_ax.legend()
        self.multiplot_ax.tick_params(labelsize=16)
        

    def save_aggregate(self):
        location = self.data_dict['location']
        aggregatefilename = location + '_Aggregate_Stiffness.png'
        multiplotname = location + '_Multiplot.png'
        save_path_png = os.path.join(self.save_path, aggregatefilename)
        multiplot_path = os.path.join(self.save_path, multiplotname)
        self.aggregate_fig.savefig(save_path_png, bbox_inches='tight', transparent=False, dpi=300)
        self.multiplot.savefig(multiplot_path, bbox_inches='tight', transparent=False, dpi=300)

if __name__ == "__main__":
    plotter = StiffnessAggregate()
    plotter.run()
