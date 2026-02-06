#!/usr/bin/env python3
"""
Add Geometric Elements and Starting Diagram to deconstruct_parallel_symbols.json
Copies geometric elements and starting diagram from math_solution_standard.json
"""

import json
from pathlib import Path

def add_geometric_elements_to_timing():
    """Add geometric elements and starting diagram to the timing JSON file."""
    
    # File paths - updated for current directory structure
    timing_file = Path("deconstruct_parallel_symbols.json")
    geometric_file = Path("math_solution_pipeline/math_solution_standard.json")
    output_file = Path("geometric_elements_with_timing.json")
    
    print("📂 Loading files...")
    
    # Load timing data
    try:
        with open(timing_file, 'r', encoding='utf-8') as f:
            timing_data = json.load(f)
        print(f"✅ Loaded timing data from: {timing_file}")
    except Exception as e:
        print(f"❌ Error loading timing file: {e}")
        return False
    
    # Load geometric data
    try:
        with open(geometric_file, 'r', encoding='utf-8') as f:
            geometric_data = json.load(f)
        print(f"✅ Loaded geometric data from: {geometric_file}")
    except Exception as e:
        print(f"❌ Error loading geometric file: {e}")
        return False
    
    # Create lookup for geometric data
    geometric_lookup = {step.get("step_id"): step for step in geometric_data.get("solution_steps", [])}
    
    print("🔧 Processing steps...")
    
    # Process each step in timing data
    for timing_step in timing_data.get("solution_steps", []):
        step_id = timing_step.get("step_id")
        geometric_step = geometric_lookup.get(step_id, {})
        
        print(f"   📋 Processing step: {step_id}")
        
        # Add starting_diagram to the step (as is from math_solution_standard.json)
        starting_diagram = geometric_step.get("starting_diagram", [])
        if starting_diagram:
            timing_step["starting_diagram"] = starting_diagram
            print(f"      🎬 Added {len(starting_diagram)} starting diagram elements")
        
        # Process sentences
        timing_sentences = timing_step.get("sentences", [])
        geometric_sentences = geometric_step.get("sentences", [])
        
        for i, timing_sentence in enumerate(timing_sentences):
            geometric_sentence = geometric_sentences[i] if i < len(geometric_sentences) else {}
            
            # Use text from geometric_sentence (math_solution_standard.json) instead of timing_sentence
            standard_text = geometric_sentence.get("text", timing_sentence.get("text", ""))
            timing_sentence["text"] = standard_text
            
            # Add khan_academy_text from geometric_sentence
            khan_academy_text = geometric_sentence.get("khan_academy_text", "")
            timing_sentence["khan_academy_text"] = khan_academy_text
            
            # Add geometric_elements to the sentence (without start_time_seconds)
            original_elements = geometric_sentence.get("geometric_elements", [])
            simplified_elements = []
            
            for element in original_elements:
                if element and any(element.values()):
                    simplified_element = {
                        "element_type": element.get("element_type", ""),
                        "element_id": element.get("element_id", ""),
                        "animation_type": element.get("animation_type", "")
                        # No start_time_seconds field
                    }
                    simplified_elements.append(simplified_element)
                else:
                    simplified_elements.append({})
            
            timing_sentence["geometric_elements"] = simplified_elements
            
            # Count valid elements
            valid_elements = [e for e in simplified_elements if e and any(e.values())]
            if valid_elements:
                print(f"      📝 Sentence {i+1}: {len(valid_elements)} geometric elements")
    
    # Save the modified data
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(timing_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Successfully created: {output_file}")
        print("✅ Added geometric elements and starting diagram to timing data")
        
        # Show summary
        total_steps = len(timing_data.get("solution_steps", []))
        total_sentences = sum(len(step.get("sentences", [])) for step in timing_data.get("solution_steps", []))
        total_starting_elements = sum(len(step.get("starting_diagram", [])) for step in timing_data.get("solution_steps", []))
        
        print(f"\n📊 Summary:")
        print(f"   • Steps processed: {total_steps}")
        print(f"   • Sentences processed: {total_sentences}")
        print(f"   • Starting diagram elements: {total_starting_elements}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving output file: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Adding Geometric Elements to Timing Data")
    print("="*50)
    
    success = add_geometric_elements_to_timing()
    
    if success:
        print("\n✨ SUCCESS! Timing data now includes geometric elements and starting diagram.")
    else:
        print("\n❌ FAILED! Check the error messages above.")
