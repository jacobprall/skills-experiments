import csv
import os
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from collections import defaultdict


def calculate_similarity(str1, str2):
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def is_create_statement(code_unit):
    if not code_unit or code_unit == 'N/A':
        return False
    return code_unit.strip().upper().startswith('CREATE ')


def process_csv_file(csv_path):
    objects_by_type = defaultdict(list)
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row.get('Category', '').strip()
            code_unit = row.get('CodeUnit', '').strip()
            code_unit_id = row.get('CodeUnitId', '').strip()
            
            if not category or not code_unit or code_unit == 'N/A':
                continue
            
            if not is_create_statement(code_unit):
                continue
            
            if not code_unit_id or code_unit_id == 'N/A':
                continue
            
            objects_by_type[category].append({
                'id': code_unit_id,
                'full_code_unit': code_unit,
                'file_name': row.get('FileName', ''),
                'line_number': row.get('LineNumber', ''),
                'conversion_status': row.get('ConversionStatus', '')
            })
    
    return objects_by_type


def find_nearest_neighbors(objects_by_type, top_k=5):
    results = []
    
    for obj_type, objects in objects_by_type.items():
        if len(objects) <= 1:
            continue
        
        print(f"  Processing {obj_type}: {len(objects)} objects...")
        
        for i, obj in enumerate(objects):
            if i % 50 == 0 and i > 0:
                print(f"    Processed {i}/{len(objects)} objects")
            
            candidates = []
            obj_id_lower = obj['id'].lower()
            
            for j, other_obj in enumerate(objects):
                if i == j:
                    continue
                
                other_id_lower = other_obj['id'].lower()
                
                if len(obj_id_lower) > 3 and len(other_id_lower) > 3:
                    if obj_id_lower[:3] != other_id_lower[:3]:
                        continue
                
                similarity = calculate_similarity(obj['id'], other_obj['id'])
                
                if similarity > 0.3:
                    candidates.append((similarity, other_obj))
            
            candidates.sort(reverse=True, key=lambda x: x[0])
            
            for similarity, neighbor in candidates[:top_k]:
                results.append({
                    'object': obj,
                    'neighbor': neighbor,
                    'type': obj_type,
                    'similarity': similarity,
                    'rank': candidates.index((similarity, neighbor)) + 1
                })
    
    return results


def write_results(results, output_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_folder = Path(output_dir) / f'nearest_neighbors_{timestamp}'
    output_folder.mkdir(parents=True, exist_ok=True)
    
    output_file = output_folder / 'nearest_neighbors.csv'
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'object_type',
            'object_id',
            'object_full_code_unit',
            'object_file',
            'object_line',
            'object_status',
            'nearest_neighbor_id',
            'nearest_neighbor_full_code_unit',
            'nearest_neighbor_file',
            'nearest_neighbor_line',
            'nearest_neighbor_status',
            'similarity_score',
            'rank'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            writer.writerow({
                'object_type': result['type'],
                'object_id': result['object']['id'],
                'object_full_code_unit': result['object']['full_code_unit'],
                'object_file': result['object']['file_name'],
                'object_line': result['object']['line_number'],
                'object_status': result['object']['conversion_status'],
                'nearest_neighbor_id': result['neighbor']['id'],
                'nearest_neighbor_full_code_unit': result['neighbor']['full_code_unit'],
                'nearest_neighbor_file': result['neighbor']['file_name'],
                'nearest_neighbor_line': result['neighbor']['line_number'],
                'nearest_neighbor_status': result['neighbor']['conversion_status'],
                'similarity_score': f"{result['similarity']:.4f}",
                'rank': result['rank']
            })
    
    print(f"Results written to: {output_file}")
    print(f"Total matches found: {len(results)}")
    
    summary_file = output_folder / 'summary.txt'
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Nearest Neighbor Analysis Summary\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total matches: {len(results)}\n\n")
        
        type_counts = {}
        for result in results:
            obj_type = result['type']
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        f.write("Matches by Object Type:\n")
        for obj_type, count in sorted(type_counts.items()):
            f.write(f"  {obj_type}: {count}\n")
    
    print(f"Summary written to: {summary_file}")
    return output_folder


def main():
    csv_path = '/Users/apgupta/WORK/migrations/Customer/Kepler/Convert1105/results/conversions/conversion-2025-11-05-10-24-01/Reports/SnowConvert/TopLevelCodeUnits.20251105.102401.csv'
    output_dir = '/Users/apgupta/WORK/migrations/Customer/Kepler/ai-assessment/nearest-neighbor-by-name'
    
    print(f"Processing CSV file: {csv_path}")
    objects_by_type = process_csv_file(csv_path)
    
    print(f"Found {len(objects_by_type)} object types")
    for obj_type, objects in objects_by_type.items():
        print(f"  {obj_type}: {len(objects)} objects")
    
    print("\nFinding nearest neighbors (top 5 per object)...")
    results = find_nearest_neighbors(objects_by_type, top_k=5)
    
    print("\nWriting results...")
    output_folder = write_results(results, output_dir)
    
    print(f"\nDone! Output folder: {output_folder}")


if __name__ == '__main__':
    main()
