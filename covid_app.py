# Import our packages

import streamlit as st
import pandas as pd
import plotly_express as px
import pydeck as pdk
import matplotlib.pyplot as plt


# Upon loading dashboard, load and process the global death data
@st.cache
def load_global_death_data():
    # Pull data from Johns Hopkins source
   data = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv', error_bad_lines=False)
   # Drop columns province/state, geographic coordinates
   data.drop(['Province/State', 'Lat', 'Long'], axis=1, inplace=True)
   # Groupby country
   data = data.groupby(['Country/Region']).sum()
   return data

def load_us_death_data():
    # Pull data from Johns Hopkins source
   data = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv', error_bad_lines=False)
   # Drop unused columns
   data.drop(['Country_Region','UID','iso2','iso3','code3','Combined_Key','FIPS','Admin2','Lat', 'Long_', 'Population'], axis=1, inplace=True)
   # Groupby state
   data = data.groupby(['Province_State']).sum()
   return data


def date_convert(df):
    # transpose the frame
    df_tran = df.transpose().reset_index()
    # Next rename the column 
    df_tran.rename({'index': 'Date'}, axis=1, inplace=True)
    # Convert the date column to datetime
    df_tran['Date'] =  pd.to_datetime(df_tran['Date'])
    return df_tran

def tidy_death_data(df,group):
    df_tidy = pd.melt(df, id_vars=['Date'])
    df_tidy.drop(df_tidy[df_tidy['value'] < 10].index, inplace=True) # Drop all dates and countries with less than 10 recorded deaths
    df_tidy = df_tidy.assign(Days=df_tidy.groupby(group).Date.apply(lambda x: x - x.iloc[0]).dt.days) # Calculate # of days since 10th death by country
    # calculate daily change in deaths (raw)
    df_tidy['daily_change'] = df_tidy.sort_values([group,'Days']).groupby(group)['value'].diff()
    # calculate daily change in deaths (%)
    df_tidy['daily_pct_change'] = df_tidy.sort_values([group,'Days']).groupby(group)['value'].pct_change() * 100
    # calculate 7-day rolling average in deaths (raw)
    df_tidy['daily_roll_avg'] = df_tidy.groupby(group)['daily_change'].rolling(7).mean().round().reset_index(0,drop= True)
    # calculate 7-day rolling average in deaths (%)
    df_tidy['daily_pctchange_roll_avg'] = df_tidy.groupby(group)['daily_pct_change'].rolling(7).mean().round().reset_index(0,drop= True)

    # Replace the first day (NaN) as zero and missing rolling averages with the value that day
    df_tidy['daily_change'].fillna(0, inplace=True)
    df_tidy['daily_pct_change'].fillna(0, inplace=True)
    df_tidy['daily_roll_avg'].fillna(df_tidy['daily_change'], inplace=True)
    df_tidy['daily_pctchange_roll_avg'].fillna(df_tidy['daily_pct_change'], inplace=True)
    return df_tidy

# Function to be used for plotting the global deaths data with a line graph
def global_plot_create(data, x, y, title, xaxis, yaxis):
    fig = px.line(data, x=x, y=y, color='Country/Region', width=800, height=600)
    fig.update_layout(title=title, 
                      xaxis_title= xaxis, 
                      yaxis_title = yaxis,
                      legend_title_text='Countries',
                      yaxis_type="log", 
                      yaxis_tickformat = 'f',
                      xaxis_gridcolor = 'LightBlue',
                      yaxis_gridcolor = 'LightBlue',
                      paper_bgcolor='rgba(0,0,0,0)',
                      plot_bgcolor='rgba(0,0,0,0)')
    return fig

# Function to be used for plotting the US deaths data with a line graph
def us_plot_create(data, x, y, title, xaxis, yaxis):
    fig = px.line(data, x=x, y=y, color='Province_State', width=800, height=600)
    fig.update_layout(title=title, 
                      xaxis_title= xaxis, 
                      yaxis_title = yaxis,
                      legend_title_text='States',
                      yaxis_type="log", 
                      yaxis_tickformat = 'f',
                      xaxis_gridcolor = 'LightBlue',
                      yaxis_gridcolor = 'LightBlue',
                      paper_bgcolor='rgba(0,0,0,0)',
                      plot_bgcolor='rgba(0,0,0,0)')
    return fig

