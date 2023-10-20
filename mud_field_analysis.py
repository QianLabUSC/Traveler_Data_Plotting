from force_analysis import *
from pick import pick
import csv
import plotly.express as px
from plotly.express.colors import sample_colorscale
import plotly.graph_objects as go


class MudAnalyzer(TravelerAnalysisBase):
    def __init__(self):
        super().__init__()
        self.color_discrete_sequence=["red", "green", "blue", "goldenrod", "magenta"]
        self.data_vector = []
        self.filenames = np.array([])

        self.fig = go.Figure()

        self.trial_data = {}

        self.output_filename = 'mud_analysis.csv'

    def user_selection(self):
        self.path = self.select_file()

    def get_moisture(self):
        # get water percentage as user input from terminal and ask for confirmation of value
        water_percentage = input("Enter the water percentage: ")
        print("You entered: ", water_percentage)
        confirm = input("Confirm? (y/n): ")
        if confirm == 'y':
            return water_percentage
        else:
            return self.get_moisture()

    
    def run(self):
        self.moisture = self.get_moisture()
        self.process_file()

    def process_file(self):
        self.curr_file_valid = True
        # Read data from path
        self.travelerRead()

        if (self.curr_file_valid):
            self.process_data()
            self.data_vector.append(self.data_dict)
        
        if (self.curr_file_valid):
            self.format_trial()
            self.run_analysis()


    def format_trial(self):
        filename = self.path.split('/')[-1]
        self.filenames = np.append(self.filenames, filename)
        # filename is in format:
        # MUD23_L#T#_t1_Thu_Oct_12_16_44_34_2023

        force = self.data_dict['trimmed_force']
        position = self.data_dict['trimmed_position']

## Calculate the average force from the shear data in the 85-95% position range
        pos_range = max(position) - min(position)
        lower_pos = 0.85 * pos_range
        upper_pos = 0.95 * pos_range
        lower_index = np.argmin(np.abs(position - lower_pos))
        upper_index = np.argmin(np.abs(position - upper_pos))

        steady_state_force = np.trapz(force[lower_index:upper_index], position[lower_index:upper_index]) / (position[upper_index] - position[lower_index])

        self.trial_data = {
            'filename': filename,
            'water_ratio': self.moisture,
            'force': self.data_dict['trimmed_force'],
            'avg_force': self.data_dict['average_force'],
            'steady_state_force': steady_state_force,
            
        }

    def run_analysis(self):
        constant = [11.7909, 0.3615, 8.4203]

        delta_phi = -constant(1) * ((self.trial_data['steady_state_force']/constant(0)) ** (1/constant(2)) - 1)
        phi_j = delta_phi + (1 - self.trial_data['water_ratio'])
        print("phi_j = ", phi_j)

        clay_ratio = (phi_j - 0.85)/(-0.2) + 0.5
        print("estimated clay ratio = ", clay_ratio)

        self.write_to_file(self.output_filename, self.trial_data['filename'], phi_j, clay_ratio)
    
    def write_to_file(self, filename, value1, value2, value3):
        # write a line of data to csv [filename] with values [value1, value2, value3]
        
        # if filename does not exist, create it and write the values to it
        with open(filename, 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([value1, value2, value3])
        


    def create_plot(self):
        # plot water percentage vs force
        self.fig.data = []

        # create a dictionary where keys are clay ratio and values are [water ratio, force]]
        plot_dict = {}
        for i in range(len(self.data_vector)):
            clay_ratio = self.data_vector[i]['clay_ratio']
            water_ratio = self.data_vector[i]['water_ratio']
            force = self.data_vector[i]['steady_state_force']

            if clay_ratio in plot_dict:
                plot_dict[clay_ratio].append([water_ratio, force])
            else:
                plot_dict[clay_ratio] = [[water_ratio, force]]

    def test_computation(self, force, water_ratio):
        constant = [11.7909, 0.3615, 8.4203]

        delta_phi = -constant[1] * ((force/constant[0]) ** (1/constant[2]) - 1)
        phi_j = delta_phi + (1 - water_ratio)
        print("phi_j = ", phi_j)

        clay_ratio = (phi_j - 0.85)/(-0.2) + 0.5
        print("estimated clay ratio = ", clay_ratio)

if __name__ == "__main__":
    test_ = MudAnalyzer()
    test_.test_computation(3, 0.2)