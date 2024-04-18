import pandas as pd
import sys
from random import sample
import trace_parser


# directory = sys.argv[1]
# total_num_svc= int(sys.argv[2])
# if len(sys.argv) < 2:
#     print("Usage: python3 replicate.py <original_file> <total_num_svc>")
#     sys.exit(1)
    
# merged_trace_file_name = trace_parser.run_optimizer.run(directory)

merged_trace_file_name = "hotelreservation.csv"

columns = ["cluster_id","svc_name","method","url","trace_id","span_id","parent_span_id","st","et","rt","xt","ct","call_size","inflight_dict","rps_dict"]
df = pd.read_csv(merged_trace_file_name, header=None, names=columns)

trace_span_counts = df.groupby('trace_id').size()
trace_ids_with_four_spans = trace_span_counts[trace_span_counts == total_num_svc].index
filtered_df = df[df['trace_id'].isin(trace_ids_with_four_spans)]
filtered_df.to_csv("four_span_trace.csv", index=False)

trace_id = filtered_df['trace_id'].unique().tolist()
sample_ratio = 0.1
sample_size = int(len(trace_id) * sample_ratio)
sampled_trace_id = sample(trace_id, sample_size)
double_filtered_df = filtered_df[filtered_df['trace_id'].isin(sampled_trace_id)]
double_filtered_df.to_csv("sampled_four_span_trace.csv", index=False)

print("all trace ", len(df['trace_id'].unique()))
print("four span trace", len(filtered_df['trace_id'].unique()))
print("sampled four span trace", len(double_filtered_df['trace_id'].unique()))
# display(double_filtered_df)

''' This is where you define replicated cluster for slatelog'''
# new_cluster_list = ["us-east-1", "us-central-1", "us-south-1"]
new_cluster_dict = dict()

######################################################
''' Define how you want to replicate '''
# new_cluster_dict["us-east-1"] = ["frontend", "a"]
# new_cluster_dict["us-central-1"] = ["frontend", "a"]
# new_cluster_dict["us-south-1"] = ["frontend", "a"]

# new_cluster_dict["us-east-1"] = ["frontend", "a", "b", "c", "d"]
# new_cluster_dict["us-central-1"] = ["frontend", "a", "b", "c", "d"]
# new_cluster_dict["us-south-1"] = ["frontend", "a", "b", "c", "d"]

new_cluster_dict["us-east-1"] = ["slateingress", "frontend", "profile", "rate", "recommend", "search", "user", "reservation", "geo"]
new_cluster_dict["us-central-1"] = ["slateingress", "frontend", "profile", "rate", "recommend", "search", "user", "reservation", "geo"]
new_cluster_dict["us-south-1"] = ["slateingress", "frontend", "profile", "rate", "recommend", "search", "user", "reservation", "geo"]

######################################################

new_df_dict = dict()
for nc in new_cluster_dict:
    copy_df = double_filtered_df.copy() # copy orignal trace log df
    copy_df['cluster_id'] = nc # set 'cluster_id' column to a new cluster name
    copy_df = copy_df[copy_df['svc_name'].isin(new_cluster_dict[nc])] # filter out services that you don't want to replicate
    new_df_dict[nc] = copy_df.copy()

    print(f"Replicated {nc}")

# Step 3: Concatenate all DataFrames together
df_all = double_filtered_df.copy()
for cluster_id, new_df in new_df_dict.items():
    df_all = pd.concat([df_all, new_df])
df_all.sort_values(by=['cluster_id', 'trace_id'], inplace=True)
output_fn = f"replicated-{merged_trace_file_name}.csv"
df_all.to_csv(output_fn, index=False, header=False)
print("Output file written: ", output_fn)
