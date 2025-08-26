#!/usr/bin/env python3
"""
Simple launcher for the sitemap discovery script with emoji filename
"""
import os
import sys

def main():
    # Find the sitemap discovery file
    current_dir = os.getcwd()
    
    # Look for the emoji sitemap file
    for filename in os.listdir(current_dir):
        if "sitemap_discovery_Phase_1.py" in filename and filename.startswith("🗺️"):
            print(f"Found sitemap discovery file: {filename}")
            
            # Execute the file directly with proper globals
            try:
                # Create a proper execution environment
                exec_globals = {'__name__': '__main__', '__file__': filename}
                
                with open(filename, 'r', encoding='utf-8') as f:
                    code = f.read()
                    exec(code, exec_globals)
                return
            except Exception as e:
                print(f"Error running {filename}: {e}")
                import traceback
                traceback.print_exc()
                return
    
    print("❌ Could not find sitemap discovery file")

if __name__ == "__main__":
    main()
