#!/usr/bin/env python3
"""
01_extract_schema.py
IML 파일에서 모든 XML 태그와 속성을 추출하여 스키마 정의

Usage:
    python scripts/01_extract_schema.py
"""

import os
import sys
import json
import codecs
from pathlib import Path
from collections import defaultdict
from xml.etree import ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Set, List, Tuple, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Constants
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "schemas"


def read_iml_file(file_path: Path) -> str:
    """Read IML file with EUC-KR encoding and convert to UTF-8."""
    encodings = ['euc-kr', 'cp949', 'utf-8']

    for encoding in encodings:
        try:
            with codecs.open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception:
            continue

    return None


def extract_tags_from_xml(xml_content: str) -> Tuple[Dict[str, Set[str]], Dict[str, Dict[str, Set[str]]], Dict[str, Set[str]]]:
    """
    Extract all tags, attributes, and hierarchy from XML content.

    Returns:
        - tags: {tag_name: set of parent tags}
        - attributes: {tag_name: {attr_name: set of sample values}}
        - tag_children: {tag_name: set of child tags}
    """
    tags = defaultdict(set)
    attributes = defaultdict(lambda: defaultdict(set))
    tag_children = defaultdict(set)

    try:
        root = ET.fromstring(xml_content)

        def traverse(element, parent_tag=None):
            tag = element.tag

            # Record parent relationship
            if parent_tag:
                tags[tag].add(parent_tag)
                tag_children[parent_tag].add(tag)
            else:
                tags[tag].add("ROOT")

            # Record attributes
            for attr_name, attr_value in element.attrib.items():
                # Store sample values (limit to 10 per attribute)
                if len(attributes[tag][attr_name]) < 10:
                    # Truncate long values
                    if len(attr_value) > 100:
                        attr_value = attr_value[:100] + "..."
                    attributes[tag][attr_name].add(attr_value)

            # Traverse children
            for child in element:
                traverse(child, tag)

        traverse(root)

    except ET.ParseError as e:
        # Try to recover from malformed XML
        pass
    except Exception as e:
        pass

    return tags, attributes, tag_children


def process_single_file(file_path: Path) -> Tuple[Dict, Dict, Dict, bool]:
    """Process a single IML file and extract schema information."""
    content = read_iml_file(file_path)
    if content is None:
        return {}, {}, {}, False

    tags, attributes, tag_children = extract_tags_from_xml(content)

    # Convert sets to lists for JSON serialization later
    tags_dict = {k: list(v) for k, v in tags.items()}
    attrs_dict = {k: {ak: list(av) for ak, av in v.items()} for k, v in attributes.items()}
    children_dict = {k: list(v) for k, v in tag_children.items()}

    return tags_dict, attrs_dict, children_dict, True


def merge_schemas(all_tags: List[Dict], all_attrs: List[Dict], all_children: List[Dict]) -> Tuple[Dict, Dict, Dict]:
    """Merge schema information from multiple files."""
    merged_tags = defaultdict(set)
    merged_attrs = defaultdict(lambda: defaultdict(set))
    merged_children = defaultdict(set)

    for tags in all_tags:
        for tag, parents in tags.items():
            merged_tags[tag].update(parents)

    for attrs in all_attrs:
        for tag, tag_attrs in attrs.items():
            for attr_name, values in tag_attrs.items():
                # Limit samples to 20 per attribute
                current = merged_attrs[tag][attr_name]
                for v in values:
                    if len(current) < 20:
                        current.add(v)

    for children in all_children:
        for tag, child_tags in children.items():
            merged_children[tag].update(child_tags)

    return merged_tags, merged_attrs, merged_children


def find_iml_files(data_dir: Path) -> List[Path]:
    """Find all IML files in the data directory."""
    iml_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.lower().endswith('.iml'):
                iml_files.append(Path(root) / file)
    return iml_files


def main():
    print("=" * 60)
    print("IML Schema Extraction")
    print("=" * 60)

    # Find all IML files
    print(f"\n[1/4] Scanning for IML files in {DATA_DIR}...")
    iml_files = find_iml_files(DATA_DIR)
    print(f"      Found {len(iml_files):,} IML files")

    if not iml_files:
        print("ERROR: No IML files found!")
        return

    # Process files
    print(f"\n[2/4] Extracting schema from files...")

    all_tags = []
    all_attrs = []
    all_children = []
    success_count = 0
    error_count = 0

    # Process with progress indicator
    total = len(iml_files)
    for i, file_path in enumerate(iml_files):
        if (i + 1) % 500 == 0 or i == 0 or i == total - 1:
            print(f"      Processing: {i + 1:,}/{total:,} ({(i+1)/total*100:.1f}%)")

        tags, attrs, children, success = process_single_file(file_path)

        if success:
            all_tags.append(tags)
            all_attrs.append(attrs)
            all_children.append(children)
            success_count += 1
        else:
            error_count += 1

    print(f"      Success: {success_count:,}, Errors: {error_count:,}")

    # Merge schemas
    print(f"\n[3/4] Merging schema information...")
    merged_tags, merged_attrs, merged_children = merge_schemas(all_tags, all_attrs, all_children)

    # Convert to serializable format
    tags_output = {
        "total_tags": len(merged_tags),
        "tags": {
            tag: {
                "parents": sorted(list(parents)),
                "children": sorted(list(merged_children.get(tag, set())))
            }
            for tag, parents in sorted(merged_tags.items())
        }
    }

    attrs_output = {
        "total_tags_with_attributes": len(merged_attrs),
        "attributes": {
            tag: {
                attr: {
                    "sample_values": sorted(list(values)),
                    "sample_count": len(values)
                }
                for attr, values in sorted(tag_attrs.items())
            }
            for tag, tag_attrs in sorted(merged_attrs.items())
        }
    }

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save schemas
    print(f"\n[4/4] Saving schemas to {OUTPUT_DIR}...")

    tags_file = OUTPUT_DIR / "iml_tags.json"
    with open(tags_file, 'w', encoding='utf-8') as f:
        json.dump(tags_output, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {tags_file}")

    attrs_file = OUTPUT_DIR / "iml_attributes.json"
    with open(attrs_file, 'w', encoding='utf-8') as f:
        json.dump(attrs_output, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {attrs_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("Schema Extraction Summary")
    print("=" * 60)
    print(f"  Total IML files processed: {success_count:,}")
    print(f"  Total unique tags: {len(merged_tags)}")
    print(f"  Tags with attributes: {len(merged_attrs)}")

    print("\n  Top-level tags (under ROOT):")
    root_children = [tag for tag, parents in merged_tags.items() if "ROOT" in parents]
    for tag in sorted(root_children):
        print(f"    - {tag}")

    print("\n  Tags with most attributes:")
    attr_counts = [(tag, len(attrs)) for tag, attrs in merged_attrs.items()]
    attr_counts.sort(key=lambda x: -x[1])
    for tag, count in attr_counts[:10]:
        print(f"    - {tag}: {count} attributes")

    print("\n" + "=" * 60)
    print("Schema extraction completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
