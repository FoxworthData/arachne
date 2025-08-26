#!/usr/bin/env python3
"""
Test script to validate that the browser persona fix is working correctly.
This tests that only Chrome personas are selected and that header/runtime consistency is maintained.
"""

import sys
import os
import hashlib

# Add the current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from walmart_home_page import BrowserPersonaChooser, BrowserPersona

def test_persona_selection():
    """Test that only Chrome personas are available."""
    print("🧪 Testing Browser Persona Selection Fix")
    print("=" * 60)
    
    chooser = BrowserPersonaChooser()
    
    # Test multiple random selections to ensure all are Chrome
    print("📋 Testing 10 random persona selections:")
    chrome_count = 0
    non_chrome_count = 0
    
    for i in range(10):
        persona = chooser.get_random_persona()
        
        # Check if it's a Chrome persona
        is_chrome = "Chrome" in persona.user_agent
        is_safari = "Safari" in persona.user_agent and "Chrome" not in persona.user_agent
        is_firefox = "Firefox" in persona.user_agent
        
        if is_chrome:
            chrome_count += 1
            print(f"   {i+1:2d}. ✅ Chrome persona: {persona.persona_id}")
        elif is_safari:
            non_chrome_count += 1
            print(f"   {i+1:2d}. ❌ Safari persona detected: {persona.persona_id}")
        elif is_firefox:
            non_chrome_count += 1
            print(f"   {i+1:2d}. ❌ Firefox persona detected: {persona.persona_id}")
        else:
            non_chrome_count += 1
            print(f"   {i+1:2d}. ❓ Unknown persona: {persona.persona_id}")
        
        # Also check the sec-ch-ua header consistency
        if "Google Chrome" in persona.sec_ch_ua or "Chromium" in persona.sec_ch_ua:
            print(f"       ✅ sec-ch-ua header consistent: {persona.sec_ch_ua}")
        else:
            print(f"       ❌ sec-ch-ua header inconsistent: {persona.sec_ch_ua}")
    
    print()
    print(f"📊 Results Summary:")
    print(f"   ✅ Chrome personas: {chrome_count}/10")
    print(f"   ❌ Non-Chrome personas: {non_chrome_count}/10")
    
    if non_chrome_count == 0:
        print("🎉 SUCCESS: All personas are Chrome-based, compatible with Playwright's Chromium engine!")
        return True
    else:
        print("💥 FAILURE: Found non-Chrome personas that will cause header/runtime mismatches!")
        return False

def test_persona_id_generation():
    """Test that persona ID generation works for all supported types."""
    print("\n🧪 Testing Persona ID Generation")
    print("=" * 60)
    
    test_user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    ]
    
    expected_prefixes = ["chrome-win", "chrome-mac", "chrome-linux"]
    
    all_correct = True
    
    for i, ua in enumerate(test_user_agents):
        persona_id = BrowserPersona.generate_persona_id(ua)
        expected_prefix = expected_prefixes[i]
        
        if persona_id.startswith(expected_prefix):
            print(f"   ✅ {expected_prefix}: {persona_id}")
        else:
            print(f"   ❌ Expected {expected_prefix}, got: {persona_id}")
            all_correct = False
    
    if all_correct:
        print("🎉 SUCCESS: All persona IDs generated correctly!")
        return True
    else:
        print("💥 FAILURE: Some persona IDs generated incorrectly!")
        return False

def test_available_personas():
    """Test that we have the expected Chrome personas available."""
    print("\n🧪 Testing Available Personas")
    print("=" * 60)
    
    chooser = BrowserPersonaChooser()
    personas_data = chooser._personas_data
    
    print(f"📊 Total personas available: {len(personas_data)}")
    
    expected_platforms = {"Windows", "macOS", "Linux"}
    found_platforms = set()
    
    for i, persona_data in enumerate(personas_data, 1):
        user_agent = persona_data["user_agent"]
        platform = persona_data["sec_ch_ua_platform"].strip('"')
        
        found_platforms.add(platform)
        
        print(f"   {i}. Platform: {platform}")
        print(f"      User-Agent: {user_agent[:60]}...")
        print(f"      sec-ch-ua: {persona_data['sec_ch_ua']}")
        print(f"      Viewport: {persona_data['viewport_width']}x{persona_data['viewport_height']}")
        print()
    
    missing_platforms = expected_platforms - found_platforms
    extra_platforms = found_platforms - expected_platforms
    
    if not missing_platforms and not extra_platforms:
        print("🎉 SUCCESS: All expected Chrome platforms available!")
        return True
    else:
        if missing_platforms:
            print(f"❌ Missing platforms: {missing_platforms}")
        if extra_platforms:
            print(f"❓ Unexpected platforms: {extra_platforms}")
        return False

def main():
    """Run all tests."""
    print("🚀 Browser Persona Fix Validation")
    print("=" * 80)
    print("This test validates that the Chrome-only persona fix is working correctly")
    print("and that we no longer have Safari personas causing header/runtime mismatches.")
    print()
    
    # Run all tests
    test1_passed = test_persona_selection()
    test2_passed = test_persona_id_generation()
    test3_passed = test_available_personas()
    
    print("\n" + "=" * 80)
    print("📈 FINAL RESULTS")
    print("=" * 80)
    
    if all([test1_passed, test2_passed, test3_passed]):
        print("🎉 ALL TESTS PASSED!")
        print("✅ The browser persona fix is working correctly.")
        print("✅ Only Chrome personas are available.")
        print("✅ No header/runtime mismatches should occur.")
        print("✅ Bot detection due to browser fingerprinting inconsistencies should be eliminated.")
        return 0
    else:
        print("💥 SOME TESTS FAILED!")
        print("❌ The browser persona fix needs additional work.")
        return 1

if __name__ == "__main__":
    sys.exit(main())