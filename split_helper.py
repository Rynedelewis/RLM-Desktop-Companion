import re
import sys

def analyze(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    in_func = False
    func_start = 0
    func_name = ""
    
    for i, line in enumerate(lines):
        if re.match(r'^(local )?function ', line) or re.match(r'^RCEPGP[.:][a-zA-Z0-9_]+\s*=\s*function', line):
            print(f"[{i+1}] {line.strip()}")

if __name__ == '__main__':
    analyze(sys.argv[1])
