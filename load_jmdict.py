import ftplib
import gzip
import os

# sort -t$'\t' -k5,5n output.tsv -o sorted_output.tsv

FTP_HOST = "ftp.edrdg.org"
FTP_DIR = "/pub/Nihongo/"
JMDICT_GZ = "JMdict.gz"
CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)

FREQ_LIST_URL = "https://github.com/Kuuuube/yomitan-dictionaries/raw/main/data/jpdb_v2.2_freq_list_2024-10-13.csv"
FREQ_FILE_PATH = os.path.join(CACHE_DIR, "jpdb_v2.2_freq_list_2024-10-13.csv")
OUTPUT_TSV_PATH = "output.tsv"


def download_file(url, output_path):
    """Download a file if it doesn't already exist."""
    if not os.path.exists(output_path):
        print(f"Downloading {url}...")
        import requests
        r = requests.get(url)
        r.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(r.content)
        print(f"Saved to {output_path}.")
    else:
        print(f"{output_path} already exists. Skipping download.")


def download_jmdict():
    local_gz_path = os.path.join(CACHE_DIR, JMDICT_GZ)
    if not os.path.exists(local_gz_path):
        print("Downloading JMdict.gz from FTP...")
        with ftplib.FTP(FTP_HOST) as ftp:
            ftp.login()
            ftp.cwd(FTP_DIR)
            with open(local_gz_path, 'wb') as f:
                ftp.retrbinary(f"RETR {JMDICT_GZ}", f.write)
        print("Download complete.")
    else:
        print("JMdict.gz already exists in cache. Skipping download.")
    return local_gz_path


def extract_jmdict(gz_path):
    temp_file = os.path.join(CACHE_DIR, "JMdict")
    print("Extracting JMdict.gz...")
    with gzip.open(gz_path, 'rb') as gzfile:
        with open(temp_file, 'wb') as jfile:
            jfile.write(gzfile.read())
    print(f"Extracted to {temp_file}.")
    return temp_file


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


OUTSIDE_ENTRY = 0
INSIDE_ENTRY = 1


def main():
    # Download files if needed
    gz_path = download_jmdict()
    jmdict_path = extract_jmdict(gz_path)
    download_file(FREQ_LIST_URL, FREQ_FILE_PATH)
    frequency_data = parse_frequency_file(FREQ_FILE_PATH)

    state = OUTSIDE_ENTRY

    kanji = ""
    reading = ""
    english_glosses = []
    russian_glosses = []

    with open(OUTPUT_TSV_PATH, "w", encoding="utf-8") as output_file:
        # Write TSV header
        output_file.write("Kanji\tReading\tRussian\tEnglish\tFrequency\n")

        with open(jmdict_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip('\n')

                if state == OUTSIDE_ENTRY:
                    if line.startswith("<entry>"):
                        # Reset buffers
                        kanji = ""
                        reading = ""
                        english_glosses = []
                        russian_glosses = []
                        state = INSIDE_ENTRY

                elif state == INSIDE_ENTRY:
                    if line.startswith("</entry>"):
                        # Entry ended. Decide if we write it
                        if not kanji:
                            kanji = reading

                        freq = frequency_data.get((kanji, reading), None)
                        if freq:
                            # Write to TSV file
                            output_file.write(
                                f"{kanji}\t{reading}\t{'; '.join(russian_glosses)}\t{'; '.join(english_glosses)}\t{freq}\n"
                            )

                        state = OUTSIDE_ENTRY

                    else:
                        # Parse inside entry
                        if line.startswith("<keb>") and line.endswith("</keb>") and not kanji:
                            kanji = line[5:-6]

                        if line.startswith("<reb>") and line.endswith("</reb>") and not reading:
                            reading = line[5:-6]

                        if line.endswith("</gloss>"):
                            gloss_text = line.removesuffix("</gloss>")
                            if gloss_text.startswith('<gloss xml:lang="rus">'):
                                russian_glosses.append(gloss_text.removeprefix('<gloss xml:lang="rus">'))
                            if gloss_text.startswith('<gloss>'):
                                english_glosses.append(gloss_text.removeprefix("<gloss>"))

    print(f"Output written to {OUTPUT_TSV_PATH}.")


if __name__ == "__main__":
    main()
