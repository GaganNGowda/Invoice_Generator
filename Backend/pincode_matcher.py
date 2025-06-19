# pincode_matcher.py
import pandas as pd
import re
from typing import Optional

def find_nearest_pincode(target_pincode_str: str, csv_file_path: str = 'branch_list 2.csv') -> Optional[str]:
    """
    Finds the numerically nearest 6-digit pincode in the 'address' column of a CSV file.

    Args:
        target_pincode_str: The 6-digit pincode string provided by the user.
        csv_file_path: The path to the CSV file containing address data.

    Returns:
        The nearest matching 6-digit pincode string from the CSV, or None if no valid pincodes are found.
    """
    try:
        target_pincode = int(target_pincode_str)
        if not (100000 <= target_pincode <= 999999):
            print(f"WARNING: Target pincode '{target_pincode_str}' is not a valid 6-digit number. Skipping nearest match search.")
            return None
    except ValueError:
        print(f"WARNING: Target pincode '{target_pincode_str}' is not a valid number. Skipping nearest match search.")
        return None

    try:
        # Read the CSV file
        df = pd.read_csv(csv_file_path)

        # Assuming the addresses are in a column named 'address' or similar
        # Adjust 'address' if your column name is different
        if 'address' not in df.columns:
            print(f"ERROR: 'address' column not found in '{csv_file_path}'. Cannot extract pincodes.")
            return None

        # Regex to find 6-digit numbers that look like pincodes
        pincode_pattern = re.compile(r'\b(\d{6})\b') # Matches exactly 6 digits as a whole word

        min_diff = float('inf')
        nearest_pincode_found = None

        # Iterate through the address column and extract pincodes
        for address in df['address'].dropna():
            found_pincodes = pincode_pattern.findall(str(address))
            for p_str in found_pincodes:
                try:
                    p_int = int(p_str)
                    diff = abs(target_pincode - p_int)
                    if diff < min_diff:
                        min_diff = diff
                        nearest_pincode_found = p_str
                except ValueError:
                    # Skip if the found string is not a valid number, though regex should prevent most of these
                    pass

        return nearest_pincode_found

    except FileNotFoundError:
        print(f"ERROR: CSV file not found at '{csv_file_path}'.")
        return None
    except pd.errors.EmptyDataError:
        print(f"WARNING: CSV file '{csv_file_path}' is empty.")
        return None
    except Exception as e:
        print(f"ERROR: An error occurred while processing CSV for pincode matching: {e}")
        return None

# Example usage (for testing this file independently)
if __name__ == '__main__':
    # Create a dummy CSV for testing if it doesn't exist
    dummy_csv_path = 'branch_list 2.csv'
    if not pd.io.common.file_exists(dummy_csv_path):
        dummy_data = {
            'branch_name': ['Branch A', 'Branch B', 'Branch C', 'Branch D'],
            'address': [
                '123 Main St, CityA, StateA, 563101',
                '456 Oak Ave, CityB, StateB, 563001',
                '789 Pine Rd, CityC, StateC, 563200',
                '101 Maple Ln, CityD, StateD, 123456'
            ]
        }
        dummy_df = pd.DataFrame(dummy_data)
        dummy_df.to_csv(dummy_csv_path, index=False)
        print(f"Created a dummy CSV: {dummy_csv_path}")

    test_pincode = "563012"
    nearest = find_nearest_pincode(test_pincode)
    if nearest:
        print(f"For {test_pincode}, the nearest pincode found in CSV is: {nearest}")
    else:
        print(f"No nearest pincode found for {test_pincode}.")

    test_pincode_no_match = "999999"
    nearest_no_match = find_nearest_pincode(test_pincode_no_match)
    if nearest_no_match:
        print(f"For {test_pincode_no_match}, the nearest pincode found in CSV is: {nearest_no_match}")
    else:
        print(f"No nearest pincode found for {test_pincode_no_match}.")
