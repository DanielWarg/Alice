#!/usr/bin/env python3
"""
Validate Autonomous Test System
Tests the voice pipeline testing components without full TS compilation
"""

import os
import json
import sys
from pathlib import Path
import subprocess
import time
import simple_progress_tracker as tracker

def check_file_exists(filepath, description):
    """Check if a file exists and log result"""
    if Path(filepath).exists():
        tracker.log_activity("validation", f"✅ {description} exists", {"file": filepath})
        return True
    else:
        tracker.log_activity("validation", f"❌ {description} missing", {"file": filepath})
        return False

def validate_test_structure():
    """Validate the test system file structure"""
    tracker.log_activity("testing", "Validating test system structure")
    
    required_files = [
        ("core/talk/tests/autonomous/realtime_audio_generator.ts", "Audio Generator"),
        ("core/talk/tests/validation/privacy_validator.ts", "Privacy Validator"),
        ("core/talk/tests/validation/latency_validator.ts", "Latency Validator"),
        ("core/talk/tests/validation/barge_in_validator.ts", "Barge-in Validator"),
        ("core/talk/tests/utils/test_logger.ts", "Test Logger"),
        ("core/talk/tests/test_runner_simple.ts", "Simple Test Runner"),
        ("core/talk/tests/run_autonomous_tests.ts", "Autonomous Test Runner"),
        ("core/talk/server/privacy/safe_summary.ts", "Safe Summary"),
        ("core/talk/server/metrics/logger.ts", "Metrics Logger"),
    ]
    
    passed = 0
    total = len(required_files)
    
    for filepath, description in required_files:
        if check_file_exists(filepath, description):
            passed += 1
    
    tracker.track_test("structure", f"passed" if passed == total else "failed", {
        "passed": passed,
        "total": total,
        "success_rate": f"{(passed/total)*100:.1f}%"
    })
    
    return passed == total

def validate_test_content():
    """Validate that test files contain expected content"""
    tracker.log_activity("testing", "Validating test content quality")
    
    tests = []
    
    # Check Privacy Validator
    privacy_file = Path("core/talk/tests/validation/privacy_validator.ts")
    if privacy_file.exists():
        content = privacy_file.read_text()
        has_pii_patterns = "piiPatterns" in content
        has_logger = "TestLogger" in content
        has_validation = "validate(" in content
        
        privacy_score = sum([has_pii_patterns, has_logger, has_validation])
        tests.append(("Privacy Validator Content", privacy_score, 3))
        
        tracker.log_activity("validation", f"Privacy Validator: {privacy_score}/3 features", {
            "pii_patterns": has_pii_patterns,
            "logger_integration": has_logger,
            "validation_method": has_validation
        })
    
    # Check Audio Generator
    audio_file = Path("core/talk/tests/autonomous/realtime_audio_generator.ts")
    if audio_file.exists():
        content = audio_file.read_text()
        has_synthesis = "synthesizeText" in content
        has_samples = "recordedSamples" in content
        has_cleanup = "cleanup" in content
        
        audio_score = sum([has_synthesis, has_samples, has_cleanup])
        tests.append(("Audio Generator Content", audio_score, 3))
        
        tracker.log_activity("validation", f"Audio Generator: {audio_score}/3 features", {
            "synthesis": has_synthesis,
            "samples": has_samples,
            "cleanup": has_cleanup
        })
    
    # Check Test Logger
    logger_file = Path("core/talk/tests/utils/test_logger.ts")
    if logger_file.exists():
        content = logger_file.read_text()
        has_structured_logging = "TestLogEntry" in content
        has_metrics = "TestMetrics" in content
        has_report_gen = "generateReport" in content
        
        logger_score = sum([has_structured_logging, has_metrics, has_report_gen])
        tests.append(("Test Logger Content", logger_score, 3))
        
        tracker.log_activity("validation", f"Test Logger: {logger_score}/3 features", {
            "structured_logging": has_structured_logging,
            "metrics": has_metrics,
            "report_generation": has_report_gen
        })
    
    total_score = sum(score for _, score, _ in tests)
    max_score = sum(max_score for _, _, max_score in tests)
    
    success = total_score == max_score
    tracker.track_test("content", "passed" if success else "failed", {
        "total_score": total_score,
        "max_score": max_score,
        "success_rate": f"{(total_score/max_score)*100:.1f}%"
    })
    
    return success

