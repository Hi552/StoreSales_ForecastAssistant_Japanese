# Copyright 2024 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_theme import st_theme

sys.path.append("..")

from forecastic.api import (
    LLMNotAvailableException,
    get_app_settings,
    get_explain_df,
    get_filters,
    get_forecast_as_plotly_json,
    get_llm_summary,
    get_predictions,
    get_scoring_data,
    get_standardized_predictions,
    _process_predictions,
)
from forecastic.i18n import gettext
from forecastic.schema import FilterSpec

CHART_CONFIG = {"displayModeBar": False, "responsive": True}


sys.setrecursionlimit(10000)
app_settings = get_app_settings()

# Configure the page title, favicon, layout, etc
st.set_page_config(
    page_title=app_settings.page_title,
    layout="wide",
    page_icon="./datarobot_favicon.png",
)

with open("./style.css") as f:
    css = f.read()

st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def clean_column_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Clean column headers for display"""
    return df.rename(columns=lambda x: gettext(x.replace("_", " ").title()))


def set_title() -> None:
    """Set the title of the page"""

    with st.container(key="datarobot-logo"):
        col1, _ = st.columns([1, 2])
        theme = st_theme()
        logo = '<svg width="133" height="20" xmlns="http://www.w3.org/2000/svg" id="datarobot-logo"></svg>'
        if theme:
            if theme.get("base") == "light":
                logo = "./DataRobot_black.svg"
            else:
                logo = "./DataRobot_white.svg"
        col1.image(logo, width=200)
        st.markdown(
            f"<h1 style='text-align: center;'>{app_settings.page_title}</h1>",
            unsafe_allow_html=True,
        )


def fpa() -> None:
    set_title()
    chartContainer = st.container()
    explanationContainer = st.container()

    if "filters" not in st.session_state:
        st.session_state["filters"] = get_filters()
    with st.sidebar:
        with st.form(key="sidebar_form"):
            st.subheader(gettext("Select Filters for the Forecast"))

            for filter_widget in st.session_state["filters"]:
                column_name = filter_widget.column_name
                st.selectbox(
                    label=filter_widget.display_name,
                    options=filter_widget.valid_values,
                    key=f"filter_{column_name}",
                    placeholder=gettext("Choose an option"),
                    index=None
                )

            sidebarSubmit = st.form_submit_button(label=gettext("Run Forecast"))

        n_historical_records_to_display = st.number_input(
            gettext("Number of records to display"),
            min_value=10,
            max_value=200,
            value=min(200, app_settings.maximum_default_display_length),
            step=10,
        )
    if sidebarSubmit:
        with st.spinner(gettext("Processing forecast...")):
            series_selections = []
            for filter_widget in st.session_state["filters"]:
                column_name = filter_widget.column_name
                widget_value = [st.session_state[f"filter_{column_name}"]]
                series_selections.append(
                    FilterSpec(column=column_name, selected_values=widget_value)
                )
            try:
                scoring_data = get_scoring_data(filter_selection=series_selections)
                st.session_state["scoring_data"] = scoring_data
            except ValueError as e:
                st.error(str(e))
                st.stop()
            forecast_raw = get_predictions(scoring_data)

            forecast_processed = get_standardized_predictions(scoring_data)
            st.session_state["forecast_raw"] = forecast_raw

            st.session_state["forecast_processed"] = forecast_processed

            st.session_state["chart_json"] = get_forecast_as_plotly_json(
                scoring_data, n_historical_records_to_display
            )

        with st.spinner(gettext("Generating explanation...")):
            try:
                #st.session_state["_process_predictions"] = _process_predictions(forecast_raw)
                forecast_summary = get_llm_summary(forecast_raw)
                st.session_state["headline"] = forecast_summary.headline
                st.session_state["forecast_interpretation"] = (
                    forecast_summary.summary_body
                )

            except LLMNotAvailableException:
                pass
        st.session_state["explanations_df"] = clean_column_headers(
            get_explain_df(forecast_raw)
        )

    if "chart_json" in st.session_state:
        chartContainer.plotly_chart(
            go.Figure(st.session_state["chart_json"]),
            config=CHART_CONFIG,
            use_container_width=True,
        )

    with explanationContainer:
        if "forecast_raw" in st.session_state:
            with st.expander(gettext("Forecast Result"), expanded=False):
                st.write(pd.DataFrame(st.session_state["forecast_raw"]))
        if "forecast_interpretation" in st.session_state:
            st.subheader(gettext("**AI分析:**"))
            st.write(f"**{st.session_state['headline']}**")
            st.subheader(gettext("**モデル解釈:**"))
            st.write(st.session_state["forecast_interpretation"])
        if "explanations_df" in st.session_state:
            with st.expander(gettext("Important Features"), expanded=False):
                st.write(st.session_state["explanations_df"])
        if "scoring_data" in st.session_state:
            with st.expander(gettext("Scoring Data"), expanded=False):
                st.write(pd.DataFrame(st.session_state["scoring_data"]))
        #if "_process_predictions" in st.session_state:
        #    with st.expander(gettext("Process Predictions"), expanded=False):
        #        st.write(st.session_state["_process_predictions"])
        #if "forecast_processed" in st.session_state:
        #    with st.expander(gettext("Forecast Processed"), expanded=False):
        #        st.write(st.session_state["forecast_processed"])
                


def _main() -> None:
    hide_streamlit_style = """
    <style>
    # MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    fpa()


if __name__ == "__main__":
    _main()
