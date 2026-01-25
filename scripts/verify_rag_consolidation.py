#!/usr/bin/env python3
"""
Verification Script: RAG Pipeline Consolidation
================================================
Validates that RAG-based LLM pipeline writes to ppwr_result table.

Tests performed:
1. PPWRAssessment class removed from models
2. Imports correctly updated (extract_regulatory_mentions_windows added)
3. RAG endpoint uses PPWRResult instead of PPWRAssessment
4. parse_ppwr_output returns ppwr_result-compatible schema
5. No references to PPWRAssessment remain in codebase
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ppwr_assessment_removed():
    """Test 1: Verify PPWRAssessment class no longer exists in models.py"""
    print("Test 1: Checking PPWRAssessment class removed...")
    
    models_path = Path(__file__).parent.parent / "backend" / "models.py"
    content = models_path.read_text()
    
    if "class PPWRAssessment" in content:
        print("  ❌ FAILED: PPWRAssessment class still exists in models.py")
        return False
    
    print("  ✅ PASSED: PPWRAssessment class successfully removed")
    return True

def test_extract_regulatory_import():
    """Test 2: Verify extract_regulatory_mentions_windows import added"""
    print("Test 2: Checking extract_regulatory_mentions_windows import...")
    
    main_path = Path(__file__).parent.parent / "backend" / "main.py"
    content = main_path.read_text()
    
    if "from backend.pipeline import initialize_azure_models, run_ppwr_pipeline, extract_regulatory_mentions_windows" not in content:
        print("  ❌ FAILED: extract_regulatory_mentions_windows not in imports")
        return False
    
    print("  ✅ PASSED: extract_regulatory_mentions_windows import added")
    return True

def test_rag_endpoint_uses_ppwr_result():
    """Test 3: Verify RAG endpoint writes to PPWRResult table"""
    print("Test 3: Checking RAG endpoint uses PPWRResult...")
    
    main_path = Path(__file__).parent.parent / "backend" / "main.py"
    content = main_path.read_text()
    
    # Check for PPWRResult usage in /ppwr/assess endpoint
    if "session.query(PPWRResult).filter_by(material_id=mid)" not in content:
        print("  ❌ FAILED: RAG endpoint not using PPWRResult")
        return False
    
    # Check for old PPWRAssessment usage (should not exist)
    if "session.query(PPWRAssessment)" in content:
        print("  ❌ FAILED: RAG endpoint still using PPWRAssessment")
        return False
    
    print("  ✅ PASSED: RAG endpoint correctly uses PPWRResult")
    return True

def test_parse_ppwr_output_schema():
    """Test 4: Verify parse_ppwr_output returns ppwr_result schema"""
    print("Test 4: Checking parse_ppwr_output schema...")
    
    parse_path = Path(__file__).parent.parent / "backend" / "parse_llm.py"
    content = parse_path.read_text()
    
    # Check for ppwr_result compatible keys in output
    required_keys = ["material_id", "supplier_name", "cas_id", "chemical", "concentration", "status"]
    
    for key in required_keys:
        if f"'{key}':" not in content:
            print(f"  ❌ FAILED: Missing key '{key}' in parse_ppwr_output")
            return False
    
    # Check docstring mentions ppwr_result
    if "ppwr_result table schema" not in content:
        print("  ⚠️ WARNING: parse_ppwr_output docstring doesn't mention ppwr_result")
    
    print("  ✅ PASSED: parse_ppwr_output returns ppwr_result-compatible schema")
    return True

def test_no_remaining_references():
    """Test 5: Verify no remaining references to PPWRAssessment"""
    print("Test 5: Checking for remaining PPWRAssessment references...")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    references_found = []
    
    for py_file in backend_dir.rglob("*.py"):
        if py_file.name == "__pycache__":
            continue
        
        content = py_file.read_text()
        
        # Allow comment references (documentation)
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if "PPWRAssessment" in line and not line.strip().startswith('#'):
                references_found.append((py_file.name, i, line.strip()))
    
    if references_found:
        print(f"  ⚠️ WARNING: Found {len(references_found)} non-comment references:")
        for fname, lineno, line in references_found:
            print(f"    {fname}:{lineno} - {line[:80]}")
        return False
    
    print("  ✅ PASSED: No remaining code references to PPWRAssessment")
    return True

def test_schema_mapping_logic():
    """Test 6: Verify schema mapping logic in RAG endpoint"""
    print("Test 6: Checking schema mapping logic...")
    
    main_path = Path(__file__).parent.parent / "backend" / "main.py"
    content = main_path.read_text()
    
    # Check for key mapping operations
    checks = [
        ("Join restricted substances", "', '.join(restricted_list)"),
        ("Status mapping", "status = 'Compliant' if ppwr_compliant else 'Non-Compliant'"),
        ("Concentration mapping", "rec.get('recycled_content_percent')"),
        ("Chemical field", "'chemical': chemical"),
        ("Status field", "'status': status")
    ]
    
    all_passed = True
    for check_name, check_str in checks:
        if check_str not in content:
            print(f"  ❌ FAILED: Missing {check_name} logic")
            all_passed = False
    
    if all_passed:
        print("  ✅ PASSED: Schema mapping logic present")
    
    return all_passed

def run_all_tests():
    """Run all verification tests"""
    print("=" * 70)
    print("RAG Pipeline Consolidation Verification")
    print("=" * 70)
    print()
    
    tests = [
        test_ppwr_assessment_removed,
        test_extract_regulatory_import,
        test_rag_endpoint_uses_ppwr_result,
        test_parse_ppwr_output_schema,
        test_no_remaining_references,
        test_schema_mapping_logic
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ ERROR: Test failed with exception: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 70)
    print(f"SUMMARY: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("🎉 All tests passed! RAG pipeline consolidation complete.")
        print()
        print("Next steps:")
        print("  1. Rebuild Docker containers: docker-compose down && docker-compose up --build -d")
        print("  2. Apply database migration: python frontend/run_migrations.py")
        print("  3. Test RAG pipeline:")
        print("     - Upload PPWR declaration PDF")
        print("     - Click 'Evaluate Selected'")
        print("     - Verify results in /ppwr/evaluation page")
        return 0
    else:
        print(f"⚠️ {total - passed} test(s) failed. Review output above.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
