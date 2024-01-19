# Plotting Scripts (For Traveler Data)

## Prerequisites and Setup:

### Directory Structure

The scripts assume that you have data files created by a Traveler Leg in a specific directory structure.

The directory structure is as follows:

```jsx
<Parent_Directory>
	|  data 
	| 	|  <Traveler Data files (.csv)>
	|	  |  .....
	|  videos
	| 	|  <Traveler Video files (corresponding to data files)
	| 	|  .....
```

- The data files should follow the filename convention: `<identifier>_<location>_<transect>_<protocol>_<trial number>_<timestamp>.csv` for example: `WS23_L1_T1_P_2_Tue_Mar__7_13_23_05_2023.csv`
- In general, the plotting scripts either process single file selections or recursively process entire directories. So if you have 100 trials and want to process a set of 10 trials, you would need to copy these trials into a sibling directory following the above structure.
- If using the `video_sync.py` module, there should be a `videos` folder that contains video files with the same filenames as the data files.

### Python Configuration

Install all prerequisites contained in `requirements.txt`

## Included Modules

- `force_analysis.py`: describes a base functionality for loading and analyzing features in the traveler data logs. This script can be run standalone, but this functionality is not maintained.
- `basic_plotter.py` this module wraps the `force_analysis.py` module and generates simple plots. Run with `-h` flag for run options.
- `flex_plotter_px.py` This module brings up a rudimentary interactive plotter using Plotly. The plotter is controlled through a simple terminal interface.
- `[experimental.py](http://experimental.py)` contains experimental functionality.
- `video_sync.py` creates a video that shows a trial video and corresponding force curve with a synchronized, superimposed tracking dot. the `bias` parameter may need to be adjusted.