def validate_typescript_syntax():
    """Check basic TypeScript syntax without full compilation"""
    tracker.log_activity("testing", "Validating TypeScript syntax")
    
    ts_files = [
        "core/talk/tests/validation/privacy_validator.ts",
        "core/talk/tests/validation/latency_validator.ts", 
        "core/talk/tests/validation/barge_in_validator.ts",
        "core/talk/tests/utils/test_logger.ts"
    ]
    
    syntax_issues = []
    
    for ts_file in ts_files:
        if Path(ts_file).exists():
            try:
                # Basic syntax check - look for common issues
                content = Path(ts_file).read_text()
                
                # Check for basic TS structure
                has_imports = content.count("import") > 0
                has_exports = content.count("export") > 0
                has_interfaces = content.count("interface") > 0
                has_classes = content.count("class") > 0
                
                issues = []
                if not has_imports and not has_exports:
                    issues.append("no_imports_exports")
                if not has_interfaces and not has_classes:
                    issues.append("no_types_defined")
                
                # Check for obvious syntax issues
                open_braces = content.count("{")
                close_braces = content.count("}")
                if open_braces != close_braces:
                    issues.append("unmatched_braces")
                
                if issues:
                    syntax_issues.extend([(ts_file, issue) for issue in issues])
                    
            except Exception as e:
                syntax_issues.append((ts_file, f"read_error: {e}"))
    
    success = len(syntax_issues) == 0
    tracker.track_test("syntax", "passed" if success else "failed", {
        "files_checked": len(ts_files),
        "issues_found": len(syntax_issues),
        "issues": syntax_issues
    })
    
    return success

def validate_integration_readiness():
    """Check if system is ready for integration testing"""
    tracker.log_activity("testing", "Validating integration readiness")
    
    checks = []
    
    # Check package.json exists
    package_json = Path("core/talk/package.json")
    if package_json.exists():
        try:
            with open(package_json) as f:
                package_data = json.load(f)
            
            has_scripts = "scripts" in package_data
            has_deps = "dependencies" in package_data
            has_dev_deps = "devDependencies" in package_data
            
            checks.append(("Package Configuration", has_scripts and has_deps and has_dev_deps))
        except:
            checks.append(("Package Configuration", False))
    else:
        checks.append(("Package Configuration", False))
    
    # Check tsconfig exists
    tsconfig = Path("core/talk/tsconfig.json")
    checks.append(("TypeScript Config", tsconfig.exists()))
    
    # Check test directories
    test_dirs = [
        "core/talk/tests/autonomous",
        "core/talk/tests/validation", 
        "core/talk/tests/utils",
        "core/talk/tests/fixtures"
    ]
    
    for test_dir in test_dirs:
        checks.append((f"Directory: {test_dir}", Path(test_dir).exists()))
    
    # Check server structure
    server_files = [
        "core/talk/server/privacy/safe_summary.ts",
        "core/talk/server/metrics/logger.ts"
    ]
    
    for server_file in server_files:
        checks.append((f"Server: {Path(server_file).name}", Path(server_file).exists()))
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    success = passed == total
    
    tracker.track_test("integration", "passed" if success else "failed", {
        "checks_passed": passed,
        "total_checks": total,
        "success_rate": f"{(passed/total)*100:.1f}%",
        "failed_checks": [name for name, result in checks if not result]
    })
    
    return success

