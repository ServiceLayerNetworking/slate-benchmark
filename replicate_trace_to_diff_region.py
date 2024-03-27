import sys
import os

# Check if a file name was provided as an argument
if len(sys.argv) < 2:
    print("Usage: python script.py <filename>")
    sys.exit(1)

original_file = sys.argv[1]
merged_file = f"{original_file}-replicated.csv"

def create_merged_file(original, merged):
    # Check if the original file exists
    if not os.path.isfile(original):
        print(f"Error: {original} does not exist.")
        return

    try:
        with open(original, 'r') as orig_file:
            original_content = orig_file.read()
            print(original_content[-1])
            if original_content[-1] != '\n':
                original_content += '\n'
                print("add newline")
            print(original_content[-1])
            with open('copy.txt', 'w') as copy_file:
                copy_file.write(original_content)
            east_content = original_content.replace('west', 'east')
            central_content = original_content.replace('west', 'central')
            south_content = original_content.replace('west', 'south')
            
            # Concatenate all versions: original, east, and central
            final_content = original_content + east_content + central_content + south_content
            
        with open(merged, 'w') as merged_file:
            merged_file.write(final_content)
            
        print(f"All modifications merged into {merged}")
    except IOError as e:
        print(f"An error occurred: {e}")

create_merged_file(original_file, merged_file)
