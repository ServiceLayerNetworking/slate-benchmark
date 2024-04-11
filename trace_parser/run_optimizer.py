import logging
from threading import Lock
import config as cfg
import span as sp
import time_stitching as tst
import pandas as pd
from IPython.display import display
from pprint import pprint
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.preprocessing import StandardScaler
import time
import math
import matplotlib.pyplot as plt
import sys
import numpy as np
import sys
import os
import glob

latency_func = {}
is_trained_flag = False
complete_traces = {}
all_traces = {}
prerecorded_trace = {}
svc_to_rps = {}
endpoint_level_inflight = {}
endpoint_level_rps = {}
endpoint_to_cg_key = {}
ep_str_callgraph_table = {}
sp_callgraph_table = {}
all_endpoints = {}
placement = {}
coef_dict = {}
profiling = True
trace_str = list()
# x_feature = "num_inflight_dict"
x_feature = "rps_dict"
target_y = "xt" # rt

'''
cluster_to_cid and cid_to_cluster should be deprecated
cluster_id is given as a number. e.g., 0, 1, 2, ...
'''
# cluster_to_cid = {"us-west": 0, "us-east": 1}
# cid_to_cluster = {0: "us-west", 1: "us-east"}
stats_mutex = Lock()
cluster_pcts = {}


def parse_stats_into_spans(body, cluster_id, service):
    spans = []
    lines = body.split("\n")
    '''
     ['us-west-1', 'profile-us-west-1', 'POST', '/profile.Profile/GetProfiles', '4a1afd4e0565e973d6bfd803432ae314', '31efa4c6f2197ac7', 'd6bfd803432ae314', '1704910272445', '1704910272447', '0', 'POST@/profile.Profile/GetProfiles,1,1|us-west-1', 'profile-us-west-1', 'POST', '/profile.Profile/GetProfiles', '2857529ac30263da51709ea9b6c9c578', '022d10421302e0f6', '51709ea9b6c9c578', '1704910272723', '1704910272725', '0', 'POST@/profile.Profile/GetProfiles,2,1|us-west-1', 'profile-us-west-1', 'POST', '/profile.Profile/GetProfiles', '3e7eb51dcdeeae6b1456481977f216fc', 'c23cfe5e72207f6a', '1456481977f216fc', '1704910272943', '1704910272945', '0', 'POST@/profile.Profile/GetProfiles,3,1|us-west-1', 'profile-us-west-1', 'POST', '/profile.Profile/GetProfiles', '1d99a31fa2261f7d62e52212c362bfda', 'b124fe1f6fc5c726', '62e52212c362bfda', '1704910273122', '1704910273124', '0', 'POST@/profile.Profile/GetProfiles,4,1|us-west-1', 'profile-us-west-1', 'POST', '/profile.Profile/GetProfiles', 'a7eed018a3853824b2bd871b66e07e1d', '4a73e25f4d0526c1', 'b2bd871b66e07e1d', '1704910273304', '1704910273306', '0', 'POST@/profile.Profile/GetProfiles,5,1|us-west-1', 'profile-us-west-1', 'POST', '/profile.Profile/GetProfiles', '9e6ffa80728847844c827938e1fd09c8', '5dc9301134652860', '4c827938e1fd09c8', '1704910273487', '1704910273489', '0', 'POST@/profile.Profile/GetProfiles,6,1|us-west-1', 'profile-us-west-1', 'POST', '/profile.Profile/GetProfiles', '7f1a217d64410611b44abf639652e341', 'f7fe7d2e60f46317', 'b44abf639652e341', '1704910273656', '1704910273657', '0', 'POST@/profile.Profile/GetProfiles,7,1|']
    '''
    service_level_rps = int(lines[0])
    inflightStats = lines[1]
    requestStats = lines[3:]
    # app.logger.debug('='*30)
    # app.logger.debug(f'lines: {lines}')
    # app.logger.debug('='*30)
    # app.logger.debug(f'service_level_rps: {service_level_rps}')
    # app.logger.debug('='*30)
    # app.logger.debug(f'inflightStats: {inflightStats}')
    # app.logger.debug('='*30)
    # app.logger.debug(f'requestStats: {requestStats}')
    # app.logger.debug('='*30)
    for span_stat in requestStats:
        ss = span_stat.split(" ")
        # app.logger.debug(f"ss: {ss}")
        # app.logger.debug(f"len(ss): {len(ss)}")
        ## NOTE: THIS SHOUD BE UPDATED WHEN member fields in span class is updated.
        if len(ss) != 11:
            app.logger.error(f"ERROR, len(ss) != 11, {len(ss)}, {ss}")
            # assert False
            continue
        region = ss[0]
        serviceName = ss[1]
        method = ss[2]
        path = ss[3]
        traceId = ss[4]
        spanId = ss[5]
        parentSpanId = ss[6]
        startTime = int(ss[7])
        endTime = int(ss[8])
        bodySize = int(ss[9])
        # 'GET@/hotels,0,1|POST@/reservation,2,0|GET@/recommendations,2,1|'
        endpointInflightStats = ss[10].split("|")
        if endpointInflightStats[-1] == "":
            endpointInflightStats = endpointInflightStats[:-1]
        rps_dict = dict()
        inflight_dict = dict()
        for ep_load in endpointInflightStats:
            method_and_path = ep_load.split(",")[0]
            method = method_and_path.split("@")[0]
            path = method_and_path.split("@")[1]
            endpoint = sp.Endpoint(svc_name=serviceName, method=method, url=path)
            rps = ep_load.split(",")[1]
            inflight = ep_load.split(",")[2]
            rps_dict[str(endpoint)] = rps
            inflight_dict[str(endpoint)] = inflight
        spans.append(sp.Span(method, path, serviceName, region, traceId, spanId, parentSpanId, startTime, endTime, bodySize, rps_dict=rps_dict, num_inflight_dict=inflight_dict))
        print(f"new span parsed")
    return spans


