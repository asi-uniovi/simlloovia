from itertools import islice
import pandas as pd
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dash import dash_table
import plotly.express as px
import plotly.graph_objects as go
import click

from simlloovia.monitor import EvType

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
)

app_exec_color = [
    "hsl(280, 100, 50)",
    "hsl(40, 100, 50)",
    "hsl(20, 100, 50)",
    "hsl(150, 100, 50)",
]

# Each line is for the events of an app: not-created, created, executing
colors = [
    "rgb(229,236,246)",
    "hsl(280, 100, 85)",
    app_exec_color[0],
    "rgb(229,236,246)",
    "hsl(40, 100, 85)",
    app_exec_color[1],
    "rgb(229,236,246)",
    "hsl(20, 100, 85)",
    app_exec_color[2],
    "rgb(229,236,246)",
    "hsl(150, 100, 85)",
    app_exec_color[3],
]

style_message_shown = {
    "width": "80%",
    "max-width": "800px",
    "padding": "1em",
    "margin": "auto",
    "margin-bottom": "1em",
    "overflow-y": "auto",
    "background-color": "orange",
    "display": "block",
}

style_message_hidden = {"display": "none"}

app.layout = html.Div(
    children=[
        html.H1(children="Requests"),
        html.Div(
            id="messages",
            style=style_message_hidden,
        ),
        html.Div(
            [
                "Base dir: ",
                dcc.Input(id="base-dir", value=".", type="text", persistence=True),
                " Prefix: ",
                dcc.Input(id="prefix", value="", type="text", persistence=True),
                html.Span(
                    id="req-selector",
                    children=[
                        " First request: ",
                        dcc.Input(id="first-req", value="0", type="number"),
                        " Last request: ",
                        dcc.Input(id="last-req", value="50", type="number"),
                    ],
                    style={"display": "inline"},
                ),
                html.Button("Apply", id="button-apply"),
            ]
        ),
        html.Br(),
        dcc.Tabs(
            id="tabs",
            value="tab-summary",
            children=[
                dcc.Tab(label="Summary", value="tab-summary"),
                dcc.Tab(label="Gantt", value="tab-gantt"),
                dcc.Tab(label="Detail", value="tab-detail"),
                dcc.Tab(label="Utilizations", value="tab-util"),
                dcc.Tab(label="Events", value="tab-events"),
            ],
        ),
        html.Div(id="tabs-content"),
    ]
)

tab_summary = html.Div(
    [
        dcc.Loading(
            id="loading-summary",
            type="default",
            children=[
                html.Div(
                    [
                        html.Div(
                            dash_table.DataTable(
                                id="req-table",
                                style_as_list_view=True,
                                style_header={
                                    "display": "none",
                                },
                            ),
                            className="two columns",
                        ),
                        html.Div(
                            dash_table.DataTable(
                                id="sim-table",
                                style_as_list_view=True,
                                style_header={
                                    "display": "none",
                                },
                            ),
                            className="two columns",
                        ),
                        html.Div(
                            dash_table.DataTable(
                                id="sol-table",
                                style_as_list_view=True,
                                style_header={
                                    "display": "none",
                                },
                            ),
                            className="four columns",
                        ),
                    ],
                    className="row",
                ),
                html.Br(),
                dcc.Graph(id="summ-reqs", className="four columns"),
                dcc.Graph(id="summ-resp_time", className="four columns"),
                html.Div(
                    [
                        html.H6("---", id="summ-cost"),
                        html.P("Cost ($)"),
                    ],
                    className="one column",
                ),
                html.Div(
                    [
                        html.H6("---", id="summ-wl-length"),
                        html.P("Workload length (h)"),
                    ],
                    className="one column",
                ),
            ],
            style={"width": "50%", "padding-left": "25%", "padding-right": "25%"},
        )
    ],
    className="row",
)