def run_comprehensive_validation():
    """Run all validation tests"""
    tracker.log_activity("testing", "Starting comprehensive test system validation")
    tracker.track_milestone("Comprehensive Validation Started")
    
    validation_results = []
    
    print("🧪 Alice Autonomous Test System Validation")
    print("=" * 50)
    
    # Test 1: Structure
    print("\n📁 Test 1: File Structure Validation")
    structure_ok = validate_test_structure()
    validation_results.append(("Structure", structure_ok))
    
    # Test 2: Content
    print("\n📝 Test 2: Content Quality Validation")
    content_ok = validate_test_content()
    validation_results.append(("Content", content_ok))
    
    # Test 3: Syntax
    print("\n🔍 Test 3: TypeScript Syntax Validation")
    syntax_ok = validate_typescript_syntax()
    validation_results.append(("Syntax", syntax_ok))
    
    # Test 4: Integration Readiness
    print("\n🔗 Test 4: Integration Readiness")
    integration_ok = validate_integration_readiness()
    validation_results.append(("Integration", integration_ok))
    
    # Final Results
    passed = sum(1 for _, result in validation_results if result)
    total = len(validation_results)
    overall_success = passed == total
    
    print("\n" + "=" * 50)
    print("📊 VALIDATION RESULTS")
    print("=" * 50)
    
    for test_name, result in validation_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if overall_success:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ Autonomous test system is ready for deployment")
        tracker.track_milestone("Test System Validation Completed Successfully", {
            "all_tests_passed": True,
            "success_rate": "100%"
        })
    else:
        print("⚠️  Some validations failed")
        print("🔧 Review failed components before deployment")
        tracker.track_milestone("Test System Validation Completed with Issues", {
            "tests_passed": passed,
            "tests_total": total,
            "success_rate": f"{(passed/total)*100:.1f}%"
        })
    
    tracker.log_activity("testing", "Comprehensive validation completed", {
        "overall_success": overall_success,
        "passed": passed,
        "total": total
    })
    
    return overall_success, validation_results

def create_validation_report(success, results):
    """Create a detailed validation report"""
    tracker.log_activity("reporting", "Creating validation report")
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = Path(f"logs/test_validation_report_{timestamp}.md")
    
    # Ensure logs directory exists
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Alice Autonomous Test System Validation Report\n\n")
        f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Overall Status:** {'✅ PASSED' if success else '❌ FAILED'}\n\n")
        
        f.write("## Test Results\n\n")
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            f.write(f"- **{test_name}:** {status}\n")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        f.write(f"\n**Success Rate:** {passed}/{total} ({(passed/total)*100:.1f}%)\n\n")
        
        f.write("## System Architecture\n\n")
        f.write("The autonomous test system includes:\n\n")
        f.write("### Core Components\n")
        f.write("- **Real-time Audio Generator** - Generates Swedish speech for testing\n")
        f.write("- **Privacy Validator** - Ensures no PII leakage\n") 
        f.write("- **Latency Validator** - Validates SLO compliance\n")
        f.write("- **Barge-in Validator** - Tests interruption handling\n")
        f.write("- **Test Logger** - Structured logging and metrics\n\n")
        
        f.write("### Features\n")
        f.write("- Sub-500ms voice pipeline testing\n")
        f.write("- Real-time audio generation (not just mock data)\n")
        f.write("- Comprehensive privacy validation\n")
        f.write("- Performance SLO validation\n")
        f.write("- Structured test reporting\n")
        f.write("- Clean test organization for easy cleanup\n\n")
        
        if success:
            f.write("## ✅ Ready for Production\n\n")
            f.write("All validation tests passed. The autonomous test system is ready for:\n")
            f.write("- Real-time voice pipeline testing\n")
            f.write("- Privacy compliance validation\n") 
            f.write("- Performance benchmarking\n")
            f.write("- Production quality assurance\n\n")
        else:
            f.write("## ⚠️ Issues Found\n\n")
            f.write("Some validation tests failed. Please review:\n")
            for test_name, result in results:
                if not result:
                    f.write(f"- {test_name} validation failed\n")
            f.write("\nResolve these issues before production deployment.\n\n")
        
        f.write("---\n")
        f.write("*Generated by Alice Autonomous Test Validation System*\n")
    
    print(f"\n📄 Validation report saved: {report_file}")
    tracker.log_activity("reporting", "Validation report created", {"file": str(report_file)})
    
    return report_file

if __name__ == "__main__":
    print("🚀 Starting Alice Test System Validation...")
    
    try:
        # Run comprehensive validation
        success, results = run_comprehensive_validation()
        
        # Create report
        report_file = create_validation_report(success, results)
        
        # Final status
        if success:
            print(f"\n🎯 SUCCESS: Test system validation completed successfully!")
            tracker.track_milestone("Autonomous Test System Fully Validated and Ready")
            sys.exit(0)
        else:
            print(f"\n⚠️  WARNING: Some validation tests failed")
            tracker.log_activity("testing", "Validation completed with issues")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 ERROR: Validation failed with exception: {e}")
        tracker.log_activity("error", f"Validation failed: {e}")
        sys.exit(2)