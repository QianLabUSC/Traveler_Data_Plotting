# import cv2
# import time
from force_analysis import *
from matplotlib.animation import FuncAnimation

class BasePlotter(TravelerAnalysisBase):
    def __init__(self):
        super().__init__()
        self.trimTrailingData = True
        # overwrite the axes definition in the base class
        self.fig, self.ax = plt.subplots(figsize=(12,6))

    def process_file(self):
        super().process_file()
        if (self.curr_file_valid == True):
            self.save_plot()
    
    def run(self):
        for self.path in self.paths:
            self.ax.clear()
            self.process_file()

            self.path_index += 1
            self.fig.show()
        
        plt.show()


if __name__ == "__main__":
    plotter = BasePlotter()
    plotter.run()