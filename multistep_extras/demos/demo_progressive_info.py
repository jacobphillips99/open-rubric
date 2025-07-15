"""
Demonstration of progressive information revelation in multistep environments.

This script shows how information is progressively revealed as requirements are satisfied,
creating a more realistic and engaging interactive experience.
"""

from verifiers.rubrics.multistep.scenario import Scenario


def create_progressive_scenario() -> Scenario:
    """Create a scenario that demonstrates progressive information revelation."""
    return Scenario(
        name="Progressive Emergency Response",
        description="First responder scenario with progressive information revelation",
        prompt="You are a first responder arriving at a scene. A person is on the ground. Your view is limited.",
        answers={
            "scene_safety": {"answer": 1.0, "reasoning": "Scene is assessed as safe"},
            "initial_assessment": {"answer": 0.0, "reasoning": "Patient is unconscious"},
            "breathing_support": {"answer": 0.0, "reasoning": "Patient needs breathing support"},
            "emergency_protocols": {"answer": 1.0, "reasoning": "Emergency protocols initiated"}
        },
        revealed_info={
            "scene_safety": {
                "1.0": "🔍 Scene Assessment: The area is secure. No traffic, electrical hazards, or dangerous individuals present. Safe to approach.",
                "0.0": "⚠️ Scene Assessment: Multiple hazards detected. Do not approach until scene is secured."
            },
            "initial_assessment": {
                "1.0": "👤 Patient Status: Adult male, conscious and alert. Responsive to voice, tracking movement with eyes.",
                "0.0": "👤 Patient Status: Adult male, unconscious. Eyes closed, no response to verbal stimuli. Appears critical."
            },
            "breathing_support": {
                "1.0": "💨 Breathing Assessment: Patient breathing normally, clear chest rise and fall. No distress.",
                "0.0": "💨 Breathing Assessment: Inadequate breathing detected. Shallow, irregular pattern. Immediate intervention needed."
            },
            "emergency_protocols": {
                "1.0": "📞 Emergency Response: Emergency services contacted. Advanced life support en route. Protocols active.",
                "0.0": "📞 Emergency Response: Emergency protocols not yet initiated. Critical time window."
            }
        }
    )


def demo_progressive_revelation():
    """Demonstrate how progressive information revelation works."""
    scenario = create_progressive_scenario()
    
    print("🎯 PROGRESSIVE INFORMATION REVELATION DEMO")
    print("=" * 50)
    print()
    
    print("📝 Initial Scenario:")
    print(f"   {scenario.prompt}")
    print()
    
    print("🔄 Progressive Information Flow:")
    print()
    
    # Simulate the progression through requirements
    requirements = ["scene_safety", "initial_assessment", "breathing_support", "emergency_protocols"]
    
    for i, req in enumerate(requirements, 1):
        print(f"Step {i}: {req}")
        
        # Get the answer for this requirement
        answer_data = scenario.answers.get(req, {})
        score = answer_data.get("answer", 0.0)
        reasoning = answer_data.get("reasoning", "")
        
        print(f"   Assessment: {reasoning} (Score: {score})")
        
        # Show revealed information
        if req in scenario.revealed_info:
            score_key = str(float(score))
            if score_key in scenario.revealed_info[req]:
                revealed_info = scenario.revealed_info[req][score_key]
                print(f"   {revealed_info}")
        
        print()
    
    print("✅ Progressive information revelation creates a more engaging")
    print("   and realistic emergency response training experience!")


if __name__ == "__main__":
    demo_progressive_revelation() 