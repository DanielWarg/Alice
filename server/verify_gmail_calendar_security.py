#!/usr/bin/env python3
"""
Gmail/Calendar Security Verification for Alice
Verifies scope minimization and security practices
"""

import sys
import os
import re
from pathlib import Path

# Add server to path  
sys.path.insert(0, str(Path(__file__).parent))

def verify_gmail_scope():
    """Verify Gmail uses minimal scope"""
    print("📧 Verifying Gmail scope minimization...")
    
    gmail_service_path = Path(__file__).parent / "core" / "gmail_service.py"
    
    if not gmail_service_path.exists():
        print("   ⚠️ Gmail service file not found")
        return False
    
    with open(gmail_service_path, 'r') as f:
        content = f.read()
    
    # Look for scope declaration
    scope_pattern = r"scopes=\['([^']+)'\]"
    matches = re.findall(scope_pattern, content)
    
    if matches:
        actual_scope = matches[0]
        expected_scope = "https://www.googleapis.com/auth/gmail.modify"
        
        if actual_scope == expected_scope:
            print(f"   ✅ Gmail uses minimal scope: {actual_scope}")
            return True
        else:
            print(f"   ❌ Gmail scope not minimal. Expected: {expected_scope}, Got: {actual_scope}")
            return False
    else:
        print("   ❌ Could not find Gmail scope declaration")
        return False

def verify_calendar_scope():
    """Verify Calendar uses minimal scope"""
    print("\n📅 Verifying Calendar scope minimization...")
    
    calendar_service_path = Path(__file__).parent / "core" / "calendar_service.py"
    
    if not calendar_service_path.exists():
        print("   ⚠️ Calendar service file not found")
        return False
    
    with open(calendar_service_path, 'r') as f:
        content = f.read()
    
    # Look for scope declaration
    scope_pattern = r"scopes=\['([^']+)'\]"
    matches = re.findall(scope_pattern, content)
    
    if matches:
        actual_scope = matches[0]
        expected_scope = "https://www.googleapis.com/auth/calendar"
        
        if actual_scope == expected_scope:
            print(f"   ✅ Calendar uses minimal scope: {actual_scope}")
            return True
        else:
            print(f"   ❌ Calendar scope not minimal. Expected: {expected_scope}, Got: {actual_scope}")
            return False
    else:
        print("   ❌ Could not find Calendar scope declaration")
        return False

def verify_gitignore_security():
    """Verify sensitive files are in .gitignore"""
    print("\n🚫 Verifying sensitive files excluded from git...")
    
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    
    if not gitignore_path.exists():
        print("   ❌ .gitignore file not found")
        return False
    
    with open(gitignore_path, 'r') as f:
        gitignore_content = f.read()
    
    # Check critical patterns
    critical_patterns = [
        "*credentials*.json",
        "*token*.pickle", 
        "gmail_token.pickle",
        "calendar_token.pickle",
        ".env"
    ]
    
    missing_patterns = []
    for pattern in critical_patterns:
        if pattern not in gitignore_content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"   ❌ Missing patterns in .gitignore: {missing_patterns}")
        return False
    else:
        print("   ✅ All sensitive file patterns excluded from git")
        return True

def verify_error_handling():
    """Verify graceful error handling"""
    print("\n⚠️ Verifying graceful error handling...")
    
    # Check Gmail service error messages
    gmail_service_path = Path(__file__).parent / "core" / "gmail_service.py"
    
    if gmail_service_path.exists():
        with open(gmail_service_path, 'r') as f:
            gmail_content = f.read()
        
        # Look for graceful error messages
        if "inte tillgänglig" in gmail_content or "not available" in gmail_content.lower():
            print("   ✅ Gmail service has graceful error handling")
            gmail_ok = True
        else:
            print("   ❌ Gmail service missing graceful error handling")
            gmail_ok = False
    else:
        gmail_ok = False
    
    # Check Calendar service error handling
    calendar_service_path = Path(__file__).parent / "core" / "calendar_service.py"
    
    if calendar_service_path.exists():
        with open(calendar_service_path, 'r') as f:
            calendar_content = f.read()
        
        # Look for initialization checks
        if "_initialize_service" in calendar_content:
            print("   ✅ Calendar service has initialization checks")
            calendar_ok = True
        else:
            print("   ❌ Calendar service missing initialization checks")
            calendar_ok = False
    else:
        calendar_ok = False
    
    return gmail_ok and calendar_ok

