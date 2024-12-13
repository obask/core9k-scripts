import os
import requests
import json
import csv

CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# File URLs
MIGAKU_DICT_1_URL = "https://github.com/migaku-official/Migaku-Japanese-Addon/raw/refs/heads/master/src/dict/compAccDict1_.json"
MIGAKU_DICT_2_URL = "https://github.com/migaku-official/Migaku-Japanese-Addon/raw/refs/heads/master/src/dict/compAccDict2_.json"
DICT_1_PATH = os.path.join(CACHE_DIR, "compAccDict1_.json")
DICT_2_PATH = os.path.join(CACHE_DIR, "compAccDict2_.json")
OUTPUT_CSV_PATH = "output_audio.csv"


# Download function
def download_file(url, output_path):
    if not os.path.exists(output_path):
        print(f"Downloading {url}...")
        response = requests.get(url)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"Saved to {output_path}.")
    else:
        print(f"{output_path} already exists. Skipping download.")


def parse_frequency_file(file_path):
    frequency_data = {}
    with open(file_path, "r", encoding="utf-8") as f:
        next(f)  # skip header
        for i, line in enumerate(f):
            if i >= 12137:
                break
            row = line.strip().split("\t")
            key = (row[0], row[1])
            if key not in frequency_data:
                frequency_data[key] = int(row[2])
    print(f"Loaded {len(frequency_data)} entries from frequency file.")
    return frequency_data


def is_tokyo_accent(accent_indices, accent_types):
    if len(accent_indices) > 0 and len(accent_indices[0]) > 0:
        accent_idx = accent_indices[0][0]
    else:
        accent_idx = None

    if len(accent_types) > 0 and len(accent_types[0]) > 0:
        accent_type = accent_types[0][0]
    else:
        accent_type = None

    assert not (accent_idx == 0 and accent_type != "平板")
    return (accent_idx == 0) or (accent_type == "平板")


def main():
    # Download dictionary files
    download_file(MIGAKU_DICT_1_URL, DICT_1_PATH)
    download_file(MIGAKU_DICT_2_URL, DICT_2_PATH)

    # Combine frequency data logic
    frequency_data = parse_frequency_file("cache/jpdb_v2.2_freq_list_2024-10-13.csv")  # Implement parse_frequency_file

    # Process JSON files
    json_files = [DICT_1_PATH, DICT_2_PATH]
    output_rows = []
    seen_words = set()

    for filename in json_files:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            for entry in data:
                if len(entry) < 5:
                    continue

                word = entry[0]
                reading = entry[1]
                variants = entry[4] if len(entry) > 4 else []
                if not variants:
                    continue
                accent_indices = entry[5] if len(entry) > 5 else []
                accent_types = entry[6] if len(entry) > 6 else []

                if word in seen_words:
                    continue

                tokyo = is_tokyo_accent(accent_indices, accent_types)

                selected_mp3s = []
                if tokyo:
                    if len(accent_indices) > 0 and len(accent_indices[0]) > 0:
                        expected_idx = accent_indices[0][0]
                    else:
                        expected_idx = None

                    for var in variants:
                        if len(var) > 1:
                            pitch_str = var[1].strip()
                            pitch_num = None
                            if pitch_str.startswith("[") and pitch_str.endswith("]"):
                                try:
                                    pitch_num = int(pitch_str.strip("[]"))
                                except ValueError:
                                    pass
                            if pitch_num == expected_idx:
                                selected_mp3s.append(var[2])

                    if not selected_mp3s and variants:
                        selected_mp3s = [v[2] for v in variants if len(v) > 2]
                else:
                    if variants and len(variants[0]) > 2:
                        selected_mp3s = [variants[0][2]]

                if (word, reading) not in frequency_data:
                    continue

                row = {
                    "word": word,
                    "reading": reading,
                    "word_index": frequency_data[word, reading],
                }
                for mp3_path in selected_mp3s[:1]:
                    col_name = f"mp3_tokyo_1"
                    row[col_name] = f"[sound:{mp3_path}]"

                output_rows.append(row)
                seen_words.add(word)

    header = ["word", "reading", "word_index", "mp3_tokyo_1"]

    with open(OUTPUT_CSV_PATH, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        for row in sorted(output_rows, key=lambda x: x["word_index"])[:9999]:
            col_name = f"mp3_tokyo_1"
            if col_name not in row:
                row[col_name] = ""
            writer.writerow(row)

    print(f"CSV file '{OUTPUT_CSV_PATH}' created successfully.")


if __name__ == "__main__":
    main()