tab_gantt = [
    html.Div(
        [
            html.Br(),
            html.Div(
                dcc.RadioItems(
                    id="gantt-type",
                    options=[
                        {"label": "VM", "value": "vm"},
                        {"label": "App", "value": "app"},
                    ],
                    value="vm",
                    labelStyle={"display": "inline-block", "padding-right": "1em"},
                ),
                className="four columns",
            ),
            html.Div(
                [
                    "App filter: ",
                    dcc.Input(id="app-filter", value="", type="text", persistence=True),
                    html.Button("Apply filter", id="button-apply-app-filter"),
                ],
                className="four columns",
            ),
        ],
        className="row",
    ),
    dcc.Loading(
        id="loading-gantt",
        type="default",
        children=[
            html.Div(id="gantts"),
        ],
        style={"padding-top": "2em", "margin-top": "2em"},
    ),
]

tab_detail = html.Div(
    [
        html.Div(
            [
                html.Br(),
                html.Div(
                    [
                        "Aggregate by: ",
                        dcc.Checklist(
                            id="aggregations",
                            options=[
                                {"label": "App", "value": "app"},
                                {"label": "VM", "value": "vm"},
                                {"label": "Instance class", "value": "ic"},
                                {"label": "Creation", "value": "creation"},
                            ],
                            labelStyle={
                                "display": "inline-block",
                                "padding-right": "1em",
                            },
                            persistence=True,
                        ),
                    ],
                    className="six columns",
                ),
                html.Div(
                    [
                        "Aggregation type: ",
                        dcc.RadioItems(
                            id="aggregation-type",
                            options=[
                                {"label": "Average", "value": "mean"},
                                {"label": "Max", "value": "max"},
                            ],
                            value="mean",
                            labelStyle={
                                "display": "inline-block",
                                "padding-right": "1em",
                            },
                            persistence=True,
                        ),
                    ],
                    className="three columns",
                ),
                html.Div(
                    [
                        html.Br(),
                        dcc.Checklist(
                            id="plot",
                            options=[
                                {"label": "Plot", "value": "plot"},
                            ],
                            labelStyle={
                                "display": "inline-block",
                                "padding-right": "1em",
                            },
                            persistence=True,
                        ),
                    ],
                    className="two columns",
                ),
            ],
            className="Row",
        ),
        html.Br(),
        html.Br(),
        dcc.Loading(
            id="loading-detail-plot",
            type="default",
            children=[
                html.Div([], id="resp-time-plot"),
                html.Br(),
            ],
        ),
        dcc.Loading(
            id="loading-detail-table",
            type="default",
            children=[
                html.Div(dash_table.DataTable(id="detail-table", export_format="csv")),
            ],
        ),
    ]
)

tab_util = html.Div(
    [
        html.Br(),
        dcc.Loading(
            id="loading-plot-util",
            type="default",
            children=[
                dcc.Graph(id="plot-util"),
            ],
        ),
        dcc.Loading(
            id="loading-table-util",
            type="default",
            children=[
                html.Div(
                    dash_table.DataTable(
                        id="table-util",
                        style_as_list_view=True,
                    )
                ),
            ],
        ),
    ]
)

tab_events = html.Div(
    [
        html.Br(),
        dcc.Loading(
            id="loading-table-events",
            type="default",
            children=[
                dash_table.DataTable(
                    id="table-events",
                    page_current=0,
                    page_size=15,
                    page_action="custom",
                    export_format="csv",
                )
            ],
        ),
    ]
)


@app.callback(
    Output("tabs-content", "children"),
    Output("req-selector", "style"),
    Input("tabs", "value"),
)
def render_content(tab):
    tabs = {
        "tab-summary": tab_summary,
        "tab-gantt": tab_gantt,
        "tab-detail": tab_detail,
        "tab-util": tab_util,
        "tab-events": tab_events,
    }

    if tab in ["tab-gantt", "tab-detail"]:
        style = {"visibility": "visible"}
    else:
        style = {"visibility": "hidden"}

    return tabs[tab], style


