import os
import sys


def process_file(file_path):
    with open(file_path, "r") as file:
        content = file.read()
        return f"{file_path}:\n```\n{content}\n```\n"


def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <file/directory patterns>")
        sys.exit(1)

    patterns = sys.argv[1:]
    current_directory = os.getcwd()

    output = ""
    for pattern in patterns:
        for root, _, files in os.walk(current_directory, topdown=True):
            for file in files:
                if file.endswith(".py") and pattern in os.path.join(root, file):
                    file_path = os.path.join(root, file)
                    print(f"Include file: {file_path}? (y/n)")
                    user_input = input()
                    if user_input.lower() == "y":
                        output += process_file(file_path)
                    else:
                        print(f"Skipping file: {file_path}")

    with open("output.md", "w") as output_file:
        output_file.write(output)


if __name__ == "__main__":
    main()
