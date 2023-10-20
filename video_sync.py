import cv2
import time
from force_analysis import *
from matplotlib.animation import FuncAnimation

class VideoPlayer(TravelerAnalysisBase):
    def __init__(self):
        super().__init__()
        # overwrite the axes definition in the base class
        # self.fig, (self.ax, self.video_ax) = plt.subplots(1, 2, figsize=(14,6))
        self.fig, (self.ax, self.video_ax) = plt.subplots(2, 1, figsize=(10,12))
  
        # handle time offset of video and data
        # increasing the value 
        self.bias = 0.7 # seconds

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


    def process_file(self):
        super().process_file()
        self.fig.tight_layout(pad=2.0)
        self.tracking_dot, = self.ax.plot([], [], 'ro', markersize=12)
        video_file = self.path.replace('.csv', '.mp4').replace('data', 'videos')
        video_save_file = video_file.replace('videos', 'generatedVideos')
        if (self.data_dict['version'] == 0): # for WS video files that are .avi format
            video_file = video_file.replace('.mp4', '.avi')
        print('Video file: ', video_file)
        
        # exit if the video file does not exist
        if (not os.path.exists(video_file)):
            print('ERROR: Video file does not exist!')
            return

        self.cap = cv2.VideoCapture(video_file)

        if (self.cap.isOpened() == False):
            print("Error opening the video file")
        else:
            print('Video File opened!')
            self.FPS = int(self.cap.get(5)) # get the video FPS
            self.frames_to_preview = self.FPS
            print('Video FPS: ', self.FPS )
            self.setup()
            # Animate the figure
            num_frames = 2 * (self.frames_to_play + self.frames_to_preview)
            ani = FuncAnimation(self.fig, self.update, frames=num_frames, init_func=self.init, interval=1)
            # saves the animation in our desktop
            ani.save(video_save_file, writer = 'ffmpeg', fps = int(self.FPS))
            # play the animation
            print('Processing Complete!')

        self.cap.release()

    def setup(self):
        # get start time of plot
        self.start_index = self.data_dict['start_index']
        end_index = self.data_dict['end_index']
        self.start_time = self.data_dict['time'][self.start_index]
        self.end_time = self.data_dict['time'][end_index]

        # adjust the frames to pass to preview some of the video
        self.frames_to_pass = int(self.start_time * self.FPS) - self.frames_to_preview
        
        self.frames_to_play = int((self.end_time - self.start_time) * self.FPS)
        self.frame_count = int(self.cap.get(7))
        self.frame_index = self.frames_to_pass

        if (self.frames_to_play + self.frames_to_pass + self.frames_to_preview >= self.frame_count):
            correction = self.frames_to_play + self.frames_to_pass - self.frame_count
            self.frames_to_play -= correction

        self.video_ax.set_title('Live Video',fontsize=18)
        if (self.generic_labels):
            self.ax.set_title('Force vs. Depth',fontsize=18)
            self.fig.suptitle('')

    def init(self):
        for i in range(self.frames_to_pass):
            self.cap.read()

        ret, frame = self.cap.read()
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
        if (self.frame_index % 2 == 0):
            ret, frame = self.cap.read()
            if not ret:
                print('frame reading error!')
                return
            
            frame = cv2.flip(frame, 0)

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
            
            # Display the video frame with the plot
            self.video_img.set_array(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
        self.frame_index += 1
        
if __name__ == "__main__":
    player = VideoPlayer()
    player.run()