@app.callback(
    Output(component_id="req-table", component_property="data"),
    Output(component_id="req-table", component_property="columns"),
    Output(component_id="sim-table", component_property="data"),
    Output(component_id="sim-table", component_property="columns"),
    Output(component_id="sol-table", component_property="data"),
    Output(component_id="sol-table", component_property="columns"),
    Output(component_id="summ-reqs", component_property="figure"),
    Output(component_id="summ-resp_time", component_property="figure"),
    Output(component_id="summ-cost", component_property="children"),
    Output(component_id="summ-wl-length", component_property="children"),
    Output(component_id="messages", component_property="children"),
    Output(component_id="messages", component_property="style"),
    Input(component_id="button-apply", component_property="n_clicks"),
    State(component_id="base-dir", component_property="value"),
    State(component_id="prefix", component_property="value"),
    State(component_id="first-req", component_property="value"),
    State(component_id="last-req", component_property="value"),
)
def apply_new_dir_summary(n_clicks, base_dir, prefix, first_req, last_req):
    try:
        first_req = int(first_req)
        last_req = int(last_req)

        summary = get_summary(base_dir, prefix)
    except Exception as e:
        msg = f"Error in apply_new_dir_summary: {e}"
        print(msg)
        return (
            None,
            None,
            None,
            None,
            None,
            None,
            {},
            {},
            None,
            None,
            msg,
            style_message_shown,
        )

    msg = []
    return (*summary, msg, style_message_hidden)


@app.callback(
    Output(component_id="gantts", component_property="children"),
    Input(component_id="button-apply", component_property="n_clicks"),
    Input("gantt-type", "value"),
    Input(component_id="button-apply-app-filter", component_property="n_clicks"),
    State(component_id="base-dir", component_property="value"),
    State(component_id="prefix", component_property="value"),
    State(component_id="first-req", component_property="value"),
    State(component_id="last-req", component_property="value"),
    State(component_id="app-filter", component_property="value"),
)
def apply_new_dir_gantt(
    n_clicks,
    gantt_type,
    n_clicks_app_filter,
    base_dir,
    prefix,
    first_req,
    last_req,
    app_filter,
):
    try:
        first_req = int(first_req)
        last_req = int(last_req)

        return get_gantt(gantt_type, base_dir, prefix, first_req, last_req, app_filter)
    except Exception as e:
        msg = f"Error in apply_new_dir_gantt: {e}"
        print(msg)
        return ({},)


@app.callback(
    Output(component_id="detail-table", component_property="data"),
    Output(component_id="detail-table", component_property="columns"),
    Output(component_id="resp-time-plot", component_property="children"),
    Input(component_id="button-apply", component_property="n_clicks"),
    Input(component_id="aggregations", component_property="value"),
    Input(component_id="aggregation-type", component_property="value"),
    Input(component_id="plot", component_property="value"),
    State(component_id="base-dir", component_property="value"),
    State(component_id="prefix", component_property="value"),
    State(component_id="first-req", component_property="value"),
    State(component_id="last-req", component_property="value"),
)
def update_detail_table_and_plot(
    n_clicks, aggregations, agg_type, plot, base_dir, prefix, first_req, last_req
):
    data = None
    cols = None
    children = None

    try:
        first_req = int(first_req)
        last_req = int(last_req)

        df_req = get_df_with_times(base_dir, prefix, first_req, last_req)

        df_table = df_req
        if aggregations:
            df_table = (
                df_table.groupby(aggregations)
                .agg({"req": "count", "resp_time": agg_type, "serv_time": "mean"})
                .reset_index()
            )

        data = df_table.to_dict("records")
        cols = dash_cols(df_table)
    except Exception as e:
        print("Error in update_detail_table_and_plot while aggregating:", e)
        return data, cols, children

    if plot:
        try:
            children = get_resp_time_plot(df_req, df_table, aggregations, agg_type)
        except Exception as e:
            print("Error in update_detail_table_and_plot while plotting:", e)

    return data, cols, children


def dash_cols(df):
    return [{"name": i, "id": i} for i in df.columns]


