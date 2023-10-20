from force_analysis import *
from pick import pick
import plotly.express as px
from plotly.express.colors import sample_colorscale
import plotly.graph_objects as go


class MudPlotter(TravelerAnalysisBase):
    def __init__(self):
        super().__init__()
        self.color_discrete_sequence=["red", "green", "blue", "goldenrod", "magenta"]
        self.data_vector = []
        self.filenames = np.array([])

        self.fig = go.Figure()

        self.trial_data = {}

    def user_selection(self):
        self.filepath = self.select_directory()
        self.paths = self.traverse_csv_files()

    def get_moisture(self):
        
    
    def run(self):
        for self.path in self.paths:
            self.process_file()

            self.path_index += 1

    def process_file(self):
        print('\n\nProcessing file ', self.path_index, ' of ', len(self.paths), '...')
        self.curr_file_valid = True
        # Read data from path
        self.travelerRead()

        if (self.curr_file_valid):
            self.process_data()
            self.data_vector.append(self.data_dict)

   
    def format_trial(self):
        filename = self.path.split('/')[-1]
        self.filenames = np.append(self.filenames, filename)
        # filename is in format:
        # MUD_EXPERIMENT_S0C16_1320_t1_Thu_Oct_12_16_44_34_2023

        # get the water volume
        water_volume = filename.split('_')[3]
        water_cups = (water_volume/120) * 0.5
        water_ratio = water_cups / (16+water_cups)

        # calculate the clay ratio
        sample_composition = filename.split('_')[2]
        # the sample composition is in the format S[int]C[int]
        sand, clay = self.extract_numbers(sample_composition)
        ratio = sand / (sand + clay)


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
            'water_ratio': water_ratio,
            'clay_ratio': ratio,
            'force': self.data_dict['trimmed_force'],
            'avg_force': self.data_dict['average_force'],
            'steady_state_force': steady_state_force,
            
        }

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
        

    
    def extract_numbers(self, s):
        n1 = int(re.search(r'S(\d+)', s).group(1))
        n2 = int(re.search(r'C(\d+)', s).group(1))
        return n1, n2