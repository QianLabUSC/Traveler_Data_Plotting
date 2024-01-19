from force_analysis import *
import numpy as np
from scipy.fft import fft
from scipy.signal import find_peaks
from scipy.signal import savgol_filter
from scipy.stats import linregress
from scipy.interpolate import CubicSpline
from scipy.interpolate import Akima1DInterpolator


class Experimental(TravelerAnalysisBase):
    def __init__(self):
        super().__init__(_bypass_selection=False)
        # overwrite the axes definition in the base class
        self.fig, (self.ax, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(12,9))
        # self.fig.tight_layout(pad=10.0)
        self.force_detrended = None
        self.pdf = None

    def run(self):
        for self.path in self.paths:
            if ('valid' in self.path):
                continue
            self.ax.clear()
            self.ax2.clear()
            self.ax3.clear()

            self.process_file()

            self.path_index += 1
            self.fig.show()
            # plt.show()
        
        plt.show()
        self.pdf.close()

    # # detrend and perform frequency analysis
    # def process_file(self):
    #     super().process_file()
    #     self.detrend_data()
    #     self.freq_analysis()
    #     if (self.curr_file_valid == True):
    #         # write self.path to csv file
    #         self.save_plot()

    # velocity analysis
    def process_file(self):
        super().process_file()

        if (self.curr_file_valid == True):
            self.findVel()
            # write self.path to csv file
            self.save_plot()    
    
    def findVel(self):
        t = self.data_dict['time']
        pos_x = self.data_dict['position_x']
        pos_y = self.data_dict['position_y'] + self.groundHeight
        extension = np.sqrt(pos_x**2 + pos_y**2)
        force_x = self.data_dict['force_x']
        force_y = self.data_dict['force_y']
        force_vector = np.sqrt(force_x**2 + force_y**2)

        smoothed_positions = savgol_filter(extension, window_length=201, polyorder=3)
        
        dt = np.diff(t)
        dx = np.diff(smoothed_positions)

        vel = np.gradient(smoothed_positions, t)
        smoothed_vel = savgol_filter(vel, window_length=201, polyorder=3)

        self.data_dict['velocity'] = vel

        self.ax.clear()
        self.ax2.clear()
        self.ax3.clear()

        self.ax.plot(t, smoothed_positions, label='Depth vs Time')
        self.ax.set_xlabel('Time(s)')
        self.ax.set_ylabel('Depth (m)')

        # plot vertical lines where smoothed_position is equal to self.groundHeight
        idx = self.find_closest_index(smoothed_positions, self.groundHeight)
        line_pos = t[idx]
        self.ax.axvline(x=line_pos, color='r', linestyle='-')
        self.ax2.axvline(x=line_pos, color='r', linestyle='-')
        self.ax3.axvline(x=line_pos, color='r', linestyle='-')

        self.ax2.plot(t, vel, label='vel vs Time')
        self.ax2.plot(t, smoothed_vel, label='smoothed Velocity vs Time')
        self.ax2.set_xlabel('Time(s)')
        self.ax2.set_ylabel('dx (m)')

        self.ax3.plot(t, force_vector, label='Force vs Time')
        self.ax3.set_xlabel('Time(s)')
        self.ax3.set_ylabel('Force (N)')

    def detrend_data(self):
        x = self.data_dict['smoothed_pos']
        y = self.data_dict['smoothed_force']
        # Using scipy.stats.linregress for linear fitting
        slope, intercept, _, _, _ = linregress(x, y)

        # Creating the predicted y values using the fitted slope and intercept
        force_pred = slope * x + intercept

        # calculate the detrended force curve -- removing the linear component of the range.
        self.force_detrended = y - force_pred
        self.ax.plot(x, self.force_detrended, '-', label="Detrended Force", linewidth=2)
        self.ax.legend()

    def freq_analysis(self):
        # Frequency analysis using FFT
        x = self.data_dict['smoothed_pos']
        y = self.force_detrended

        # Handling duplicates - Averaging y values for duplicate x values
        df = pd.DataFrame({'x': x, 'y': y})
        df = df.groupby('x').mean().reset_index()

        # Now we can perform interpolation
        cs = CubicSpline(df.x, df.y)

        # Creating a regular interval for interpolation
        length = int(len(x) * 0.9)
        x_regular = np.linspace(x.min(), x.max(), length)

        # Assuming df is your DataFrame with x and y columns
        akima_interpolator = Akima1DInterpolator(df.x, df.y)
        y_akima = akima_interpolator(x_regular)
    
        fft_values = fft(y_akima)
        frequencies = np.fft.fftfreq(len(x_regular), d=(x_regular[1] - x_regular[0]))

        positive_freq = frequencies[:len(frequencies)//2]
        positive_fft_values = np.abs(fft_values)[:len(fft_values)//2]

        # Identifying peaks in the FFT to find dominant frequencies
        peaks, _ = find_peaks(positive_fft_values, height=0)

        # Plotting the FFT
        self.ax2.plot(positive_freq, positive_fft_values, label='FFT of Detrended Data')
        self.ax2.plot(positive_freq[peaks], positive_fft_values[peaks], 'x', label='Peaks')
        self.ax2.set_xlabel('Frequency (Hz)')
        self.ax2.set_ylabel('Amplitude')
        self.ax2.set_xlim(0, 1000)

        self.ax.plot(x_regular, y_akima, label='Interpolated Data')
        self.ax.legend()
        # self.ax2.show()

    def piecewise_analysis(self):
        force = self.data_dict['trimmed_force']
        x = self.data_dict['trimmed_pos']
        smoothed_force = savgol_filter(force, 50, 3)

        # Calculating the first derivative of the smoothed data
        first_derivative = np.diff(smoothed_force) / np.diff(x)

        # Identifying potential breakpoints (large changes in the first derivative)
        # Using find_peaks to find significant changes in the absolute value of the derivative
        peaks, _ = find_peaks(np.abs(first_derivative), height=np.std(first_derivative))

        # Adjusting breakpoints to align with original data indices
        breakpoints = x[peaks]

        # Adding the start and end points of the data to the breakpoints
        breakpoints = np.concatenate(([x[0]], breakpoints, [x[-1]]))

        # Segmenting the data and fitting linear models to each segment
        scipy_fits = []
        for i in range(len(breakpoints) - 1):
            # Segmenting
            start, end = breakpoints[i], breakpoints[i+1]
            segment_mask = (x >= start) & (x <= end)
            x_segment = x[segment_mask]
            y_segment = force[segment_mask]

            # Filtering short segments
            if len(x_segment) > 10:  # Threshold for segment length
                # Linear regression
                scipy_slope, scipy_intercept = scipy_linregress(x_segment, y_segment)
                scipy_fits.append((scipy_slope, scipy_intercept, start, end))

            # Plotting the original data and the piecewise linear fits
            plt.figure(figsize=(10, 6))
            plt.plot(x, force, label='Original Data')
            for model, start, end in scipy_fits:
                x_values = np.linspace(start, end, 100)
                y_values = scipy_slope * x_values + scipy_intercept
                plt.plot(x_values, y_values, label=f'Scipy Fit {start:.2f} to {end:.2f}', linestyle='--')

            plt.title('Piecewise Linear Regression on Noisy Data')
            plt.xlabel('x')
            plt.ylabel('y')
            plt.legend()
            plt.show()
    
    def save_plot(self, fig_folder='figures'):
        super().save_plot()
        if (self.pdf == None) :
            pdf_save_name = 'vel_analysis.pdf'
            self.pdf = PdfPages(os.path.join(self.output_path, pdf_save_name))
        self.pdf.savefig(bbox_inches='tight',dpi=300, pad_inches=1)

# Function to perform linear regression using scipy
def scipy_linregress(x, y):
    slope, intercept, _, _, _ = linregress(x, y)
    return slope, intercept


if __name__ == "__main__":
    plotter = Experimental()
    plotter.run()
