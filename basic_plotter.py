# import cv2
# import time
import csv
import argparse
from force_analysis import *
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_pdf import PdfPages

class BasePlotter(TravelerAnalysisBase):
    def __init__(self):
        parser = self.init_argparse()
        self.args = parser.parse_args()
        if (self.args.single):
            self.mode = 's'
            bypass_selection = True
        else:
            self.mode = 'b'
            bypass_selection = True

        super().__init__(_bypass_selection=bypass_selection)
        self.trimTrailingData = False
        # overwrite the axes definition in the base class
        self.fig, self.ax = plt.subplots(figsize=(12,6))
        self.pdf = None

        # self.csv_file = open(os.path.join(self.filepath, 'invalid_files.csv'), mode='w')
        # create a csv writer
        # self.csv_writer = csv.writer(self.csv_file, delimiter=',')

    def init_argparse(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            usage="%(prog)s [OPTION]",
            description="Plot a single force curve or all force \
                        curves in a directory and save the resulting figures. \
                        Defaults to plotting in batch mode by recursively processing all files \
                        in a directory."
        )
        parser.add_argument(
            "-v","--version", action="version",
            version=f"{parser.prog} version 1.0.0"
        )
        parser.add_argument(
            "-s","--single", action='store_true', help='Plots a single force curve'
        )
        parser.add_argument(
            '-b','--batch', action='store_true', help='(Default) Plots in directory batch mode (recursively plots all data files within a directory)'
        )
        parser.add_argument(
            '-i','--ids', action='store_true', help='Prompts for .csv file with ids to plot'
        )
        parser.add_argument(
            '-c', '--compound', action='store_true', help='Plots compound force curves (will plot all data within a directory on top of each other)'
        )

        return parser

    def process_file(self):
        super().process_file()
        if (self.curr_file_valid == True):
            # write self.path to csv file
            self.save_plot()


    
    def run(self):
        for self.path in self.paths:
            if ('valid' in self.path):
                continue
            if (not self.args.compound):
                self.ax.clear()

            self.process_file()

            self.path_index += 1
            self.fig.show()
            # plt.show()
        
        plt.show()
        self.pdf.close()


    # called by super.process_file()
    def plot_force(self):
        # reinitialize vectors based on changes from minmax finder
        pos = self.data_dict['trimmed_pos']
        force = self.data_dict['trimmed_force']
        time = self.data_dict['trimmed_time']
        average_force = self.data_dict['average_force']
        smooth_pos = self.data_dict['smoothed_pos']
        smooth_force = self.data_dict['smoothed_force']
        max_indices = self.data_dict['max_indices']
        min_indices = self.data_dict['min_indices']
        
        if (average_force < 0 and self.data_dict['mode'] == 0):
            print('WARNING: Irregular Force Profile Detected... skipping file...')
            self.curr_file_valid = False
        
        if (self.curr_file_valid == False):
            return


        # multiply pos by 100 to convert to cm
        pos *= 100

        self.ax.plot(pos, force, '-', label="Raw Force", linewidth=3)
        # self.ax.plot(smooth_pos[min_indices], smooth_force[min_indices], "v", label="Local Minima", markersize=10, markerfacecolor='r')
        # self.ax.plot(smooth_pos[max_indices], smooth_force[max_indices], "^", label="Local Maxima", markersize=10, markerfacecolor='g')

        if (self.data_dict.get('mode') == 0):
            self.ax.set_xlabel('Vertical Depth (cm)', fontsize=20)
            self.ax.set_ylabel('Penetration Force (N)', fontsize=20)
            self.ax.set_xlim(0, 3)
        else:
            self.ax.set_xlabel('Shear Length (meters)', fontsize=18)
            self.ax.set_ylabel('Shear Force (N)', fontsize=18)
        
        self.fig.suptitle(self.data_dict.get("suptitle"), fontsize=24)
        self.ax.set_title(self.data_dict.get("notes"), fontsize=18)
        self.ax.legend()
        self.ax.tick_params(labelsize=20)

    def save_plot(self, fig_folder='figures'):
        super().save_plot()
        if (self.pdf == None) :
            pdf_save_name = 'fig.pdf'
            self.pdf = PdfPages(os.path.join(self.output_path, pdf_save_name))
        self.pdf.savefig(bbox_inches='tight',dpi=300)
        
        eps_save_name = 'fig.png'
        self.fig.savefig(os.path.join(self.output_path, eps_save_name), format='png', bbox_inches='tight',dpi=300)


if __name__ == "__main__":
    plotter = BasePlotter()
    plotter.run()