def get_summary(base_dir, prefix):
    df = pd.read_csv(
        f"{base_dir}/{prefix}.csv", names=["key", "value"], header=0, index_col=0
    ).T

    req_df = df[
        [
            "req_injected",
            "req_proc",
            "req_pending",
            "req_lost",
            "avg_resp_time",
            "max_resp_time",
            "min_resp_time",
        ]
    ].T.reset_index()

    sim_df = df[["cost", "util", "sim_time", "stats_time"]].T.reset_index()

    sol_df = df[
        ["sol_file", "workload", "workload_period", "workload_length"]
    ].T.reset_index()

    res_data = req_df.to_dict("records")
    sim_data = sim_df.to_dict("records")
    sol_data = sol_df.to_dict("records")

    res_cols = dash_cols(req_df)
    sim_cols = dash_cols(sim_df)
    sol_cols = dash_cols(sol_df)

    req_info_df = df[
        ["req_injected", "req_proc", "req_pending", "req_lost"]
    ].T.reset_index()
    req_info_df.value = req_info_df.value.astype("int")
    fig_req = px.bar(req_info_df, x="key", y="value")
    fig_req.update_yaxes(title="Number of requests")
    fig_req.update_xaxes(title="")

    resp_time_df = df[
        [
            "min_resp_time",
            "avg_resp_time",
            "max_resp_time",
        ]
    ].T.reset_index()
    fig_resp_time = px.bar(resp_time_df, x="key", y="value", color="key")
    fig_resp_time.update_layout(showlegend=False)
    fig_resp_time.update_yaxes(title="Response time (s)")
    fig_resp_time.update_xaxes(title="")

    cost = f"{float(df.cost):.2f}"
    wl_period_s = float(df["workload_period"].astype(float))
    wl_length_periods = float(df["workload_length"].astype(float))
    wl_length_h = f"{wl_period_s * wl_length_periods / 3600:.2f}"

    return (
        res_data,
        res_cols,
        sim_data,
        sim_cols,
        sol_data,
        sol_cols,
        fig_req,
        fig_resp_time,
        cost,
        wl_length_h,
    )


def get_df_with_times(base_dir, prefix, first_req, last_req):
    df_req = pd.read_csv(f"{base_dir}/{prefix}_reqs.csv", nrows=last_req)

    df_req = df_req[(df_req.req >= first_req) & (df_req.req <= last_req)]

    df_req["resp_time"] = df_req.end - df_req.creation
    df_req["serv_time"] = df_req.end - df_req.start

    return df_req


def get_resp_time_plot(req_df, df_table, aggregations, agg_type):
    if aggregations and len(aggregations) > 1 and "creation" in aggregations:
        aggregations.remove("creation")

        fig = go.Figure()

        df_groups = req_df.groupby(aggregations)

        for name, group in df_groups:
            if agg_type == "max":
                g = group.groupby("creation").resp_time.max().reset_index()
            else:
                g = group.groupby("creation").resp_time.mean().reset_index()
            name = name if isinstance(name, str) else "-".join(name)
            fig.add_trace(
                go.Scatter(x=g.creation, y=g.resp_time, mode="lines+markers", name=name)
            )

        fig.update_xaxes(title="Creation time (s)")

    elif aggregations:
        if "app" in aggregations:
            color = "app"
        elif "ic" in aggregations:
            color = "ic"
        elif "vm" in aggregations:
            color = "vm"
        else:
            color = "resp_time"

        # Add a column with the combination of the aggreated columns to be used
        # as name for the bars
        df_table["x"] = df_table[aggregations].apply(
            lambda x: "-".join(x.astype(str)), axis=1
        )

        fig = px.bar(df_table, x="x", y="resp_time", color=color)
        fig.update_xaxes(title=",".join(aggregations))
    else:  # No aggregation
        fig = px.bar(req_df, x="req", y="resp_time", color="app")

    fig.update_yaxes(title=f"{agg_type} resp time (s)")
    return dcc.Graph(id="resp-time-graph", figure=fig)


def get_gantt(gantt_type, base_dir, prefix, first_req, last_req, app_filter):
    df_req = pd.read_csv(f"{base_dir}/{prefix}_reqs.csv", nrows=last_req)

    if app_filter != "":
        df_req = df_req[df_req.app == app_filter]

    df_req = df_req[(df_req.req >= first_req) & (df_req.req <= last_req)]

    df_req["x_start"] = pd.to_datetime(df_req["creation"], unit="s")
    df_req["x_end"] = pd.to_datetime(df_req["start"], unit="s")
    df_req["type"] = "Waiting"

    # Obtain a continuous index for each app or vm
    df_req["req_app"] = df_req.groupby(gantt_type)["req"].rank(
        method="first", ascending=True
    )
    df_req["real_req_app"] = df_req.groupby("app")["req"].rank(
        method="first", ascending=True
    )

    # Copy all requests and change the type to "Service" so the waiting and the
    # service time are plotted at the same time
    df_service = df_req.copy()
    df_service["x_start"] = pd.to_datetime(df_service["start"], unit="s")
    df_service["x_end"] = pd.to_datetime(df_service["end"], unit="s")
    df_service["type"] = "Service"
    df_all = pd.concat([df_service, df_req])

    plot_order = sorted(list(df_req[gantt_type].unique()))

    figs = []
    for i in plot_order:
        df_i = df_all[df_all[gantt_type] == i]

        gantt = px.timeline(
            df_i,
            x_start="x_start",
            x_end="x_end",
            y="req_app",
            color="type",
            color_discrete_sequence=app_exec_color,
            facet_row=gantt_type,
            text="real_req_app" if gantt_type == "vm" else "vm",
            category_orders={gantt_type: plot_order},
        )

        gantt.update_yaxes(autorange="reversed", matches=None)

        gantt.update_layout(autosize=True, height=max(300, 18 * len(df_i)))

        figs.append(dcc.Graph(id=f"gantt_{i}", figure=gantt))

    return figs