def fit_polynomial_regression(data, y_col_name, svc_name, ep_str, cid, trace_file_name, directory):
    degree_list = [1,2,3,4]
    plt.figure()
    df = pd.DataFrame(data)
    x_colnames = [x for x in df.columns if x != y_col_name]
    X = df[x_colnames]
    y = df[y_col_name]
    plt.scatter(X, y, color='blue', alpha=0.1, label='Data') # plot true data only once
    for degree in degree_list: # plot different degree of polynomial
        X_transformed = np.hstack((X**degree, np.ones(X.shape)))
        model = LinearRegression(fit_intercept=False)  # Intercept is manually included in X_transformed
        model.fit(X_transformed, y)
        # print(f'x_colnames: {x_colnames}')
        feature_names = x_colnames.copy() + ['intercept']
        coefficients = pd.Series(model.coef_, index=feature_names)

        '''plot'''
        X_plot = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
        X_plot_transformed = np.hstack((X_plot**degree, np.ones(X_plot.shape)))
        y_plot = model.predict(X_plot_transformed)
        plt.plot(X_plot, y_plot, linewidth=1, label=f'Cubic Fit: $a \cdot x^{degree} + b$')
        print(f"plt.plot, degree: {degree}")
    plt.xlabel(x_feature)
    plt.ylabel(y_col_name +" ms")
    plt.title(f'{ep_str} in {cid}')
    plt.legend()
    pdf_fn = f"{directory}/latency-{x_feature}-{svc_name}.pdf"
    plt.savefig(pdf_fn)
    print(f"**output: {pdf_fn}")
    plt.show()
    return coefficients.to_dict()

