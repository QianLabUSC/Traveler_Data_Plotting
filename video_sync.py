import cv2
import time
import argparse
import textwrap
from force_analysis import *
from matplotlib.animation import FuncAnimation

class VideoPlayer(TravelerAnalysisBase):
    def __init__(self):
        parser = self.init_argparse()
        self.args = parser.parse_args()

        if (self.args.batch):
            self.mode = 'b'
            bypass_selection = True
        else:
            self.mode = 's'
            bypass_selection = True

        super().__init__(_bypass_selection=bypass_selection)
        
        self.showLeadingData = True

        # overwrite the axes definition in the base class
        if (self.args.column):
            self.fig, (self.ax, self.video_ax) = plt.subplots(2, 1, figsize=(10,12))
        else:
            self.fig, (self.ax, self.video_ax) = plt.subplots(1, 2, figsize=(14,6))
        
  
        # handle time offset of video and data
        # increasing the value delays the video relative to the data
        # self.bias = 0.5 # seconds
        self.bias = 0.33 # seconds

        self.flip = False

        # variable initializations
        self.cap = None
        self.FPS = 0
        self.start_time = 0
        self.end_time = 0
        self.start_index = 0
        self.frame_index = 0
        self.frames_to_pass = 0
        self.frames_to_preview = 0
        self.frames_to_play = 0
        self.tracking_dot, = self.ax.plot([], [], 'ro')

        self.generic_labels = True

    def init_argparse(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            usage="%(prog)s [OPTIONS]",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent('''\
                Generates a force curve with a tracking dot matching a corresponding video.
                    > The data file must be in a directory named 'data' 
                        and the video file must be in a directory named 'videos'
                    > The data file should have a corresponding video file 
                        with the same name (except for file extension)
                    > The 'data' and 'videos' directories must be under 
                        the same parent directory
                    ''')
        )
        parser.add_argument(
            "-v","--version", action="version",
            version=f"{parser.prog} version 1.0.0"
        )
        parser.add_argument(
            "-s","--single", action='store_true', help='Plots a single data file (default)'
        )
        parser.add_argument(
            '-b','--batch', action='store_true', help='Plots in directory batch mode'
        )
        parser.add_argument(
            '-c','--column', action='store_true', help='Stacks the force curve above the video (defaults to side-by-side)'
        )
        

        return parser

    def process_file(self):
        super().process_file()
        if (self.curr_file_valid == False):
            return
        self.fig.tight_layout(pad=2.0)
        self.tracking_dot, = self.ax.plot([], [], 'ro', markersize=12)
        video_file = self.path.replace('.csv', '.mp4').replace('data', 'videos')
        video_save_file = video_file.replace('videos', 'generatedVideos')
        if (self.args.column):
            video_save_file = video_save_file.replace('.mp4', '_column.mp4')
        else:
            video_save_file = video_save_file.replace('.mp4', '_row.mp4')

        if (self.data_dict['version'] == 0): # for WS video files that are .avi format
            video_file = video_file.replace('.mp4', '_rotated.mp4')
        print('Video file: ', video_file)

        if ('WS' in video_file):
            self.bias = 0.33
        else:
            self.flip = True
            self.bias = 0.66
            
        # exit if the video file does not exist
        if (not os.path.exists(video_file)):
            print('ERROR: Video file does not exist!')
            return
        
        # make the generatedVideos directory if it does not exist
        if (not os.path.exists(video_save_file.replace(video_save_file.split('/')[-1], ''))):
            os.makedirs(video_save_file.replace(video_save_file.split('/')[-1], ''))

        self.cap = cv2.VideoCapture(video_file)

        if (self.cap.isOpened() == False):
            print("Error opening the video file")
        else:
            print('Video File opened!')
            self.FPS = int(self.cap.get(5)) # get the video FPS
            self.frames_to_preview = 0
            print('Video FPS: ', self.FPS )
            self.setup()
            # Animate the figure
            num_frames = 2 * self.frames_to_play + self.frames_to_preview
            if (self.FPS > 60):
                self.duty_cycle = 4
            else:
                self.duty_cycle = 1
            ani = FuncAnimation(self.fig, self.update, frames=num_frames, init_func=self.init, interval=1, cache_frame_data=False)
            # saves the animation in our desktop
            ani.save(video_save_file, writer = 'ffmpeg', fps = int(self.FPS))
            # play the animation
            print('Processing Complete!')

        self.cap.release()

    def setup(self):
        # get start time of plot
        # end_index = self.data_dict['end_index']
        self.start_time = self.data_dict['trimmed_time'][0]
        self.end_time = self.data_dict['trimmed_time'][-1]

        # adjust the frames to pass to preview some of the video
        self.frames_to_pass = int((self.start_time - self.bias) * self.FPS)
        
        self.frames_to_play = int((self.end_time - self.start_time) * self.FPS)
        self.frame_count = int(self.cap.get(7))
        self.frame_index = self.frames_to_pass

        #! wtf does this conditional do
        if (self.frames_to_play + self.frames_to_pass + self.frames_to_preview >= self.frame_count):
            correction = self.frames_to_play + self.frames_to_pass - self.frame_count
            self.frames_to_play -= correction

        if (self.generic_labels):
            self.ax.set_title('Force vs. Depth',fontsize=18)
            self.fig.suptitle('')

    def init(self):
        for i in range(self.frames_to_pass):
            self.cap.read()

        ret, frame = self.cap.read()
        if self.flip:
            frame = cv2.flip(frame, 0)
        # window_name = 'image'   
        # cv2.imshow(window_name, frame)
        self.video_img = self.video_ax.imshow(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        self.video_ax.axis('off')

        x_data = self.data_dict['trimmed_pos'][0]
        y_data = self.data_dict['trimmed_force'][0]
        self.tracking_dot.set_data(x_data, y_data)
        self.preview_counter = 0

    def update(self, i):
        if (i % 2 == 0):
            # render frame every duty_cycle frames
            if (i % self.duty_cycle == 0):
                ret, frame = self.cap.read()
                if not ret:
                    print('frame reading error!')
                    return
                
                # flip the frame vertically
                if self.flip:
                    frame = cv2.flip(frame, 0)

                # Display the video frame with the plot
                self.video_img.set_array(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                self.cap.read()

            # Update the plot
            # get the time of the video
            curr_time = self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 + self.bias
            data_index = bisect_right(self.data_dict['trimmed_time'], curr_time) - 1
            if (data_index < 0):
                data_index = 0
            x_data = self.data_dict['trimmed_pos'][data_index]
            y_data = self.data_dict['trimmed_force'][data_index]
            self.tracking_dot.set_data(x_data, y_data)

            if (i % 30 == 0) :
                print('Data Updated to: [', x_data, ', ', y_data, ']')
                print('Video Frame: ', int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
                print('Time: ', curr_time)
                print('Data Index: ', data_index)
        
        self.frame_index += 1

    def grab_frame(cap):
        ret,frame = cap.read()
        if not ret:
            print('frame reading error!')
            return
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        
if __name__ == "__main__":
    player = VideoPlayer()
    player.run()
