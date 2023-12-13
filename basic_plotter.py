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
        args = parser.parse_args()
        if (args.single):
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
                        curves in a directory and save the resulting figures"
        )
        parser.add_argument(
            "-v","--version", action="version",
            version=f"{parser.prog} version 1.0.0"
        )
        parser.add_argument(
            "-s","--single", action='store_true', help='Plots a single force curve'
        )
        parser.add_argument(
            '-b','--batch', action='store_true', help='Plots in directory batch mode'
        )
        parser.add_argument(
            '-i','--ids', action='store_true', help='Prompts for .csv file with ids to plot'
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
            self.ax.clear()
            self.process_file()

            self.path_index += 1
            self.fig.show()
            # plt.show()
        
        plt.show()
        self.pdf.close()

    def save_plot(self, fig_folder='figures'):
        super().save_plot()
        if (self.pdf == None) :
            pdf_save_name = 'figures.pdf'
            self.pdf = PdfPages(os.path.join(self.output_path, pdf_save_name))
        self.pdf.savefig(bbox_inches='tight',dpi=300)


if __name__ == "__main__":
    plotter = BasePlotter()
    plotter.run()