def fit_and_visualize_linear_regression(data, y_col_name, svc_name, ep_str, cid):
    # Convert data to DataFrame and separate features and target
    df = pd.DataFrame(data)
    X = df.drop(columns=[y_col_name])
    y = df[y_col_name]
    
    # Fit the linear regression model
    model = LinearRegression()
    model.fit(X, y)
    
    # Prepare coefficients and intercept for visualization and further use
    coefficients = pd.Series(model.coef_, index=X.columns).append(pd.Series([model.intercept_], index=['intercept']))
    
    # Replace negative coefficients with 1, log error
    negative_coefs = coefficients < 0
    if negative_coefs.any():
        print(coefficients[negative_coefs])
        print(f"ERROR: Negative coefficients encountered. Setting them to 1.")
        coefficients[negative_coefs] = 1
    
    # Visualize the linear regression results
    plt.scatter(X, y, color='blue', alpha=0.1)
    x_vals = pd.DataFrame([0, 30], columns=[X.columns[0]])
    y_vals = model.predict(x_vals)
    plt.plot(x_vals, y_vals, color='red', linewidth=2)
    plt.xlabel(X.columns[0])
    plt.ylabel(f'{y_col_name} (ms)')
    plt.title(f"{ep_str} in {cid}")
    
    # Save the plot
    # plt.savefig(f"latency-{X.columns[0]}-{svc_name}.pdf")
    plt.show()
    
    # Return coefficients as a dictionary
    return coefficients.to_dict()


def fit_linear_regression(data, y_col_name, svc_name, ep_str, cid):
    df = pd.DataFrame(data)
    x_colnames = list()
    for colname in df.columns:
        if colname != y_col_name:
            x_colnames.append(colname)
    X = df[x_colnames]
    y = df[y_col_name]
    model = LinearRegression()
    model.fit(X, y)
    feature_names =  list(X.columns)+ ['intercept']
    coefficients_df = pd.DataFrame(\
            {'Feature': feature_names, \
            'Coefficient':  list(model.coef_)+[model.intercept_]}\
        )
    coef = dict()
    for index, row in coefficients_df.iterrows():
        if row['Coefficient'] < 0:
            print(row)
            print(f"ERROR: row['Coefficient'] < 0: {row['Coefficient']}")
            ##########################
            row['Coefficient'] = 1
            ##########################
            # assert False
        coef[row['Feature']] = row['Coefficient']
    key_for_coef = list()
    for key in coef:
        if key == 'intercept':
            b = coef[key]
        else:
            key_for_coef.append(key)
    a = coef[key_for_coef[0]]
    x_list = [0, 30]
    y_list = list()
    for x in x_list:
        ''' linear regression '''
        y_list.append(a*x+b)
    plt.plot(X, y, 'bo', alpha=0.1)
    plt.plot(x_list, y_list, color='red', linewidth=2)
    plt.xlabel(x_feature)
    plt.ylabel(f'{target_y} (ms)')
    plt.title(ep_str + " in " + cid)
    replaced_ep_str = ep_str.replace("/", "_")
    plt.savefig(f"latency-{x_feature}-{svc_name}.pdf")
    plt.show()
    return coef


def train_latency_function_with_trace(traces, trace_file_name, directory):
    # df = pd.read_csv(f"{trace_file_path}")
    # traces = sp.file_to_trace(trace_file_path)
    df = tst.trace_to_df(traces)
    # df.to_csv(f"trace_to_file.csv")
    for cid in df["cluster_id"].unique():
        cid_df = df[df["cluster_id"]==cid]
        for svc_name in cid_df["svc_name"].unique():
            cid_svc_df = cid_df[cid_df["svc_name"]==svc_name]
            if svc_name not in latency_func:
                latency_func[svc_name] = dict()
            if svc_name not in coef_dict:
                coef_dict[svc_name] = dict()
            for ep_str in cid_svc_df["endpoint_str"].unique():
                ep_df = cid_svc_df[cid_svc_df["endpoint_str"]==ep_str]
                # Data preparation: load(X) and latency(y) 
                data = dict()
                y_col = "latency"
                for index, row in ep_df.iterrows():
                    for key, val in row[x_feature].items():
                        if key not in data:
                            data[key] = list()
                        data[key].append(val)
                    if y_col not in data:
                        data[y_col] = list()
                    data[y_col].append(row[target_y])
                
                ''' linear regression '''
                # coef_dict[svc_name][ep_str] = fit_linear_regression(data, y_col, svc_name, ep_str, cid)
                # coef_dict[svc_name][ep_str] = fit_and_visualize_linear_regression(data, y_col, svc_name, ep_str, cid)
                coef_dict[svc_name][ep_str] = fit_polynomial_regression(data, y_col, svc_name, ep_str, cid, trace_file_name, directory)
    return coef_dict


