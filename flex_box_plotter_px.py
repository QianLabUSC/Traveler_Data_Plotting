from flex_plotter_px import *

class BoxPlotter(FlexPlotter):
    def __init__(self):
        super().__init__()

    def plot_aggregate(self, x_axis, x_data, y_axis, y_data):
        print('\nPlotting aggregate data...')

        print('Selected Axes: ', x_axis, ' vs. ', y_axis)

        # plot a box plot of the data of location as the x, selected y data as the y

        # self.fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='markers',
        #                         text=self.filenames,
        #                         showlegend=False,
        #                         marker=dict(
        #                         size=16,
        #                         color=self.aggregated_data['locations'], #set color equal to a variable
        #                         colorscale='bluered', # one of plotly colorscales
        #                         showscale=False
        #                     )))
        self.fig.add_trace(go.Box(y=y_data, x=self.aggregated_data['locations']))
        # # Edit the layout
        # set x and y axis labels for aggregate data
        self.fig.update_layout(
                            title=y_axis + ' vs. Location',
                            xaxis_title='Location',
                            yaxis_title=y_axis + self.aggregate_option_units[self.y_choice_idx],
                            font=dict(
                                family="Arial",
                                size=18,
                                color="Black"
                            ),
                            coloraxis_showscale=True
                            )
        

if __name__ == "__main__":
    plotter = BoxPlotter()
    plotter.run()