# Main function runs the app automatically when called
def main():

    page = st.sidebar.selectbox("Choose a dataset", ['Homepage', 'Global', 'US', 'County Map'])


    if page == 'Homepage':
        # Set title and subheader for dashboard
        st.title("COVID-19 Dashboard")
        st.header("Exploration of COVID-19 Deaths - Globally and USA.")
        st.subheader("Use the selection panel on the left to view global or US data. All data from Johns Hopkins University")


    elif page == 'Global':

        # Process all of the global death data using the created functions
        global_data = load_global_death_data()
        global_data = date_convert(global_data)
        global_deaths = tidy_death_data(global_data, group = 'Country/Region')

        st.title('Global COVID-19 Deaths')
        st.header('Daily COVID-19 deaths by country from Jan 22, 2020 - Present.')
        st.write("Raw Data:", global_data)

        # Create a list to pick the countries we want to look at
        # list uses the column names (the countries) of our original data
        cols = list(global_data[global_data.columns.difference(['Date'])])
        countries = st.multiselect('Select countries display', cols, ["US", "Italy", "United Kingdom"])

        # Set index in order to use loc operation
        global_deaths.set_index('Country/Region', inplace=True)
        # Limit the data to the countries selected above. 
        data_plot = global_deaths.loc[countries] 
        data_plot.reset_index(inplace=True)

        # Select the variable to be plotted
        cols = ['Total Confirmed Deaths', 'Deaths per Day','Daily Percentage Change']
        variable = st.selectbox('Select variable to display', cols)

        if variable == 'Total Confirmed Deaths':
            fig=global_plot_create(data = data_plot, 
                        x = 'Days',
                        y = 'value',
                        title = 'Global COVID-19 Deaths - Total',
                        xaxis = 'Number of days since 10th death',
                        yaxis = 'Confirmed Deaths')
            st.plotly_chart(fig)

        elif variable == 'Deaths per Day':
            fig=global_plot_create(data = data_plot, 
                        x = 'Days',
                        y = 'daily_roll_avg',
                        title = 'Daily Confirmed Deaths (7 day rolling average)',
                        xaxis = 'Number of days since 10th death',
                        yaxis = 'Confirmed Daily Deaths')
            st.plotly_chart(fig)
        else:
            fig2=global_plot_create(data = data_plot, 
                        x = 'Days',
                        y = 'daily_pctchange_roll_avg',
                        title = 'Daily Confirmed Deaths Growth (%)',
                        xaxis = 'Number of days since 10th death',
                        yaxis = 'Rate Change (%)')
            # Daily growth plot doesn't need a logged axis, so update the plot accordingly
            fig2.update_layout(yaxis_type="linear")

            st.plotly_chart(fig2)


    elif page == 'US':

        # Process all of the USA death data using the created functions
        us_data = load_us_death_data()
        us_data = date_convert(us_data)
        us_deaths = tidy_death_data(us_data, group='Province_State')

        st.title('US COVID-19 Deaths')
        st.header('Daily COVID-19 deaths by state from Jan 22, 2020 - Present.')
        st.write("Raw Data:", us_data)
        #us_deaths

        # Create a list to pick the states we want to look at
        # list uses the column names (the states) of our original data. difference drops the 'Date' column for selection
        cols = list(us_data[us_data.columns.difference(['Date'])])
        states = st.multiselect('Select states display', cols, ["California", "Massachusetts", "New York"])

        # Set index in order to use loc operation
        us_deaths.set_index('Province_State', inplace=True)
        # Limit the data to the countries selected above. 
        data_plot = us_deaths.loc[states] 
        data_plot.reset_index(inplace=True)

        # Select the variable to be plotted
        cols = ['Total Confirmed Deaths', 'Deaths per Day','Daily Percentage Change']
        variable = st.selectbox('Select variable to display', cols)

        if variable == 'Total Confirmed Deaths':
            fig=us_plot_create(data = data_plot, 
                        x = 'Days',
                        y = 'value',
                        title = 'US COVID-19 Deaths - Total by State',
                        xaxis = 'Number of days since 10th death',
                        yaxis = 'Confirmed Deaths')
            st.plotly_chart(fig)

        elif variable == 'Deaths per Day':
            fig=us_plot_create(data = data_plot, 
                        x = 'Days',
                        y = 'daily_roll_avg',
                        title = 'Daily Confirmed Deaths (7 day rolling average)',
                        xaxis = 'Number of days since 10th death',
                        yaxis = 'Confirmed Daily Deaths')
            st.plotly_chart(fig)
        else:
            fig2=us_plot_create(data = data_plot, 
                        x = 'Days',
                        y = 'daily_pctchange_roll_avg',
                        title = 'Daily Confirmed Deaths Growth (%)',
                        xaxis = 'Number of days since 10th death',
                        yaxis = 'Rate Change (%)')
            # Daily growth plot doesn't need a logged axis, so update the plot accordingly
            fig2.update_layout(yaxis_type="linear")

            st.plotly_chart(fig2)

    else:
        st.title('County Map')

        # Read in fresh dataframe of US deaths data
        us_deaths = pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv', error_bad_lines=False)
        
        # Drop rows with missing coordinates and any NaN values
        us_deaths = us_deaths[(us_deaths['Lat'] != 0)]
        us_deaths.dropna(inplace=True)

        # BELOW USED FOR SLIDER IN SELECTING DAY COUNT
        date_count = us_deaths.iloc[:,50:]
        max_days = len(date_count.columns)
        day = st.slider("Days since March 1, 2020", 1, max_days - 1, max_days - 1)
        
        # Create a list of column names (the dates) for display purposes
        date_list = list(us_deaths.iloc[:,50:])

        # Display the corresponding date of the day count since March 1, 2020
        date_selection = date_list[day]
        st.subheader(date_selection)


        st.header('Deaths by US county as of ' + str(us_deaths[date_selection].name))

        # Replace latest date of data column with the 'value' title to visualize
        us_deaths.columns = us_deaths.columns.str.replace(us_deaths[date_selection].name, "value")

        # Calculate a color ramp to use
        us_deaths['Color'] = us_deaths['value'].map(lambda x: [int(255*c) for c in  plt.cm.Wistia(x/2000)])

       
        # Create a pydeck map object that will update as we change our slider
        st.write(pdk.Deck(
                     map_style="mapbox://styles/mapbox/dark-v10",
                     mapbox_key = 'pk.eyJ1IjoicnVzc2hvd2QiLCJhIjoiY2puOTJpNmh5MHZjdTNwbXNxdDlyYTdmciJ9.C_p9lRLmh_J50bLDr2eScA',
                     tooltip={    
                            'html': '<b> {Combined_Key} </b> <br> <b>Deaths:</b> {value} ',
                            'style': {
                                    'color': 'white'
                                    }
                            },
                     initial_view_state={
                    "latitude": 36.6,
                    "longitude": -79,
                    "zoom": 4,
                    "pitch": 70,
                    "bearing": -37,
                },
                layers=[
                    pdk.Layer(
                       'ColumnLayer',
                        data=us_deaths,
                            get_position=["Long_", "Lat"],
                            get_elevation="value / 2",
                            elevation_scale=500,
                            #elevation_range=[0, 200],
                            radius=7000,
                            get_fill_color='Color',
                            #get_fill_color=['value / 2.5', 255, 255],
                            #get_fill_color = ["price_per_unit_area / 10", 0, 140, 140],
                            auto_highlight=True,
                            pickable=True,
                            material=True),
                    ],
                ))




if __name__ == '__main__':
    main()