def trace_string_file_to_trace_data_structure(trace_string_file_path, sample_ratio=1.0):
    col = ["cluster_id","svc_name","method","path","trace_id","span_id","parent_span_id","st","et","rt","xt","ct","call_size","inflight_dict","rps_dict"]
    df = pd.read_csv(trace_string_file_path, names=col, header=None)
    print(f"len(df): {len(df)}")
    df = df.loc[df['rt'] > 0]
    print(f"after negative rt filter, len(df): {len(df)}")
    
    # df.to_csv(f"trace_string_before_sampling.csv")
    # if sample_ratio < 1.0:
    #     df = df.groupby(['trace_id']).sample(frac=sample_ratio)
    #     df = df.reset_index(drop=True)
    # df.to_csv(f"trace_string_after_sampling.csv")
    # print(f"len(df): {len(df)} after sampling")
    # span_df = df.iloc[:, :-2] # inflight_dict, rps_dict
    # inflight_df = df.iloc[:, -2:-1] # inflight_dict, rps_dict
    # rps_df = df.iloc[:, -1:] # inflight_dict, rps_dict
    
    num_filter_rps_datapoint = 0
    
    list_of_span = list()
    for index, row in df.iterrows():
        if row["cluster_id"] == "SLATE_UNKNOWN_REGION" or row["svc_name"] == "consul":
            continue
        # row: user-us-west-1@POST@/user.User/CheckUser:1|,user-us-west-1@POST@/user.User/CheckUser:14|
        # , is delimiter between rps_dict and inflight_dict
        # | is delimiter between two endpoints
        # @ is delimiter between svc_name @ method @ path
        
        num_inflight_dict = dict()
        rps_dict = dict()
        
        # inflight_row =  "user-us-west-1@POST@/user.User/CheckUser:1|user-us-west-1@POST@/user.User/CheckUser:1|"
        # print(row)
        # print(row["inflight_dict"])
        inflight_list = row["inflight_dict"].split("|")[:-1]
        for ep_inflight in inflight_list:
            # print(row)
            temp = ep_inflight.split(":")
            # print(f"len(temp): {len(temp)}")
            # print(temp)
            assert len(temp) == 2
            ep = temp[0] # user-us-west-1@POST@/user.User/CheckUser
            inflight = int(temp[1]) # 1
            svc_name = ep.split("@")[0]
            method = ep.split("@")[1]
            path = ep.split("@")[2]
            num_inflight_dict[ep] = inflight
            
        rps_list = row["rps_dict"].split("|")[:-1]
        for ep_rps in rps_list:
            temp = ep_rps.split(":")
            # print(f"len(temp): {len(temp)}")
            assert len(temp) == 2
            ep = temp[0] # user-us-west-1@POST@/user.User/CheckUser
            rps = int(temp[1]) # 1
            ''' NOTE: HARDCODED, RPS FILTER'''
            if rps > 1000:
                continue
            svc_name = ep.split("@")[0]
            method = ep.split("@")[1]
            path = ep.split("@")[2]
            rps_dict[ep] = rps
        ''' NOTE: HARDCODED, RPS FILTER'''
        if rps > 1200:
            num_filter_rps_datapoint += 1
            continue
        ##################################################
        # serviceName = row["svc_name"]
        # if serviceName.find("-us-") != -1:
        #     serviceName = serviceName.split("-us-")[0]
        ##################################################
        span = sp.Span(row["method"], row["path"], row["svc_name"], row["cluster_id"], row["trace_id"], row["span_id"], row["parent_span_id"], st=float(row["st"]), et=float(row["et"]), callsize=int(row["call_size"]), rps_dict=rps_dict, num_inflight_dict=num_inflight_dict)
        list_of_span.append(span)
        # print(str(span))
        # exit()
    print(f"-- num_filter_rps_datapoint: {num_filter_rps_datapoint}")  
    # Convert list of span to traces data structure
    all_traces = dict()
    for span in list_of_span:
        if span.cluster_id not in all_traces:
            all_traces[span.cluster_id] = dict()
        if span.trace_id not in all_traces[span.cluster_id]:
            all_traces[span.cluster_id][span.trace_id] = list()
        all_traces[span.cluster_id][span.trace_id].append(span)
    
    for cid in all_traces:
        tot_num_svc = 0
        for tid in all_traces[cid]:
            tot_num_svc += len(all_traces[cid][tid])
        avg_num_svc = tot_num_svc / len(all_traces[cid])
        required_num_svc = math.ceil(avg_num_svc)
        required_num_svc = 2
        print(f"avg_num_svc in {cid}: {avg_num_svc}")
        print(f"required_num_svc in {cid}: {required_num_svc}")
    complete_traces = dict()
    for cid in all_traces:
        if cid not in complete_traces:
            complete_traces[cid] = dict()
        for tid in all_traces[cid]:
            if len(all_traces[cid][tid]) == required_num_svc:
                complete_traces[cid][tid] = all_traces[cid][tid]
    for cid in all_traces:
        print(f"len(all_traces[{cid}]): {len(all_traces[cid])}")
    for cid in complete_traces:
        print(f"len(complete_traces[{cid}]): {len(complete_traces[cid])}")
    return complete_traces


