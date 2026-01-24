"""
Test file to verify BOM upload validation works correctly.
Run this in the frontend directory to test the validation logic.
"""

import pandas as pd
from io import BytesIO
import sys

# Mock the validation function (copied from app.py for testing)
def validate_bom_structure(df, filename):
    """
    Comprehensive BOM file format and structure validation.
    
    Returns:
        tuple: (is_valid, error_messages_list)
    """
    errors = []
    
    # 1. Check for empty file
    if df.empty:
        errors.append("File is empty. Please upload a file with data rows.")
        return False, errors
    
    # 2. Check for minimum required columns
    STANDARD_COLUMNS = [
        'sku', 'product', 'component', 'component_description',
        'subcomponent', 'subcomponent_description', 'material', 'material_name'
    ]
    
    df_cols_normalized = [str(col).strip().replace('\n', '').replace('\r', '').replace(' ', '_').lower() 
                          for col in df.columns]
    missing_cols = [col for col in STANDARD_COLUMNS if col not in df_cols_normalized]
    
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}. "
                      f"Please ensure your file matches the standard BOM template.")
        return False, errors
    
    # 3. Check for no data rows (only headers)
    if len(df) == 0:
        errors.append("File contains headers but no data rows.")
        return False, errors
    
    # 4. Check for empty string, NaN, or all-whitespace values in critical fields
    critical_fields = ['sku', 'component', 'subcomponent', 'material']
    
    for idx, row in df.iterrows():
        row_num = idx + 2  # +2 because row 1 is header in Excel/CSV, +1 for 1-based indexing
        
        for field in critical_fields:
            val = str(row[field]).strip() if pd.notna(row[field]) else ""
            
            # Check for empty, 'nan', or whitespace-only values
            if not val or val.lower() == 'nan':
                errors.append(f"Row {row_num}: Required field '{field}' is empty or invalid.")
            
            # Check for non-printable or suspicious characters
            if val and not all(c.isprintable() or c.isspace() for c in val):
                errors.append(f"Row {row_num}: Field '{field}' contains non-printable characters.")
    
    # 5. Check for duplicate rows (based on composite key)
    composite_key = ['sku', 'component', 'subcomponent', 'material']
    duplicates = df.duplicated(subset=composite_key, keep=False)
    
    if duplicates.any():
        dup_rows = df[duplicates].index.tolist()
        dup_row_nums = [str(idx + 2) for idx in dup_rows]  # Convert to 1-based row numbers
        errors.append(f"Duplicate entries found in rows: {', '.join(dup_row_nums)}. "
                      f"Each (SKU, Component, Subcomponent, Material) combination must be unique.")
    
    # 6. Check data type consistency (all should be string-convertible)
    for idx, row in df.iterrows():
        row_num = idx + 2
        for col in df.columns:
            val = row[col]
            try:
                str(val)  # Attempt string conversion
            except Exception as e:
                errors.append(f"Row {row_num}: Column '{col}' contains data that cannot be converted to text.")
    
    # 7. Check for excessive whitespace or formatting issues
    for idx, row in df.iterrows():
        row_num = idx + 2
        for col in STANDARD_COLUMNS:
            if col in df.columns:
                val = str(row[col]).strip() if pd.notna(row[col]) else ""
                
                # Check for excessive leading/trailing spaces (after strip, these shouldn't exist)
                if len(str(row[col])) > len(val) + 10:  # Allow some padding
                    errors.append(f"Row {row_num}: Column '{col}' has excessive whitespace. "
                                  f"Please clean up formatting.")
    
    # 8. Check for file size reasonableness (warn if > 10k rows)
    if len(df) > 10000:
        errors.append(f"File contains {len(df):,} rows, which is very large. "
                      f"Consider splitting into smaller files for better performance.")
    
    return len(errors) == 0, errors


# Test cases
def test_valid_bom():
    """Test a valid BOM file"""
    print("Test 1: Valid BOM file...")
    df = pd.DataFrame({
        'sku': ['SKU001', 'SKU002'],
        'product': ['Product A', 'Product B'],
        'component': ['COMP1', 'COMP2'],
        'component_description': ['Desc1', 'Desc2'],
        'subcomponent': ['SC1', 'SC2'],
        'subcomponent_description': ['SDes1', 'SDes2'],
        'material': ['MAT1', 'MAT2'],
        'material_name': ['Material 1', 'Material 2']
    })
    is_valid, errors = validate_bom_structure(df, 'test.csv')
    assert is_valid, f"Expected valid, got errors: {errors}"
    print("✓ PASS: Valid BOM accepted\n")


