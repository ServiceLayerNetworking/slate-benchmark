#!/usr/bin/env python
# coding: utf-8

# In[31]:
import sys
sys.dont_write_bytecode = True

import time
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import random
import gurobipy_pandas as gppd
from gurobi_ml import add_predictor_constr
from IPython.display import display
import config as cfg
import optimizer_header as opt_func
import time_stitching as tst
import os
from IPython.display import display
import itertools
from pprint import pprint

random.seed(1234)

'''
For interactive run with jupyternotebook, comment out following lines "COMMENT_OUT_FOR_JUPYTER".
And adjust the indentation accordingly.
'''

# pre_recorded_trace is simply a list of spans?
'''
NUM_REQUESTS = {cid_0: {"cg_1": rps, "cg_2": rps}, 
                cid_1: {"cg_1": rps, "cg_2": rps}}

cg_key = bfs_callgraph and append svc_name, method, url

ep_str_callgraph_table[cg_key][parent_ep_str] = list of child_ep_str

sp_callgraph_table[cg_key][parent_'span'] = list of child_'span'

request_in_out_weight[cg_key][parent_ep_str][child_ep_str] = in_/out_ ratio

latency_func[svc_name][endpoint] = fitted regression model

endpoint_level_inflight_req[cid][svc_name][ep] = #inflight req

endpoint_level_rps[cid][svc_name][ep] = rps

root_node_max_rps[root_node_endpoint] = rps

all_endpoints[cid][svc_name][ep] = endpoint

placement[cid] = span.svc_name

svc_to_placement[svc_name] = set of cids

endpoint_to_placement[ep] = set of cids

traffic_segmentation = True/False

objective = "avg_latency"/"end_to_end_latency"/"egress_cost"/"multi_objective"
'''
def run_optimizer(coef_dict, endpoint_level_inflight_req, endpoint_level_rps, placement, all_endpoints, endpoint_to_cg_key, sp_callgraph_table, ep_str_callgraph_table, traffic_segmentation, objective):
    for cid in endpoint_level_rps:
        for svc_name in endpoint_level_rps[cid]:
            for ep in endpoint_level_rps[cid][svc_name]:
                    print(f'cid: {cid}, svc_name: {svc_name}, ep: {ep}')
                    print(f'{endpoint_level_rps[cid][svc_name][ep]}')
    root_ep = dict()
    for cg_key in ep_str_callgraph_table:
        root_ep[cg_key] = opt_func.find_root_node(ep_str_callgraph_table[cg_key])
    for cg_key in root_ep:
        print(f'root_span: {root_ep[cg_key]}')
            
    def get_root_node_rps(endpoint_level_rps, root_ep):
        root_node_rps = dict()
        for cid in endpoint_level_rps:
            if cid not in root_node_rps:
                root_node_rps[cid] = dict()
            for svc_name in endpoint_level_rps[cid]:
                for ep in endpoint_level_rps[cid][svc_name]:
                    for cg_key in root_ep:
                        if ep == root_ep[cg_key]:
                            root_node_rps[cid][ep] = endpoint_level_rps[cid][svc_name][ep]
        return root_node_rps
    
    root_node_rps = get_root_node_rps(endpoint_level_rps, root_ep)

    def collapse_cid_in_endpoint_level_rps(endpoint_level_rps):
        collapsed_endpoint_level_rps = dict()
        for cid in endpoint_level_rps:
            for svc_name in endpoint_level_rps[cid]:
                for ep in endpoint_level_rps[cid][svc_name]:
                    if svc_name not in collapsed_endpoint_level_rps:
                        collapsed_endpoint_level_rps[svc_name] = dict()
                    if ep not in collapsed_endpoint_level_rps[svc_name]:
                        collapsed_endpoint_level_rps[svc_name][ep] = 0
                    collapsed_endpoint_level_rps[svc_name][ep] += endpoint_level_rps[cid][svc_name][ep]
        return collapsed_endpoint_level_rps
    
    collapsed_endpoint_level_rps = collapse_cid_in_endpoint_level_rps(endpoint_level_rps)
    
    # This is used in flow_conservation-nonleaf_endnode constraint
    request_in_out_weight = dict()
    for cg_key in sp_callgraph_table:
        if cg_key not in request_in_out_weight:
            request_in_out_weight[cg_key] = dict()
        span_cg = sp_callgraph_table[cg_key]
        for parent_span in span_cg:
            parent_ep_str = str(parent_span.endpoint)
            if parent_ep_str not in request_in_out_weight[cg_key]:
                request_in_out_weight[cg_key][parent_ep_str] = dict()
            for child_span in span_cg[parent_span]:
                child_ep_str = str(child_span.endpoint)
                if child_ep_str not in request_in_out_weight[cg_key][parent_ep_str]:
                    request_in_out_weight[cg_key][parent_ep_str][child_ep_str] = dict()
                in_ = collapsed_endpoint_level_rps[parent_span.svc_name][parent_ep_str]
                out_ = collapsed_endpoint_level_rps[child_span.svc_name][child_ep_str]
                ###################################################################
                # TODO
                # request_in_out_weight[cg_key][parent_ep_str][child_ep_str] = in_/out_
                request_in_out_weight[cg_key][parent_ep_str][child_ep_str] = 1
                ###################################################################
    # pprint(request_in_out_weight)
    
    ##############################################
    # TODO: Problem: how should we the endpoint to each call graph? Otherwise, by simply using the endpoint, we are not able to find root endpoint of the call graph.
    # norm_inout_weight = dict()
    # for cg_key in request_in_out_weight:
    #     norm_inout_weight[cg_key] = opt_func.norm(request_in_out_weight[cg_key], root_endpoint[cg_key].endpoint)
    # merged_in_out_weight = opt_func.merge(request_in_out_weight, norm_inout_weight, MAX_LOAD)
    # norm_merged_in_out_weight = opt_func.norm(merged_in_out_weight, root_endpoint[cg_key].svc_name)
    ##############################################
    
    if traffic_segmentation == False:
        print(f'further implementation is required for traffic_segmentation False')
        assert False
        original_NUM_REQUESTS = NUM_REQUESTS.copy()
        original_MAX_LOAD = MAX_LOAD.copy()
        original_callgraph = callgraph.copy()
        original_request_in_out_weight = request_in_out_weight.copy()
        merged_cg_key = "M"
        merged_callgraph = opt_func.merge_callgraph(callgraph)
        callgraph = dict()
        callgraph[merged_cg_key] = merged_callgraph
        request_in_out_weight = dict()
        request_in_out_weight[merged_cg_key] = merged_in_out_weight
        norm_inout_weight = dict()
        norm_inout_weight[merged_cg_key] = norm_merged_in_out_weight
        merged_NUM_REQUESTS = list()
        for num_req in NUM_REQUESTS:
            merged_NUM_REQUESTS.append({merged_cg_key: sum(num_req.values())})
        NUM_REQUESTS = list()
        NUM_REQUESTS = merged_NUM_REQUESTS
        MAX_LOAD = opt_func.get_max_load(NUM_REQUESTS)
        
    # print(f'NUM_REQUESTS: {NUM_REQUESTS}')
    # print(f'MAX_LOAD: {MAX_LOAD}')
    # print(f'placement: {placement}')
    # print(f'callgraph: {callgraph}')
    # print(f'request_in_out_weight: {request_in_out_weight}')
    # print(f'norm_inout_weight: {norm_inout_weight}')
    # print(f'merged_in_out_weight: {merged_in_out_weight}')
    # print(f'norm_merged_in_out_weight: {norm_merged_in_out_weight}')


    # In[31]:

    # key: cg key, value: dict of {svc: depth}
    depth_dict = dict()
    for cg_key in ep_str_callgraph_table:
        depth_dict[cg_key] = opt_func.get_depth_in_graph(ep_str_callgraph_table[cg_key])
    # print("depth_dict")
    # print(depth_dict)
    # key: (parent_svc,child_svc), value: callsize of the link (= depth+1)
    callsize_dict = dict()
    for cg_key in ep_str_callgraph_table:
        callsize_dict[cg_key] = opt_func.get_callsize_dict(ep_str_callgraph_table[cg_key], depth_dict[cg_key])
    # print(f'callsize_dict: {callsize_dict}')

    # In[31]:
    
    root_node_max_rps = opt_func.get_root_node_max_rps(root_node_rps)
    compute_arc_var_name = opt_func.create_compute_arc_var_name(all_endpoints)
    opt_func.check_compute_arc_var_name(compute_arc_var_name)
    compute_df = opt_func.create_compute_df(compute_arc_var_name, ep_str_callgraph_table, coef_dict)
    if cfg.OUTPUT_WRITE:
        compute_df.to_csv('compute_df.csv')
    if traffic_segmentation == False:
        original_compute_df = opt_func.create_compute_df(placement, original_callgraph, callsize_dict, original_NUM_REQUESTS, original_MAX_LOAD)
        # display(original_compute_df)
        
    # for svc_name in latency_function:
    #     for ep in latency_function[svc_name]:
    #         # first elem is the first coef for the first endpiont, the second coef is for the second endpoint used to predict the endpoint latency
    #         # print(f'latency_function[{svc_name}][{ep}]: {latency_function[svc_name][ep]}')
    #         print(f'latency_function[{svc_name}][{ep}], coef: {latency_function[svc_name][ep]["linearregression"].coef_}')
    #         print(f'latency_function[{svc_name}][{ep}], intercept: {latency_function[svc_name][ep]["linearregression"].intercept_}')
        


    # In[42]:

    gurobi_model = gp.Model('RequestRouting')

    ''' 
    Create new gurobi variables
    
    How does adding gurobi variables work in gppd(gurobi pandas)?
    It takes index only from the dataframe and create variables for each index with the given prefix by name parameter.
    example: load_for_network_edge_A[('productpage_v1#0#end',_'reviews_v3#0#start')]
    example: compute_latency_A[('productpage_v1#1#start',_'productpage_v1#1#end')]
    
    example: compute_latency[('A,GET,read#0#start',_'A,GET,read#0#end')]
    
    example: load_for_compute_edge[('A,GET,read#0#start',_'A,GET,read#0#end')]

    
    ('aaa', 'bbb') is a tuple, and it is the index of the dataframe.
    '''
    # compute_latency = dict()
    # compute_load = dict()
    compute_latency = gppd.add_vars(gurobi_model, compute_df, name="compute_latency", lb="min_compute_latency")
    compute_load = gppd.add_vars(gurobi_model, compute_df, name="load_for_compute_edge")
    compute_load2 = gppd.add_vars(gurobi_model, compute_df, name="load_for_compute_edge2")
    for index, row in compute_df.iterrows():
        gurobi_model.addConstr(compute_load2[index] == compute_load[index]**2, name=f'for_higher_degree-{index}')
        print(f"addConstr, compute_load2[{index}] == compute_load[{index}]**2")
    gurobi_model.update()
    
    # # In[44]:


    '''
    Original latency function constraint
    
    It uses gurobi add_predictor_constr
    '''
    # for index, row in compute_df.iterrows():
    #     data = dict()
    #     for key in callgraph:
    #         data["observed_x_"+key] = compute_load[key][index]
    #     m_feats = pd.DataFrame(
    #         data=data,
    #         index=[index]
    #     )
    #     for key in callgraph:
    #         print(f'callgraph key: {key}')
    #         print(f'{row["svc_name"]}')
    #         print(f'index: {index}')
    #         print(f'm_feats: {m_feats}')
    #         print(f'{compute_latency[key][index]}')
    #         print(f'{row["latency_function_"+key]}')
    #         print()
    #         # (gurobi_model, regression model, x, y)
    #         pred_constr = add_predictor_constr(gurobi_model, row["latency_function_"+key], m_feats, compute_latency[key][index])
    
    '''
    Manually setting the latency function constraint
    
    coef[ep_1] = latency_function[svc_A][ep_1]["linearregression"].coef_[0]
    coef[ep_2] = latency_function[svc_A][ep_1]["linearregression"].coef_[1]
    intercept = latency_function[svc_A][ep_1]["linearregression"].intercept_
    
    Constraint equation:
        endpoint latency == (coef[ep_1]*scheduled_load[ep_1]) + (coef[ep_2]*scheduled_load[ep_2]) + intercept
    
    '''
    for index, row in compute_df.iterrows():
        lh = compute_latency[index]
        rh = 0
        coefs = row['coef']
        # print(f"target svc,endpoint: {row['svc_name']}, {row['endpoint']}")
        # print(coefs)
        for dependent_ep in coefs:
            if dependent_ep != 'intercept':
                dependent_arc_name = opt_func.get_compute_arc_var_name(dependent_ep, row['src_cid'])
                # print(f'dependent_arc_name: {dependent_arc_name}')
                # print(f'coefs[{dependent_ep}]: {coefs[dependent_ep]}')
                # print(f'dependent_arc_name: {dependent_arc_name}')
                try:
                    # rh += coefs[dependent_ep] * compute_load[dependent_arc_name]
                    rh += coefs[dependent_ep] * (compute_load2[dependent_arc_name]**2)
                except Exception as e:
                    print(f'Exception: {e}')
                    print(f'compute_load2[{dependent_arc_name}]: {compute_load2[dependent_arc_name]}')
                    print(f'coefs[{dependent_ep}]: {coefs[dependent_ep]}')
                    assert False
        rh += coefs['intercept']
        # print(f"index: {index}")
        # print(f"lh: {lh}")
        # print(f"rh: {rh}")
        gurobi_model.addConstr(lh == rh, name=f'latency_function_{index}')
    gurobi_model.update()


    # In[44]:


    endpoint_to_placement = dict()
    svc_to_placement = dict()
    for cid in all_endpoints:
        for svc_name in all_endpoints[cid]:
            if svc_name not in svc_to_placement:
                svc_to_placement[svc_name] = set()
            svc_to_placement[svc_name].add(cid)
            for ep in all_endpoints[cid][svc_name]:
                if ep not in endpoint_to_placement:
                    endpoint_to_placement[ep] = set()
                endpoint_to_placement[ep].add(cid)
    # print('endpoint_to_placement')
    # print(f'{endpoint_to_placement}')
    # print('svc_to_placement')
    # print(f'{svc_to_placement}')
    ## Define names of the variables for network arc in gurobi
    # endpoint_to_placement: 
    # {'A,POST,post': {0, 1}, 'A,GET,read': {0, 1}, 'B,GET,read': {0, 1}, 'C,POST,post': {0, 1}}
    network_arc_var_name = list()
    for cg_key in ep_str_callgraph_table:
        for parent_ep_str in ep_str_callgraph_table[cg_key]:
            for child_ep_str in ep_str_callgraph_table[cg_key][parent_ep_str]:
                for p_cid in endpoint_to_placement[parent_ep_str]:
                    for c_cid in endpoint_to_placement[child_ep_str]:
                        # print(f'parent_ep_str: {parent_ep_str}, p_cid: {p_cid}, child_ep_str: {child_ep_str}, c_cid: {c_cid}')
                        var_name = opt_func.get_network_arc_var_name(parent_ep_str, child_ep_str, p_cid, c_cid)
                        if var_name not in network_arc_var_name:
                            network_arc_var_name.append(var_name)

    for cg_key in ep_str_callgraph_table:
        root_node = opt_func.find_root_node(ep_str_callgraph_table[cg_key])
        # print(f"endpoint_to_placement[{root_node}]")
        # print(f"{endpoint_to_placement[root_node]}")
        for dst_cid in endpoint_to_placement[root_node]:
            # print(f'root_node: {root_node}')
            # print(f'dst_cid, {dst_cid}')
            var_name = opt_func.get_network_arc_var_name(opt_func.source_node_name, root_node, opt_func.NONE_CID, dst_cid)
            network_arc_var_name.append(var_name)
    
    # network_arc_var_name = opt_func.create_network_arc_var_name(endpoint_to_placement)
    # opt_func.check_network_arc_var_name(network_arc_var_name)


    # In[36]:

    columns=["src_svc", "src_cid", "dst_svc", "dst_cid", "min_network_time", "max_network_time", "max_load", "min_load", "min_egress_cost", "max_egress_cost"]
    network_df = pd.DataFrame(
        columns=columns,
        data={
        },
        index=network_arc_var_name
    )

    # In[36]:


    src_svc_list = list()
    dst_svc_list = list()
    src_cid_list = list()
    dst_cid_list = list()
    min_network_time_list = list()
    max_network_time_list = list()
    min_egress_cost_list = list()
    max_egress_cost_list = list()
    flattened_callsize_dict = {inner_key: value for outer_key, inner_dict in callsize_dict.items() for inner_key, value in inner_dict.items()}
    # print(f'callsize_dict: {callsize_dict}')
    # print(f'flattened_callsize_dict: {flattened_callsize_dict}')
    for var_name in network_arc_var_name:
        # print(var_name)
        if type(var_name) == tuple:
            src = var_name[0].split(cfg.DELIMITER)[0]
            dst = var_name[1].split(cfg.DELIMITER)[0]
            # src_cid = int(var_name[0].split(cfg.DELIMITER)[1])
            # dst_cid = int(var_name[1].split(cfg.DELIMITER)[1])
            src_cid = var_name[0].split(cfg.DELIMITER)[1]
            dst_cid = var_name[1].split(cfg.DELIMITER)[1]
        else:
            print("var_name MUST be tuple datatype")
            assert False
        src_svc_list.append(src)
        dst_svc_list.append(dst)
        src_cid_list.append(src_cid)
        dst_cid_list.append(dst_cid)
        n_time = opt_func.get_network_latency(src_cid, dst_cid)
        min_network_time_list.append(n_time)
        max_network_time_list.append(n_time)
        e_cost = opt_func.get_egress_cost(src, src_cid, dst, dst_cid, flattened_callsize_dict)
        min_egress_cost_list.append(e_cost)
        max_egress_cost_list.append(e_cost)
        
    network_df["src"] = src_svc_list
    network_df["dst"] = dst_svc_list
    network_df["src_cid"] = src_cid_list
    network_df["dst_cid"] = dst_cid_list
    network_df["min_network_time"] = min_network_time_list
    network_df["max_network_time"] = max_network_time_list
    # for index, row in network_df.iterrows():
    #     network_df.at[index, 'max_load'] = MAX_LOAD[key]
    #     if row["src_svc"] == opt_func.source_node_name:
    #         network_df.at[index, 'max_load'] = MAX_LOAD[key]
    #     else:
    #         network_df.at[index, 'max_load'] = 0
    #     network_df.at[index, 'min_load'] = 0
    network_df["min_egress_cost"] = min_egress_cost_list
    network_df["max_egress_cost"] = max_egress_cost_list
    if cfg.OUTPUT_WRITE:
        network_df.to_csv('network_df.csv')

    # In[44]:


    network_latency = dict()
    network_load = dict()
    network_egress_cost = dict()
    network_latency = gppd.add_vars(gurobi_model, network_df, name="network_latency", lb="min_network_time", ub="max_network_time")
    network_load = gppd.add_vars(gurobi_model, network_df, name="load_for_network_edge")
    network_egress_cost = gppd.add_vars(gurobi_model, network_df, name="network_egress_cost", lb="min_egress_cost", ub="max_egress_cost")
    gurobi_model.update()


    # In[44]:


    # if objective == "avg_latency":
    network_latency_sum = 0
    compute_latency_sum = 0
    network_latency_sum += sum(network_latency.multiply(network_load))
    compute_latency_sum += sum(compute_latency.multiply(compute_load))
    total_latency_sum = network_latency_sum + compute_latency_sum

    # if objective == "egress_cost":
    network_egress_cost_sum = 0
    network_egress_cost_sum += sum(network_egress_cost.multiply(network_load))
    
    # compute_egress_cost = dict()
    # compute_egress_cost = gppd.add_vars(gurobi_model, compute_df, name="compute_egress_cost", lb="min_egress_cost", ub="max_egress_cost")
    # compute_egress_cost_sum = sum(compute_egress_cost.multiply(compute_load))
    # print("compute_egress_cost_sum")
    # print(compute_egress_cost_sum)

    ## compute edge egress cost is always 0
    # total_egress_sum = network_egress_cost_sum + compute_egress_cost_sum
    total_egress_sum = network_egress_cost_sum
    gurobi_model.update()
    
    # print("network_latency_sum")
    # print(network_latency_sum)
    # print()
    # print("compute_latency_sum")
    # print(compute_latency_sum)
    # print()
    # print("total_latency_sum")
    # print(total_latency_sum)
    # print()
    # print("network_egress_cost_sum")
    # print(network_egress_cost_sum)
    # print()
    # print("total_egress_sum")
    # print(total_egress_sum)
    # print()

    
    if objective == "end_to_end_latency":
        svc_order = dict()
        for key in callgraph:
            assert key not in svc_order
            svc_order[key] = dict()
            opt_func.get_svc_order(callgraph, key, "ingress_gw", svc_order, idx=0)
        for key in svc_order:
            print(f'svc_order[{key}]: {svc_order[key]}')

        svc_to_placement = dict()
        all_combinations = dict()
        new_all_combinations = dict()
        for key in callgraph:
            svc_to_placement[key] = opt_func.svc_to_cid(svc_order[key], placement)
            print(f'svc_to_placement[{key}]: {svc_to_placement[key]}')
            all_combinations[key] = list(itertools.product(*svc_to_placement[key]))
            new_all_combinations[key] = opt_func.remove_too_many_cross_cluster_routing_path(all_combinations[key], 1)
            # for comb in new_all_combinations[key]:
            #     print(f'comb: {comb}')
            #     break
            
        assert svc_order.keys() == new_all_combinations.keys()

        root_node = dict()
        for key in callgraph:
            root_node[key] = opt_func.find_root_node(callgraph, "A")
        print(f'root_node: {root_node}')

        unpack_list = dict()
        for key in callgraph:
            unpack_list[key] = list()
            opt_func.unpack_callgraph(callgraph, key, root_node[key], unpack_list[key])
        for key in unpack_list:
            print(f'unpack_list[{key}]: {unpack_list[key]}')

        print()
        path_dict = dict()
        for key in svc_order:
            path_dict[key] = dict()
            for comb in new_all_combinations[key]:
                # return type of create_path: list (path is a list)
                path = opt_func.create_path(svc_order[key], comb, unpack_list[key], callgraph, key)
                path_dict[key][comb] = path

        print()
        for key in path_dict:
            for comb, path in path_dict[key].items():
                print(f'{comb} path in path_dict[{key}]')
                for pair in path:
                    print(f'{pair}')
                print()
            
        possible_path = dict()
        for key in callgraph:
            possible_path[key] = dict()
            for comb in new_all_combinations[key]:
                print(f'key: {key}, comb: {comb}')
                possible_path[key][comb] = list()

        print()
        end_to_end_path_var = dict()
        for key in path_dict:
            end_to_end_path_var[key] = dict()
            for comb, path in path_dict[key].items():
                print(f'comb: {comb}')
                # end_to_end_path_var[key][comb] = gurobi_model.addVar(vtype=gp.GRB.CONTINUOUS, name=f'end_to_end_path_var_{key}_{comb}')
                end_to_end_path_var[key][comb] = 0
                for pair in path:
                    if opt_func.is_network_var(pair):
                        try:
                            # print(f'network_latency[{key}][{pair}]: {network_latency[key][pair]}')
                            # end_to_end_path_var[key][comb].append(network_latency[key][pair])
                            end_to_end_path_var[key][comb] += network_latency[key][pair]
                        except Exception as e:
                            print(f'network_latency, key: {key}, pair: {pair}')
                            print(f'Exception: {e}')
                            assert False
                    else:
                        try:
                            # print(f'compute_latency[{key}][{pair}]: {compute_latency[key][pair]}')
                            # end_to_end_path_var[key][comb].append(compute_latency[key][pair])
                            end_to_end_path_var[key][comb] += compute_latency[key][pair]
                            print(f'compute_latency[{key}][{pair}]: {compute_latency[key][pair]}')
                        except Exception as e:
                            print(f'compute_latency[{key}][{pair}]: {compute_latency[key][pair]}')
                            print(f'Exception: {e}')
                            assert False
        gurobi_model.update()
        print()
        for key in end_to_end_path_var:
            for comb in end_to_end_path_var[key]:
                print(f'key: {key}, comb: {comb}')
                # for var in end_to_end_path_var[key][comb]:
                print(f'{end_to_end_path_var[key][comb]}')
                print()
                
        '''
        reference: https://www.gurobi.com/documentation/current/refman/py_model_agc_max.html#pythonmethod:Model.addGenConstrMax
        # gurobi_model.addGenConstrMax(resvar=max_end_to_end_latency, vars=end_to_end_path_list, name="maxconstr")
        '''
        max_end_to_end_latency = gurobi_model.addVar(name="max_end_to_end_latency", lb=0)
        # end_to_end_path_list = list()
        for key in end_to_end_path_var:
            for comb in end_to_end_path_var[key]:
                # end_to_end_path_list.append(end_to_end_path_var[key][comb])
                gurobi_model.addConstr(end_to_end_path_var[key][comb] <= max_end_to_end_latency, name=f'maxconstr_{key}_{comb}')
                print(f'end_to_end_path_var[{key}][{comb}]: {end_to_end_path_var[key][comb]}')
                print(f'<=')
                print(f'max_end_to_end_latency')
        gurobi_model.update()

        print('max_end_to_end_latency')
        print(f'{max_end_to_end_latency}\n')

    # In[44]:

    if objective == "avg_latency":
        gurobi_model.setObjective(total_latency_sum, gp.GRB.MINIMIZE)
    elif objective == "end_to_end_latency":
        gurobi_model.setObjective(max_end_to_end_latency, gp.GRB.MINIMIZE)
    elif objective == "egress_cost":
        gurobi_model.setObjective(total_egress_sum, gp.GRB.MINIMIZE)
    elif objective == "multi_objective":
        # NOTE: higher dollar per ms, more important the latency
        # DOLLAR_PER_MS: value of latency
        # lower dollar per ms, less tempting to re-route since bandwidth cost is becoming more important
        # simply speaking, when we have DOLLAR_PER_MS decreased, less offloading.
        gurobi_model.setObjective(total_latency_sum*cfg.DOLLAR_PER_MS + total_egress_sum, gp.GRB.MINIMIZE)
    else:
        print("unsupported objective, ", objective)
        assert False
        
    gurobi_model.update()
    # print(f"{cfg.log_prefix} model objective")
    # print(f"{gurobi_model.getObjective()}\n")


    # In[44]:


    temp = dict()
    temp = pd.concat([network_load, compute_load], axis=0)
    # concat_df = pd.concat(temp, axis=0)
    # print("type(concat_df): ", type(concat_df))
    # print("concat_df.to_dict()")
    # concat_dict = concat_df.to_dict()
    # for k, v in concat_dict.items():
        # print(f"key: {k}\nvalue: {v}")
    # print()
    arcs = dict()
    aggregated_load = dict()
    arcs, aggregated_load = gp.multidict(temp.to_dict())
    if cfg.DISPLAY:
        # print("arcs")
        # print(f'{arcs}\n')
        # print("aggregated_load")
        # print(f'{aggregated_load}\n')
        print("aggregated_load")
        # print(type(aggregated_load))
        for k, v in aggregated_load.items():
            print(f"key: {k}\nvalue: {v}")
            print()
        
    opt_func.log_timestamp("gurobi add_vars and set objective")


    # In[45]:

    print("endpoint_level_rps")
    print(endpoint_level_rps)
    # print(endpoint_level_inflight_req)
    ## Constraint 1: SOURCE
    if cfg.LOAD_IN:
        total_coming = 0
        for cg_key in sp_callgraph_table:
            root_span = opt_func.find_root_node(sp_callgraph_table[cg_key])
            # prin(f'cg_key: {cg_key}')
            for cid in placement:
                if root_span.svc_name in placement[cid]:
                    # prin(f'endpoint_level_rps[{cid}][{root_span.svc_name}]')
                    # prin(f'[{root_span.endpoint_str}]: {endpoint_level_rps[cid][root_span.svc_name][root_span.endpoint_str]}')
                    incoming = endpoint_level_rps[cid][root_span.svc_name][root_span.endpoint_str]
                    # incoming += endpoint_level_inflight_req[cid][root_span.svc_name][root_span.endpoint_str]
                    # prin(f"incoming: {incoming}")
                    total_coming += incoming
                    
                    
                    # ingress_gw_start_node = f'{svc}{cfg.DELIMITER}{cid}{cfg.DELIMITER}start'
                    node_name = f'{root_span.endpoint_str}{cfg.DELIMITER}{cid}{cfg.DELIMITER}start'
                    # prin(f'node_name: {node_name}')
                    lh = gp.quicksum(aggregated_load.select('*', node_name))
                    rh = incoming
                    gurobi_model.addConstr((lh == rh), name="cluster_"+str(cid)+"_load_in_"+str(root_span.endpoint_str))
                    if cfg.DISPLAY:
                        print(lh)
                        print("==")
                        print(rh)
                        print("-"*80)
        
        # prin("*"*80)
        # prin(aggregated_load.select(opt_func.source_node_fullname, '*'))
        # prin("==")
        # prin(total_coming)
        gurobi_model.addConstr((gp.quicksum(aggregated_load.select(opt_func.source_node_fullname, '*')) == total_coming), name="source")
        # prin("*"*80)
                
        gurobi_model.update()


    # In[47]:

    ## Constraint 2: destination
    # destination = dict()
    # destination[opt_func.destination_node_fullname] = MAX_LOAD
    # dest_keys = destination.keys()
    # leaf_services = list()
    # for parent_svc, children in callgraph.items():
    #     if len(children) == 0: # leaf service
    #         leaf_services.append(parent_svc)
    # num_leaf_services = len(leaf_services)
    # print(f"{cfg.log_prefix} num_leaf_services: {num_leaf_services}")
    # print(f"{cfg.log_prefix} leaf_services: {leaf_services}")
    # dst_flow = gurobi_model.addConstrs((gp.quicksum(aggregated_load.select('*', dst)) == destination[dst]*num_leaf_services for dst in dest_keys), name="destination")
    # for dst in dest_keys:
    #     print(aggregated_load.select('*', dst))
    # gurobi_model.update()


    # In[47]:

    ## Constraint 3: flow conservation
    # Start node in-out flow conservation
    for cid in all_endpoints:
        for svc_name in all_endpoints[cid]:
            for ep_str in all_endpoints[cid][svc_name]:
                # start_node = f'{ep_str}{cfg.DELIMITER}{cid}{cfg.DELIMITER}start'
                start_node = opt_func.get_start_node_name(ep_str, cid)
                lh = gp.quicksum(aggregated_load.select('*', start_node))
                rh = gp.quicksum(aggregated_load.select(start_node, '*'))
                gurobi_model.addConstr((lh == rh), name="flow_conservation-start_node-"+ep_str)
                # prin(lh)
                # prin("==")
                # prin(rh)
                # prin("-"*50)
    gurobi_model.update()
    
    # In[47]:


    # End node in-out flow conservation
    # case 1 (leaf node to destination): incoming num requests == outgoing num request for all nodes
    # for parent_svc, children in callgraph.items():
    #     for cid in range(len(NUM_REQUESTS)):
    #         if len(children) == 0: # leaf_services:
    #             end_node = parent_svc + cfg.DELIMITER + str(cid) + cfg.DELIMITER + "end"
    #             node_flow = gurobi_model.addConstr((gp.quicksum(aggregated_load.select('*', end_node)) == gp.quicksum(aggregated_load.select(end_node, '*'))), name="flow_conservation["+end_node+"]-leaf_endnode")
    #             print("*"*50)
    #             print(aggregated_load.select('*', end_node))
    #             print('==')
    #             print(aggregated_load.select(end_node, '*'))
    #             print("-"*50)
    #             print("*"*50)

    # In[47]:


    # case 2 
    # For non-leaf node and end node, incoming to end node == sum of outgoing
    for cg_key in ep_str_callgraph_table:
        for parent_ep in ep_str_callgraph_table[cg_key]:
            children_ep = ep_str_callgraph_table[cg_key][parent_ep]
            # prin(f'parent_ep: {parent_ep}')
            # non-leaf node will only have child
            for parent_cid in endpoint_to_placement[parent_ep]:
                for child_ep in children_ep:
                # for child_ep in ep_str_callgraph_table[cg_key][parent_ep]:
                    # prin(f'child_ep: {child_ep}')
                    end_node = opt_func.get_end_node_name(parent_ep, parent_cid)
                    # prin(f'non-leaf end_node: {end_node}')
                    outgoing_sum = 0
                    for child_cid in endpoint_to_placement[child_ep]:
                        child_start_node = opt_func.get_start_node_name(child_ep, child_cid)
                        outgoing_sum += aggregated_load.sum(end_node, child_start_node)
                    # if traffic_segmentation:
                        # lh = gp.quicksum(aggregated_load.select('*', end_node))*request_in_out_weight[cg_key][parent_svc][child_svc]
                    # else:
                    #     lh = gp.quicksum(aggregated_load.select('*', end_node))*merged_in_out_weight[parent_svc][child_svc]
                    try:
                        lh = gp.quicksum(aggregated_load.select('*', end_node))*request_in_out_weight[cg_key][parent_ep][child_ep]
                        rh = outgoing_sum
                        gurobi_model.addConstr((lh == rh), name="flow_conservation-nonleaf_endnode-"+cg_key)
                        # prin(lh)
                        # prin('==')
                        # prin(rh)
                        # prin("-"*80)
                    except Exception as e:
                        print(f'Error: {e}')
                        assert False
    gurobi_model.update()

    # In[48]:


    '''
    This constraint also seems redundant.
    The optimizer output varies with and without this constraint. The reason is assumed that there are multiple optimal solutions and how it searches the optimal solution (e.g., order of search exploration) changes with and without this constraint.
    It will be commented out anyway since it it not necessary constraint.
    '''
    ## Constraint 4: Tree topology
    # svc_to_cid = opt_func.svc_to_cid(placement)
    # print("svc_to_cid: ", svc_to_cid)
    # for key in callgraph:
    #     for svc_name in svc_to_cid:
    #         if svc_name != cfg.ENTRANCE and svc_name in callgraph[key]:
    #             incoming_sum = 0
    #             for cid in svc_to_cid[svc_name]:
    #                 start_node = opt_func.start_node_name(svc_name, cid)
    #                 incoming_sum += aggregated_load[key].sum('*', start_node)
    #             node_flow = gurobi_model.addConstr(incoming_sum == MAX_LOAD[key], name="tree_topo_conservation_"+key)
    #             if cfg.DISPLAY:
    #                 print(incoming_sum)
    #                 print('==')
    #                 print(MAX_LOAD[key])
    #                 print("-"*50)
    # gurobi_model.update()


    # In[48]:


    # # Constraint 5: max throughput of service
    # max_tput = dict()
    # for cid in range(len(NUM_REQUESTS)):
    #     for svc_name in placement[cid]:
    #         max_tput[svc_name+cfg.DELIMITER+str(cid)+cfg.DELIMITER+"start"] = MAX_LOAD
    #         max_tput[svc_name+cfg.DELIMITER+str(cid)+cfg.DELIMITER+"end"] = MAX_LOAD
    # print(f"{cfg.log_prefix} max_tput: {max_tput}")
    # max_tput_key = max_tput.keys()
    # throughput = gurobi_model.addConstrs((gp.quicksum(aggregated_load.select('*', n_)) <= max_tput[n_] for n_ in max_tput_key), name="service_capacity")
    # constraint_setup_end_time = time.time()



    # In[51]:

    opt_func.log_timestamp("gurobi add constraints and model update")

    gurobi_key = open("./gurobi.wls", "r")
    options = dict()
    for line in gurobi_key:
        line = line.strip()
        # print("line: ", line)
        if line == "":
            continue
        key, value = line.split(",")
        if key == "LICENSEID":
            value = int(value)
        options[key] = value
    options['OutputFlag'] = 0
    env = gp.Env(params=options)
    gurobi_model = gp.Model('RequestRouting', env=env)
    
    ## When using gurobi.lic license
    # gp.Model()
    
    gurobi_model.update()
    
    # opt_func.print_gurobi_var(gurobi_model)
    # opt_func.print_gurobi_constraint(gurobi_model)
    
    gurobi_model.setParam('NonConvex', 2)
    gurobi_model.optimize()
    solve_end_time = time.time()
    opt_func.log_timestamp("MODEL OPTIMIZE")

    ## Not belonging to optimizer critical path
    ts = time.time()
    varInfo = [(v.varName, v.LB, v.UB) for v in gurobi_model.getVars() ]
    df_var = pd.DataFrame(varInfo) # convert to pandas dataframe
    df_var.columns=['Variable Name','LB','UB'] # Add column headers
    num_var = len(df_var)
    constrInfo = [(c.constrName, gurobi_model.getRow(c), c.Sense, c.RHS) for c in gurobi_model.getConstrs() ]
    df_constr = pd.DataFrame(constrInfo)
    df_constr.columns=['Constraint Name','Constraint equation', 'Sense','RHS']
    num_constr = len(df_constr)
    if cfg.OUTPUT_WRITE:
        df_var.to_csv("variable.csv")
        df_constr.to_csv("constraint.csv")

    substract_time = time.time() - ts
    opt_func.log_timestamp("get var and constraint")

    # opt_func.write_arguments_to_file(NUM_REQUESTS, callgraph, depth_dict, callsize_dict, placement)


    if gurobi_model.Status != GRB.OPTIMAL:
        print(f"{cfg.log_prefix} XXXXXXXXXXXXXXXXXXXXXXXXXXX")
        print(f"{cfg.log_prefix} XXXX INFEASIBLE MODEL! XXXX")
        print(f"{cfg.log_prefix} XXXXXXXXXXXXXXXXXXXXXXXXXXX")
        if cfg.DISPLAY:
            display(df_constr)
        
        gurobi_model.computeIIS()
        gurobi_model.write("gurobi_model.ilp")
        print('\nThe following constraints and variables are in the IIS:')
        # for c in gurobi_model.getConstrs():
        #     if c.IISConstr: print(f'\t{c.constrname}: {gurobi_model.getRow(c)} {c.Sense} {c.RHS}')
        for v in gurobi_model.getVars():
            if v.IISLB: print(f'\t{v.varname} ≥ {v.LB}')
            if v.IISUB: print(f'\t{v.varname} ≤ {v.UB}')
        print("OPTIMIZER, INFEASIBLE MODEL")
        return None
    else:
        print(f"{cfg.log_prefix} ooooooooooooooooooooooo")
        print(f"{cfg.log_prefix} oooo SOLVED MODEL! oooo")
        print(f"{cfg.log_prefix} ooooooooooooooooooooooo")

        ## Print out the result
        optimize_end_time = time.time()
        # optimizer_runtime = round((optimize_end_time - optimizer_start_time) - substract_time, 5)
        # solve_runtime = round(solve_end_time - solve_start_time, 5)
        print(f"{cfg.log_prefix} ** Objective function: {objective}")
        print(f"{cfg.log_prefix} ** Num constraints: {num_constr}")
        print(f"{cfg.log_prefix} ** Num variables: {num_var}")
        # print(f"{cfg.log_prefix} ** Optimization runtime: {optimizer_runtime} ms")
        # print(f"{cfg.log_prefix} ** model.optimize() runtime: {solve_runtime} ms")
        print(f"{cfg.log_prefix} ** model.objVal: {gurobi_model.objVal}")
        # print(f"{cfg.log_prefix} ** gurobi_model.objVal / total num requests: {gurobi_model.objVal/MAX_LOAD}")
        request_flow = pd.DataFrame(columns=["From", "To", "Flow"])
        for arc in arcs:
            if aggregated_load[arc].x > 1e-6:
                temp = pd.DataFrame({"From": [arc[0]], "To": [arc[1]], "Flow": [aggregated_load[arc].x]})
                request_flow = pd.concat([request_flow, temp], ignore_index=True)
        if cfg.OUTPUT_WRITE:
            request_flow.to_csv('request_flow.csv')
        # display(request_flow)
        percentage_df = dict()
        percentage_df = opt_func.translate_to_percentage(request_flow)
        if cfg.OUTPUT_WRITE:
            percentage_df.to_csv('percentage_df.csv')
        opt_func.plot_callgraph_request_flow(percentage_df, network_arc_var_name)
        return percentage_df


        # In[52]:
        
        def update_flow(cur_node, cur_node_cid, inout_weight, cg, actual_req_flow_df, p_df, NUM_REQ, key, incoming_flow):
            if cur_node == opt_func.source_node_name:
                for index, row in p_df.iterrows():
                    if row["src"] == opt_func.source_node_name:
                        new_flow = 0
                        new_flow += NUM_REQ[row['dst_cid']][key]
                        print(f'update_flow, {tup_index_to_str_index(row)},  new_flow: {new_flow}')
                        # print()
                        actual_req_flow_df.loc[tup_index_to_str_index(row), "flow"] += new_flow
                        update_flow(row['dst'], row['dst_cid'], inout_weight, cg, actual_req_flow_df, p_df, NUM_REQ, key, incoming_flow=new_flow)
            else:
                if len(cg[cur_node]) == 0:
                    return
                for child in cg[cur_node]:
                    for index, row in p_df.iterrows():
                        if row['src'] == cur_node and row['dst'] == child and row['src_cid'] == cur_node_cid:
                            new_flow = incoming_flow * inout_weight[row["src"]][row["dst"]]*row['weight']
                            
                            str_index = tup_index_to_str_index(row)
                            
                            print(f'update_flow, {str_index}, incoming_flow: {incoming_flow} new_flow: {round(new_flow, 1)}')
                            # print()
                            actual_req_flow_df.loc[str_index, "flow"] += new_flow
                            update_flow(row['dst'], row['dst_cid'], inout_weight, cg, actual_req_flow_df, p_df,  NUM_REQ, key, incoming_flow=new_flow)
                                
                                
        def update_actual_flow(inout_weight, p_df, cg, actual_req_flow_df, NUM_REQ, key):
            # root_node = opt_func.find_root_node(cg, key)
            root_node = opt_func.source_node_name
            update_flow(root_node, -1, inout_weight, cg, actual_req_flow_df, p_df, NUM_REQ, key, 0)
        
        for key in request_in_out_weight:
            print(f'request_in_out_weight[{key}]: {request_in_out_weight[key]}')
            print(f'norm_inout_weight[{key}]: {norm_inout_weight[key]}')
            print()
        print(f'merged_in_out_weight: {merged_in_out_weight}')
        print()
        
        def tup_index_to_str_index(row):
            return f"{row['src']}, {row['src_cid']}, {row['dst']}, {row['dst_cid']}"
        
        if traffic_segmentation == False:
            assert len(percentage_df) == 1
            for key in percentage_df:
                assert key == merged_cg_key
                new_index = list()
                for index, row in percentage_df[key].iterrows():
                    new_index.append(tup_index_to_str_index(row))
                # print(f'new_index: {new_index}')
            actual_request_flow_df = dict()
            for key in original_request_in_out_weight:
                actual_request_flow_df[key] = pd.DataFrame(columns=percentage_df[merged_cg_key].columns, index=new_index)
                for index, row in percentage_df[merged_cg_key].iterrows():
                    actual_request_flow_df[key].loc[tup_index_to_str_index(row)] = [row["src"], row["dst"], row["src_cid"], row["dst_cid"], 0, 0, row["weight"]]
                    
                # update_actual_flow(request_in_out_weight[key], percentage_df, callgraph, key, actual_request_flow_df)
                print(original_request_in_out_weight)
                update_actual_flow(original_request_in_out_weight[key], percentage_df[merged_cg_key], original_callgraph[key], actual_request_flow_df[key], original_NUM_REQUESTS, key)
                
                print(f'percentage_df[{merged_cg_key}]')
                display(percentage_df[merged_cg_key])
                print(f'actual_request_flow_df[{key}]')
                display(actual_request_flow_df[key])
        

        # In[52]:

        if traffic_segmentation == True and len(request_in_out_weight) > 1:
            concat_df = pd.DataFrame()
            for key in callgraph:
                if concat_df.empty:
                    concat_df = percentage_df[key]
                    continue
                concat_df = pd.concat([concat_df, percentage_df[key]], axis=0,  ignore_index=True)
            for index, row in concat_df.iterrows():
                concat_df.loc[index, "merge_col_1"] = f"{row['src']},{row['src_cid']},{row['dst']}"
                concat_df.loc[index, "merge_col_2"] = f"{row['src']},{row['src_cid']},{row['dst']},{row['dst_cid']}"
            another_group_by_df = concat_df.groupby(['merge_col_2']).sum()
            for index, row in another_group_by_df.iterrows():
                another_group_by_df.at[index, "src"] = index.split(",")[0]
                another_group_by_df.at[index, "src_cid"] = int(index.split(",")[1].split(".")[0])
                another_group_by_df.at[index, "dst"] = index.split(",")[2]
                another_group_by_df.at[index, "dst_cid"] = int(index.split(",")[3].split(".")[0])
                another_group_by_df.at[index, "weight"] = row["flow"]/row["total"]
            print("another_group_by_df")
            display(another_group_by_df)
            
        # for key in callgraph:
        #     opt_func.plot_callgraph_request_flow(percentage_df, [key], network_arc_var_name)
        if cfg.PLOT:
            # if traffic_segmentation == True:
            cg_keys = callgraph.keys()
            opt_func.plot_callgraph_request_flow(percentage_df, cg_keys, workload, network_arc_var_name)
            if traffic_segmentation == False:
                cg_keys = actual_request_flow_df.keys()
                opt_func.plot_callgraph_request_flow(actual_request_flow_df, cg_keys, workload, network_arc_var_name)
            # else:
            #     opt_func.plot_callgraph_request_flow(actual_request_flow_df, cg_keys, workload, network_arc_var_name)
                
            
        if cfg.PLOT and cfg.PLOT_ALL:
            # NOTE: It plots latency function of call graph "A"
            opt_func.plot_latency_function_2d(compute_df, callgraph, "A")
            opt_func.plot_full_arc(compute_arc_var_name, network_arc_var_name, callgraph)
            # for key in callgraph:
            #     opt_func.plot_arc_var_for_callgraph(network_arc_var_name, placement, callgraph, key)
            opt_func.plot_merged_request_flow(another_group_by_df, workload, network_arc_var_name)
            for key in callgraph:
                opt_func.plot_callgraph_request_flow(percentage_df, key, workload, network_arc_var_name)
        
        
        # In[52]:
        
        
        # opt_func.print_all_gurobi_var(gurobi_model)
        lat_ret = dict()
        cost_ret = dict()
        for key in callgraph:
            lat_ret[key] = dict()
            lat_ret[key]["compute"] = 0
            lat_ret[key]["network"] = 0
            cost_ret[key] = 0
            
        for key in callgraph:
            assert compute_latency[key].keys().all() == compute_load[key].keys().all()
            assert network_latency[key].keys().all() == network_load[key].keys().all()
            for k, v in compute_latency[key].items():
                # print(f'compute_latency[{key}][{k}]: {round(compute_latency[key][k].getAttr("X"), 1)}')
                # print(f'compute_load[{key}][{k}]: {round(compute_load[key][k].getAttr("X"), 1)}')
                # print(f'{compute_latency[key][k].getAttr("X")*compute_load[key][k].getAttr("X")}')
                lat_ret[key]["compute"] += compute_latency[key][k].getAttr("X")*compute_load[key][k].getAttr("X")
                
            for k, v in network_latency[key].items():
                # print(f'network_latency[{key}][{k}]: {round(network_latency[key][k].getAttr("X"), 1)}')
                # print(f'network_load[{key}][{k}]: {round(network_load[key][k].getAttr("X"), 1)}')
                # print(f'{network_latency[key][k].getAttr("X")*network_load[key][k].getAttr("X")}')
                lat_ret[key]["network"] += network_latency[key][k].getAttr("X")*network_load[key][k].getAttr("X")
                
            for k, v in network_egress_cost[key].items():
                # print(f'network_egress_cost[{key}][{k}]: {round(network_egress_cost[key][k].getAttr("X"), 1)}')
                # print(f'network_load[{key}][{k}]: {round(network_load[key][k].getAttr("X"), 1)}')
                # print(f'{round(network_egress_cost[key][k].getAttr("X")*network_load[key][k].getAttr("X"), 1)}')
                cost_ret[key] += network_egress_cost[key][k].getAttr("X")*network_load[key][k].getAttr("X")
        total_lat = dict()
        sum_total_lat = dict()
        for key in lat_ret:
            total_lat[key] = 0
            for k, v in lat_ret[key].items(): # k: compute or network
                print(f"{key}: {k}: {round(v,1)}")
                total_lat[key] += v
                if k not in sum_total_lat:
                    sum_total_lat[k] = 0
                sum_total_lat[k] += v
            if MAX_LOAD[key] != 0:
                print(f"{key}: total_avg_latency: {round(total_lat[key], 1)}")
                print(f"{key}: avg_latency: {round(total_lat[key]/MAX_LOAD[key], 1)}")
            else:
                print(f"{key}: total: {total_lat[key]}, MAX_LOAD[{key}] is 0")
            print(f'{key}: total_egress_cost: {round(cost_ret[key], 1)}')
            print()
            
        all_total_e_cost = 0
        all_total_lat = 0
        for key in lat_ret:
            all_total_lat += total_lat[key]
            all_total_e_cost += cost_ret[key]
        for k in sum_total_lat:
            print(f"sum_total_lat: {k}: {round(sum_total_lat[k], 1)}")
        print(f"all_total_avg_lat: {round(all_total_lat, 1)}")
        print(f"all_avg_lat: {round(all_total_lat/sum(MAX_LOAD.values()), 1)}")
        print(f"all_total_e_cost: {round(all_total_e_cost, 1)}")
        print()
        
        print(f"model.objVal: {round(gurobi_model.objVal, 1)}")
        print('*'*70)
        
        
        # In[52]:
        
        
        if traffic_segmentation == False:
            act_tot_network_latency = dict()
            for key in actual_request_flow_df:
                # display(actual_request_flow_df[key])
                act_tot_network_latency[key] = 0
                for index, row in actual_request_flow_df[key].iterrows():
                    act_tot_network_latency[key] += opt_func.get_network_latency(row['src_cid'], row['dst_cid']) * row['flow']
            
            group_by_df = dict()
            for key in actual_request_flow_df:
                # display(actual_request_flow_df[key])
                temp_df = actual_request_flow_df[key].drop(columns=['src', 'src_cid', 'total', 'weight'])
                group_by_df[key] = temp_df.groupby(["dst", "dst_cid"]).sum()
                group_by_df[key] = group_by_df[key].reset_index()
                # display(group_by_df[key])
                
            act_tot_compute_avg_lat = dict()
            for key in group_by_df:
                act_tot_compute_avg_lat[key] = 0
                for index, row in group_by_df[key].iterrows():
                    data = dict()
                    data["observed_x_"+key] = [row["flow"]]
                    for key2 in group_by_df:
                        if key2 != key:
                            for index2, row2 in group_by_df[key2].iterrows():
                                if row2["dst"] == row["dst"] and row2["dst_cid"] == row["dst_cid"]:
                                    data["observed_x_"+key2] = [row2["flow"]]
                                    break
                    temp_df = pd.DataFrame(data=data)
                    # print(f'{row["dst"]}, {row["dst_cid"]}')
                    # display(temp_df)
                    idx = opt_func.get_compute_arc_var_name(row["dst"], row["dst_cid"])
                    lat_f = original_compute_df.loc[[idx]]["latency_function_"+key].tolist()[0]
                    # print(lat_f)
                    pred = lat_f.predict(temp_df)
                    # print(f'pred: {pred}')
                    act_tot_compute_avg_lat[key] += (pred[0] * group_by_df[key].loc[index, "flow"])
                    print(f'{key}, {row["dst"]}, cid, {row["dst_cid"]}: {round(pred[0] * group_by_df[key].loc[index, "flow"], 1)} = {round(pred[0], 1)} x {round(group_by_df[key].loc[index, "flow"], 1)}')
            act_tot_avg_lat = dict()
            for key in act_tot_compute_avg_lat:
                act_tot_avg_lat[key] = act_tot_compute_avg_lat[key] + act_tot_network_latency[key]
            for key in act_tot_avg_lat:
                print(f'{key}: compute: {round(act_tot_compute_avg_lat[key], 1)}')
                print(f'{key}: network: {round(act_tot_network_latency[key], 1)}')
                print(f'{key}: sum: {round(act_tot_avg_lat[key], 1)}')
                print(f'{key}: avg latency: {round(act_tot_avg_lat[key]/original_MAX_LOAD[key], 1)}')
                print(f'{key}: egress cost: ')
                print()
            print(f'sum_total_lat: compute: {round(sum(act_tot_compute_avg_lat.values()), 1)}')
            print(f'sum_total_lat: network: {round(sum(act_tot_network_latency.values()), 1)}')
            print(f'all_total_avg_lat: {round(sum(act_tot_avg_lat.values()), 1)}')
            print(f'all_avg_lat: {round(sum(act_tot_avg_lat.values())/sum(original_MAX_LOAD.values()), 1)}')
            print(f'all_total_e_cost: ')
        
    
''' END of run_optimizer function'''


# In[52]:


# total_list = list()
# for index, row in concat_df.iterrows():
#     total = group_by_sum.loc[[index]]["flow"].tolist()[0]
#     total_list.append(total)
# concat_df["total"] = total_list
# weight_list = list()
# for index, row in concat_df.iterrows():
#     try:
#         weight_list.append(row['flow']/row['total'])
#     except Exception as e:
#         weight_list.append(0)
# concat_df["weight"] = weight_list
# display(concat_df)


# %%
