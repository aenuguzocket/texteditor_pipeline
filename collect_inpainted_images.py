
import os
import shutil
import glob

def collect_inpainted_images(root_dir, target_dir_name="collected_inpainted_images"):
    """
    Walks through the root_dir, searching for 'inpainted.png',
    and copies it to a target directory with a unique name based on the source folder.
    """
    target_dir = os.path.join(root_dir, target_dir_name)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")
    else:
        print(f"Directory already exists: {target_dir}")

    print(f"Searching in: {root_dir}")
    # Using recursive glob to find all inpainted.png files
    search_pattern = os.path.join(root_dir, "**", "inpainted.png")
    found_files = glob.glob(search_pattern, recursive=True)

    print(f"Found {len(found_files)} files.")

    count = 0
    for file_path in found_files:
        # Avoid copying files that might already be in the target directory if it's inside root_dir
        if target_dir in os.path.abspath(file_path):
            continue

        parent_dir_name = os.path.basename(os.path.dirname(file_path))
        new_filename = f"{parent_dir_name}.png"
        dest_path = os.path.join(target_dir, new_filename)
        
        try:
            shutil.copy2(file_path, dest_path)
            print(f"Copied: {file_path} -> {dest_path}")
            count += 1
        except Exception as e:
            print(f"Error copying {file_path}: {e}")
            
    print(f"Successfully collected {count} images in '{target_dir}'.")

if __name__ == "__main__":
    pipeline_outputs_dir = os.path.join(os.getcwd(), "pipeline_outputs")
    
    if not os.path.exists(pipeline_outputs_dir):
        print(f"Directory not found: {pipeline_outputs_dir}")
        print("Please run this script from the parent directory of 'pipeline_outputs'.")
    else:
        collect_inpainted_images(pipeline_outputs_dir)
