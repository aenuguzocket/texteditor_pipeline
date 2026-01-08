
import os
import shutil
import glob

def get_next_filename(directory, base_name="inpainted", extension=".png"):
    """
    Finds the next available numbered filename in the directory.
    e.g., inpainted_1.png, inpainted_2.png, ...
    """
    counter = 1
    while True:
        new_filename = f"{base_name}_{counter}{extension}"
        full_path = os.path.join(directory, new_filename)
        if not os.path.exists(full_path):
            return full_path
        counter += 1

def copy_inpainted_images(root_dir):
    """
    Walks through the root_dir, searching for 'inpainted.png',
    and copies it to a numbered file in the same directory.
    """
    print(f"Searching in: {root_dir}")
    # Using recursive glob to find all inpainted.png files
    search_pattern = os.path.join(root_dir, "**", "inpainted.png")
    # GLOB recursive requires python 3.5+, assume modern env
    found_files = glob.glob(search_pattern, recursive=True)

    print(f"Found {len(found_files)} files.")

    for file_path in found_files:
        directory = os.path.dirname(file_path)
        
        # Determine new destination path
        dest_path = get_next_filename(directory)
        
        try:
            shutil.copy2(file_path, dest_path)
            print(f"Copied: {file_path} -> {dest_path}")
        except Exception as e:
            print(f"Error copying {file_path}: {e}")

if __name__ == "__main__":
    # Adjust this path if running from a different location, 
    # but based on current cwd it should be relative or absolute.
    pipeline_outputs_dir = os.path.join(os.getcwd(), "pipeline_outputs")
    
    if not os.path.exists(pipeline_outputs_dir):
        print(f"Directory not found: {pipeline_outputs_dir}")
        print("Please run this script from the parent directory of 'pipeline_outputs' or update the path.")
    else:
        copy_inpainted_images(pipeline_outputs_dir)