def test_missing_columns():
    """Test file with missing columns"""
    print("Test 2: Missing required columns...")
    df = pd.DataFrame({
        'sku': ['SKU001'],
        'product': ['Product A'],
        'component': ['COMP1']
        # Missing other columns
    })
    is_valid, errors = validate_bom_structure(df, 'test.csv')
    assert not is_valid, "Expected invalid"
    assert any('Missing required columns' in e for e in errors), f"Expected missing columns error, got: {errors}"
    print(f"✓ PASS: Missing columns detected - {errors[0][:80]}...\n")


def test_empty_critical_field():
    """Test file with empty critical field"""
    print("Test 3: Empty critical field...")
    df = pd.DataFrame({
        'sku': ['SKU001', ''],  # Empty SKU
        'product': ['Product A', 'Product B'],
        'component': ['COMP1', 'COMP2'],
        'component_description': ['Desc1', 'Desc2'],
        'subcomponent': ['SC1', 'SC2'],
        'subcomponent_description': ['SDes1', 'SDes2'],
        'material': ['MAT1', 'MAT2'],
        'material_name': ['Material 1', 'Material 2']
    })
    is_valid, errors = validate_bom_structure(df, 'test.csv')
    assert not is_valid, "Expected invalid"
    assert any('empty or invalid' in e.lower() for e in errors), f"Expected empty field error, got: {errors}"
    print(f"✓ PASS: Empty field detected - {errors[0][:80]}...\n")


def test_duplicate_rows():
    """Test file with duplicate composite keys"""
    print("Test 4: Duplicate rows...")
    df = pd.DataFrame({
        'sku': ['SKU001', 'SKU001'],
        'product': ['Product A', 'Product A'],
        'component': ['COMP1', 'COMP1'],
        'component_description': ['Desc1', 'Desc1'],
        'subcomponent': ['SC1', 'SC1'],
        'subcomponent_description': ['SDes1', 'SDes1'],
        'material': ['MAT1', 'MAT1'],  # Same composite key
        'material_name': ['Material 1', 'Material 1']
    })
    is_valid, errors = validate_bom_structure(df, 'test.csv')
    assert not is_valid, "Expected invalid"
    assert any('Duplicate entries' in e for e in errors), f"Expected duplicate error, got: {errors}"
    print(f"✓ PASS: Duplicate rows detected - {errors[0][:80]}...\n")


def test_nan_values():
    """Test file with NaN values in critical fields"""
    print("Test 5: NaN values in critical fields...")
    df = pd.DataFrame({
        'sku': ['SKU001', 'SKU002'],
        'product': ['Product A', 'Product B'],
        'component': [float('nan'), 'COMP2'],  # NaN value
        'component_description': ['Desc1', 'Desc2'],
        'subcomponent': ['SC1', 'SC2'],
        'subcomponent_description': ['SDes1', 'SDes2'],
        'material': ['MAT1', 'MAT2'],
        'material_name': ['Material 1', 'Material 2']
    })
    is_valid, errors = validate_bom_structure(df, 'test.csv')
    assert not is_valid, "Expected invalid"
    assert any('empty or invalid' in e.lower() for e in errors), f"Expected NaN error, got: {errors}"
    print(f"✓ PASS: NaN values detected - {errors[0][:80]}...\n")


def test_large_file():
    """Test file with 10,000+ rows (should warn)"""
    print("Test 6: Large file (10k+ rows)...")
    data = {
        'sku': [f'SKU{i:04d}' for i in range(10001)],
        'product': [f'Product {i}' for i in range(10001)],
        'component': [f'COMP{i}' for i in range(10001)],
        'component_description': [f'Desc{i}' for i in range(10001)],
        'subcomponent': [f'SC{i}' for i in range(10001)],
        'subcomponent_description': [f'SDes{i}' for i in range(10001)],
        'material': [f'MAT{i}' for i in range(10001)],
        'material_name': [f'Material {i}' for i in range(10001)]
    }
    df = pd.DataFrame(data)
    is_valid, errors = validate_bom_structure(df, 'test.csv')
    assert not is_valid, "Expected warning (invalid) for large file"
    assert any('very large' in e.lower() for e in errors), f"Expected large file warning, got: {errors}"
    print(f"✓ PASS: Large file warning - {errors[0][:80]}...\n")


if __name__ == '__main__':
    print("=" * 80)
    print("BOM VALIDATION TEST SUITE")
    print("=" * 80 + "\n")
    
    try:
        test_valid_bom()
        test_missing_columns()
        test_empty_critical_field()
        test_duplicate_rows()
        test_nan_values()
        test_large_file()
        
        print("=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