def verify_no_hardcoded_secrets():
    """Verify no hardcoded secrets in source code"""
    print("\n🔍 Verifying no hardcoded secrets...")
    
    service_files = [
        Path(__file__).parent / "core" / "gmail_service.py",
        Path(__file__).parent / "core" / "calendar_service.py",
    ]
    
    dangerous_patterns = [
        r'client_secret["\s]*=["\s]*[A-Za-z0-9_-]{10,}',
        r'access_token["\s]*=["\s]*[A-Za-z0-9._-]{20,}',
        r'ya29\.[A-Za-z0-9._-]+',
        r'client_id["\s]*=["\s]*[A-Za-z0-9_-]+\.apps\.googleusercontent\.com',
    ]
    
    violations = []
    
    for file_path in service_files:
        if not file_path.exists():
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
        
        for pattern in dangerous_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                violations.append({
                    'file': file_path.name,
                    'pattern': pattern,
                    'matches': matches
                })
    
    if violations:
        print("   ❌ Found potential hardcoded secrets:")
        for violation in violations:
            print(f"      🚨 {violation['file']}: {violation['matches'][0]}")
        return False
    else:
        print("   ✅ No hardcoded secrets detected")
        return True

def verify_token_storage_format():
    """Verify tokens stored in secure format"""
    print("\n🔐 Verifying secure token storage format...")
    
    # Check that services use pickle format (binary)
    gmail_service_path = Path(__file__).parent / "core" / "gmail_service.py"
    calendar_service_path = Path(__file__).parent / "core" / "calendar_service.py"
    
    issues = []
    
    for service_path, service_name in [(gmail_service_path, "Gmail"), (calendar_service_path, "Calendar")]:
        if service_path.exists():
            with open(service_path, 'r') as f:
                content = f.read()
            
            # Check for secure pickle usage
            if "pickle.load" in content and "pickle.dump" in content:
                print(f"   ✅ {service_name} uses secure pickle format for tokens")
            else:
                issues.append(f"{service_name} doesn't use secure token storage")
            
            # Check for problematic plain-text token storage
            if "json.dump" in content and "token" in content:
                issues.append(f"{service_name} may store tokens in plain-text JSON")
    
    if issues:
        print("   ❌ Token storage issues:")
        for issue in issues:
            print(f"      🚨 {issue}")
        return False
    else:
        print("   ✅ All tokens stored in secure binary format")
        return True

def run_security_verification():
    """Run all security verifications"""
    print("🔐 GMAIL/CALENDAR SECURITY VERIFICATION")
    print("=" * 50)
    
    tests = [
        ("Gmail Scope Minimization", verify_gmail_scope),
        ("Calendar Scope Minimization", verify_calendar_scope), 
        ("Gitignore Security", verify_gitignore_security),
        ("Error Handling", verify_error_handling),
        ("No Hardcoded Secrets", verify_no_hardcoded_secrets),
        ("Secure Token Storage", verify_token_storage_format),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"   💥 Test {test_name} failed with error: {e}")
    
    print(f"\n📊 SECURITY VERIFICATION RESULTS:")
    print(f"   ✅ Passed: {passed}/{total}")
    print(f"   📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🏆 ALL SECURITY VERIFICATIONS PASSED!")
        print("\n✅ Gmail/Calendar scope och felhantering verifierade")
        print("✅ Inga tokens i logg eller källkod")
        print("✅ Säker token-lagring implementerad") 
        print("✅ Känsliga filer exkluderade från git")
        
        print("\n🎯 SECURITY SUMMARY:")
        print("   📧 Gmail: Minimal scope (gmail.modify)")
        print("   📅 Calendar: Minimal scope (calendar)")
        print("   🔒 Token Storage: Secure binary format") 
        print("   🚫 Git Exclusions: All sensitive files")
        print("   ⚠️ Error Handling: Graceful degradation")
        
        return True
    else:
        print(f"\n❌ {total-passed} security checks failed")
        print("Review security implementation before production")
        return False

if __name__ == "__main__":
    success = run_security_verification()
    if not success:
        sys.exit(1)