def training_phase(trace_file_name, directory):
    global coef_dict
    # global endpoint_level_inflight
    # global endpoint_level_rps
    global placement
    global all_endpoints
    global endpoint_to_cg_key
    global sp_callgraph_table
    global ep_str_callgraph_table
    # global traffic_segmentation
    # global objective
    
    '''Option 1: Generate dummy traces'''
    # complete_traces = gen_trace.run(cfg.NUM_CLUSTER, num_traces=10)
    
    '''Option 2: Read trace string file'''
    ts = time.time()
    complete_traces = trace_string_file_to_trace_data_structure(trace_file_name)
    for cid in complete_traces:
        print(f"len(complete_traces[{cid}]): {len(complete_traces[cid])}")
    print(f"FILE ==> DATA STRUCTURE: {int(time.time()-ts)} seconds")
    '''Time stitching'''
    stitched_traces = tst.stitch_time(complete_traces)
    
    # stitched_df = tst.trace_to_df(stitched_traces)
    # print(f"len(stitched_df): {len(stitched_df)}")
    # stitched_df = stitched_df.loc[stitched_df['rt'] > 0]
    # stitched_df = stitched_df.loc[stitched_df['xt'] > 0]
    # print(f"after negative xt filter, len(stitched_df): {len(stitched_df)}")
    
    for cid in stitched_traces:
        print(f"len(stitched_traces[{cid}]): {len(stitched_traces[cid])}")
    
    '''Create useful data structures from the traces'''
    sp_callgraph_table = tst.traces_to_span_callgraph_table(stitched_traces)
    endpoint_to_cg_key = tst.get_endpoint_to_cg_key_map(stitched_traces)
    ep_str_callgraph_table = tst.traces_to_endpoint_str_callgraph_table(stitched_traces)
    print("ep_str_callgraph_table")
    print(f"num different callgraph: {len(ep_str_callgraph_table)}")
    for cg_key in ep_str_callgraph_table:
        print(f"{cg_key}: {ep_str_callgraph_table[cg_key]}")
    all_endpoints = tst.get_all_endpoints(stitched_traces)
    # for cid in all_endpoints:
    #     for svc_name in all_endpoints[cid]:
    #         print(f"all_endpoints[{cid}][{svc_name}]: {all_endpoints[cid][svc_name]}")
    if cfg.OUTPUT_WRITE:
        tst.file_write_callgraph_table(sp_callgraph_table)
    placement = tst.get_placement_from_trace(stitched_traces)
    for cid in placement:
        print(f"placement[{cid}]: {placement[cid]}")
    
    
    '''
    Train linear regression model
    The linear regression model is function of "inflight_req"
    '''
    coef_dict = train_latency_function_with_trace(stitched_traces, trace_file_name, directory)
    
    print("coef_dict before checking")
    for svc_name in coef_dict:
        for ep_str in coef_dict[svc_name]:
            print(f'coef_dict[{svc_name}][{ep_str}]: {coef_dict[svc_name][ep_str]}')
    
    # NOTE: latency function should be strictly increasing function
    for svc_name in coef_dict: # svc_name: metrics-db
        for ep_str in coef_dict[svc_name]: # ep_str: metrics-db@GET@/dbcall
            for feature_ep in coef_dict[svc_name][ep_str]: # feature_ep: 'metrics-db@GET@/dbcall' or 'intercept'
                if feature_ep != "intercept": # a in a*(x^degree) + b
                    if coef_dict[svc_name][ep_str][feature_ep] < 0:
                        coef_dict[svc_name][ep_str][feature_ep] = 0
                        # coef_dict[svc_name][ep_str]['intercept'] = 1
                        print(f"WARNING!!!: coef_dict[{svc_name}][{ep_str}] coefficient is negative. Set it to 0.")
                    else: 
                        if coef_dict[svc_name][ep_str]['intercept'] < 0:
                            # a is positive but intercept is negative
                            coef_dict[svc_name][ep_str]['intercept'] = 1
                            print(f"WARNING: coef_dict[{svc_name}][{ep_str}], coefficient is positive.")
                            print(f"WARNING: But, coef_dict[{svc_name}][{ep_str}], intercept is negative. Set it to 0.")
    print("coef_dict after checking")
    for svc_name in coef_dict:
        for ep_str in coef_dict[svc_name]:
            print(f'coef_dict[{svc_name}][{ep_str}]: {coef_dict[svc_name][ep_str]}')
            


def merge_slatelog_files(directory):
    """
    Merges all .slatelog files found within the specified directory and its subdirectories
    into a single file named merged.slatelog.

    Args:
    directory (str): The path to the directory to search for .slatelog files.
    """
    output_filename = "merged.slatelog"
    
    # Find all .slatelog files within the specified directory, including subdirectories
    slatelog_files = glob.glob(os.path.join(directory, '**', '*.slatelog'), recursive=True)
    
    # Merge the contents of these files into the specified output file
    with open(output_filename, 'w') as outfile:
        for fname in slatelog_files:
            with open(fname) as infile:
                outfile.write(infile.read())
    return output_filename

def run(directory):
    assert directory != ""
    merged_trace_file_name = merge_slatelog_files(directory)
    print(f"merged_trace_file_name: {merged_trace_file_name}")
    training_phase(merged_trace_file_name, directory)
    return merged_trace_file_name
  
if __name__ == "__main__":
    directory = sys.argv[1]
    if len(sys.argv) < 2:
        print("Usage: python run_optimizer.py <directory>")
        exit()
    merged_trace_file_name = merge_slatelog_files(directory)
    print(f"merged_trace_file_name: {merged_trace_file_name}")
    training_phase(merged_trace_file_name, directory)
