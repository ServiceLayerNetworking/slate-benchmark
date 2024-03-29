import pandas as pd
from IPython.display import display
import sys
import _osx_support
from random import sample

original_file = sys.argv[1]
if len(sys.argv) < 2:
    print("Usage: python3 replicate.py <original_file>")
    sys.exit(1)
df = pd.read_csv(original_file)

trace_span_counts = df.groupby('trace_id').size()
trace_ids_with_four_spans = trace_span_counts[trace_span_counts == 4].index
filtered_df = df[df['trace_id'].isin(trace_ids_with_four_spans)]
filtered_df.to_csv("four_span_trace.csv", index=False)

trace_id = filtered_df['trace_id'].unique().tolist()
sample_size = int(len(trace_id) * 0.5)
sampled_trace_id = sample(trace_id, sample_size)
double_filtered_df = filtered_df[filtered_df['trace_id'].isin(sampled_trace_id)]
double_filtered_df.to_csv("sampled_four_span_trace.csv", index=False)

print("all trace ", len(df['trace_id'].unique()))
print("four span trace", len(filtered_df['trace_id'].unique()))
print("sampled four span trace", len(double_filtered_df['trace_id'].unique()))
# display(double_filtered_df)

df_east = double_filtered_df.copy()
df_central = double_filtered_df.copy()
df_south = double_filtered_df.copy()

# Step 2: Update the cluster_id in each copy
df_east['cluster_id'] = 'us-east-1'
df_central['cluster_id'] = 'us-central-1'
df_south['cluster_id'] = 'us-south-1'

print("Replicated us-west-1 to us-east-1, us-central-1, us-south-1")
# Step 3: Concatenate all DataFrames together
df_all = pd.concat([double_filtered_df, df_east, df_central, df_south])
df_all.sort_values(by=['cluster_id', 'trace_id'], inplace=True)
output_fn = "replicated-"+original_file
df_all.to_csv(output_fn, index=False, header=False)
print("Output file written: ", output_fn)


###########################3
# import sys
# import os

# # Check if a file name was provided as an argument
# if len(sys.argv) < 2:
#     print("Usage: python script.py <filename>")
#     sys.exit(1)

# original_file = sys.argv[1]
# merged_file = f"{original_file}-replicated.csv"

# def create_merged_file(original, merged):
#     # Check if the original file exists
#     if not os.path.isfile(original):
#         print(f"Error: {original} does not exist.")
#         return

#     try:
#         with open(original, 'r') as orig_file:
#             original_content = orig_file.read()
#             print(original_content[-1])
#             if original_content[-1] != '\n':
#                 original_content += '\n'
#                 print("add newline")
#             print(original_content[-1])
#             with open('copy.txt', 'w') as copy_file:
#                 copy_file.write(original_content)
#             east_content = original_content.replace('west', 'east')
#             central_content = original_content.replace('west', 'central')
#             south_content = original_content.replace('west', 'south')
            
#             # Concatenate all versions: original, east, and central
#             final_content = original_content + east_content + central_content + south_content
            
#         with open(merged, 'w') as merged_file:
#             merged_file.write(final_content)
            
#         print(f"All modifications merged into {merged}")
#     except IOError as e:
#         print(f"An error occurred: {e}")

# create_merged_file(original_file, merged_file)
