import logging
from file_parser import FileParser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # List of file names to test
    files = ["obama.txt", "obama.pdf", "obama-ocr.pdf"]

    # Loop through the files and use the FileParser to parse each one
    for filename in files:
        try:
            # Create a FileParser instance with the filename
            parser = FileParser(filepath=filename)
            # Parse the file and print the output
            content = parser.parse()
            print(f"Content of {filename}:")
            print(content[:500])  # Print the first 500 characters to avoid too much output
            print("--------------------------------------------------")
        except Exception as e:
            # Print any errors encountered during parsing
            logging.error(f"Failed to process file '{filename}': {e}")

if __name__ == "__main__":
    main()