@app.callback(
    Output(component_id="plot-util", component_property="figure"),
    Output(component_id="table-util", component_property="data"),
    Output(component_id="table-util", component_property="columns"),
    Input(component_id="button-apply", component_property="n_clicks"),
    State(component_id="base-dir", component_property="value"),
    State(component_id="prefix", component_property="value"),
    State(component_id="first-req", component_property="value"),
    State(component_id="last-req", component_property="value"),
)
def apply_new_dir_util(n_clicks, base_dir, prefix, first_req, last_req):
    try:
        first_req = int(first_req)
        last_req = int(last_req)

        df = pd.read_csv(f"{base_dir}/{prefix}_utils.csv")

        fig = px.bar(x=df.vm_name, y=df.util, color=df.ic)
    except Exception as e:
        print("Error in apply_new_dir_util:", e)
        fig = go.Figure()
        fig.update_layout(
            xaxis={"visible": False},
            yaxis={"visible": False},
            annotations=[
                {
                    "text": "Data for utilizations could not be read",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 28},
                }
            ],
        )
        return fig, None, None

    return fig, df.to_dict("records"), dash_cols(df)


@app.callback(
    Output(component_id="table-events", component_property="data"),
    Output(component_id="table-events", component_property="columns"),
    Input(component_id="button-apply", component_property="n_clicks"),
    Input(component_id="table-events", component_property="page_current"),
    Input(component_id="table-events", component_property="page_size"),
    State(component_id="base-dir", component_property="value"),
    State(component_id="prefix", component_property="value"),
)
def apply_new_dir_events(n_clicks, page_current, page_size, base_dir, prefix):
    try:
        with open(f"{base_dir}/{prefix}_events.csv") as csv_file:
            line_start = page_current * page_size
            line_end = line_start + page_size
            lines = islice(csv_file, line_start, line_end)
            row_list = []
            for line in lines:
                fields = line.split(",")
                event = EvType(int(fields[1]))
                row = {
                    "time": fields[0],
                    "event": event.name,
                    "req": "",
                    "app": "",
                    "vm": "",
                    "ic": "",
                    "price": "",
                }

                if event == EvType.VM_START:
                    row["vm"] = fields[2]
                    row["ic"] = fields[3]
                    row["price"] = fields[4]
                elif event == EvType.VM_END:
                    row["vm"] = fields[2]
                elif event == EvType.VM_ASSIGN_APP:
                    row["vm"] = fields[2]
                    row["app"] = fields[3]
                elif event == EvType.REQ_CREATION:
                    row["req"] = fields[2]
                    row["app"] = fields[3]
                elif event == EvType.REQ_START:
                    row["req"] = fields[2]
                    row["vm"] = fields[3]
                    row["app"] = fields[4]
                elif event == EvType.REQ_END:
                    row["req"] = fields[2]

                row_list.append(row)

            df = pd.DataFrame(row_list)
    except Exception as e:
        print("Error in apply_new_dir_events:", e)
        return None, None

    return df.to_dict("records"), dash_cols(df)


@click.command()
@click.option(
    "--port", type=int, required=False, help="Port to launch the web app", default=8050
)
@click.option("--debug", type=bool, required=False, help="Debug", default=True)
def main(port, debug):
    app.run_server(port=port, debug=debug)


if __name__ == "__main__":
    main()
