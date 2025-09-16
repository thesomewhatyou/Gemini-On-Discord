#!/usr/bin/env python3
"""
Security checker for Discord Gemini Bot
Scans for common security issues and vulnerabilities
"""

import re
import os
import sys
from typing import List, Tuple

def check_hardcoded_secrets(file_path: str) -> List[Tuple[int, str]]:
    """Check for hardcoded secrets in code"""
    issues = []
    
    patterns = [
        (r'AIza[0-9A-Za-z_-]{35,}', 'Potential Google API key'),
        (r'["\']?password["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded password'),
        (r'["\']?secret["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded secret'),
        (r'["\']?token["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Hardcoded token'),
        (r'-----BEGIN.*PRIVATE KEY-----', 'Private key'),
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            for pattern, description in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append((line_num, f"{description}: {line.strip()}"))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return issues

def check_input_validation(file_path: str) -> List[Tuple[int, str]]:
    """Check for potential input validation issues"""
    issues = []
    
    patterns = [
        (r'exec\s*\(', 'Use of exec() function'),
        (r'eval\s*\(', 'Use of eval() function'),
        (r'os\.system\s*\(', 'Use of os.system()'),
        (r'subprocess\.call\([^)]*shell\s*=\s*True', 'subprocess with shell=True'),
        (r'open\s*\([^)]*["\'][^"\']*\.\.[^"\']*["\']', 'Potential path traversal'),
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            for pattern, description in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append((line_num, f"{description}: {line.strip()}"))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return issues

def check_error_handling(file_path: str) -> List[Tuple[int, str]]:
    """Check for potential information disclosure in error handling"""
    issues = []
    
    patterns = [
        (r'except.*:\s*print\s*\([^)]*[eE]rror[^)]*\)', 'Error printed to console'),
        (r'except.*:\s*.*\.send.*[eE]rror.*\)', 'Error sent in response'),
        (r'traceback\.print_exc\s*\(\s*\)', 'Traceback printed'),
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
        for line_num, line in enumerate(lines, 1):
            for pattern, description in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append((line_num, f"{description}: {line.strip()}"))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return issues

def main():
    """Main security check function"""
    print("🔒 Discord Gemini Bot Security Scanner")
    print("=" * 50)
    
    python_files = ['bot.py']
    total_issues = 0
    
    for file_path in python_files:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            continue
            
        print(f"\n📁 Checking {file_path}...")
        
        # Check for hardcoded secrets
        secret_issues = check_hardcoded_secrets(file_path)
        if secret_issues:
            print(f"  🚨 Hardcoded Secrets ({len(secret_issues)} issues):")
            for line_num, issue in secret_issues:
                print(f"    Line {line_num}: {issue}")
            total_issues += len(secret_issues)
        
        # Check input validation
        input_issues = check_input_validation(file_path)
        if input_issues:
            print(f"  ⚠️  Input Validation ({len(input_issues)} issues):")
            for line_num, issue in input_issues:
                print(f"    Line {line_num}: {issue}")
            total_issues += len(input_issues)
        
        # Check error handling
        error_issues = check_error_handling(file_path)
        if error_issues:
            print(f"  📊 Error Handling ({len(error_issues)} issues):")
            for line_num, issue in error_issues:
                print(f"    Line {line_num}: {issue}")
            total_issues += len(error_issues)
        
        if not (secret_issues or input_issues or error_issues):
            print(f"  ✅ No issues found in {file_path}")
    
    print("\n" + "=" * 50)
    if total_issues == 0:
        print("✅ Security scan completed - No major issues found!")
        return 0
    else:
        print(f"⚠️  Security scan completed - {total_issues} issues found")
        print("\n💡 Recommendations:")
        print("   - Review flagged lines carefully")
        print("   - Ensure secrets are stored in environment variables")
        print("   - Validate and sanitize all user inputs")
        print("   - Use sanitized error messages for user-facing errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())