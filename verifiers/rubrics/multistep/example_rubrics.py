# example first responder rubric

from typing import List, Any, Optional

from .requirements import Requirement, BinaryRequirement, Scenario


# First responder workflow - shorter and wider with more branching
scene_safety = BinaryRequirement(
    name="scene_safety", 
    question="Does the response consider if the scene is safe to approach?", 
    dependencies={
        1.0: ["initial_assessment", "vital_signs", "trauma_check"],  # If safe, do parallel assessments
        0.0: []  # If unsafe, stop workflow
    }
)

initial_assessment = BinaryRequirement(
    name="initial_assessment", 
    question="Does the response consider if the patient is conscious and responsive?", 
    dependencies={
        1.0: ["communication", "pain_assessment"],  # If responsive, assess communication and pain
        0.0: ["airway_management", "breathing_support"]  # If unresponsive, prioritize ABCs
    }
)

vital_signs = BinaryRequirement(
    name="vital_signs", 
    question="Does the response consider if the patient's vital signs are stable?", 
    dependencies={
        1.0: ["transport_decision"],  # If stable, consider transport
        0.0: ["immediate_intervention", "emergency_protocols"]  # If unstable, immediate action
    }
)

trauma_check = BinaryRequirement(
    name="trauma_check", 
    question="Does the response consider if there are visible signs of trauma or injury?", 
    dependencies={
        1.0: ["bleeding_control", "immobilization", "injury_assessment"],  # If trauma, multiple interventions
        0.0: ["medical_history", "symptom_assessment"]  # If no trauma, focus on medical causes
    }
)

airway_management = BinaryRequirement(
    name="airway_management", 
    question="Does the response consider if the patient's airway is clear and protected?", 
    dependencies={
        1.0: ["breathing_support"],  # If airway good, check breathing
        0.0: ["emergency_protocols"]  # If airway compromised, emergency
    }
)

breathing_support = BinaryRequirement(
    name="breathing_support", 
    question="Does the response consider if the patient is breathing adequately?", 
    dependencies={
        1.0: ["circulation_check"],  # If breathing good, check circulation
        0.0: ["emergency_protocols"]  # If breathing poor, emergency
    }
)

bleeding_control = BinaryRequirement(
    name="bleeding_control", 
    question="Does the response consider if any significant bleeding has been controlled?", 
    dependencies={
        1.0: ["transport_decision"],  # If bleeding controlled, ready for transport
        0.0: ["emergency_protocols"]  # If bleeding uncontrolled, emergency
    }
)

circulation_check = BinaryRequirement(
    name="circulation_check", 
    question="Does the response consider if the patient has adequate circulation and pulse?", 
    dependencies={
        1.0: ["transport_decision"],  # If circulation good, consider transport
        0.0: ["emergency_protocols"]  # If circulation poor, emergency
    }
)

communication = BinaryRequirement(
    name="communication", 
    question="Does the response consider if the patient can communicate their symptoms clearly?", 
    dependencies={
        1.0: ["symptom_assessment", "medical_history"],  # If can communicate, gather info
        0.0: ["observation_assessment"]  # If can't communicate, rely on observation
    }
)

pain_assessment = BinaryRequirement(
    name="pain_assessment", 
    question="Does the response consider if the patient's pain level has been assessed and managed?", 
    dependencies={
        1.0: ["comfort_measures", "transport_decision"],  # If pain managed, comfort and transport
        0.0: ["pain_management"]  # If pain not managed, intervene
    }
)

immediate_intervention = BinaryRequirement(
    name="immediate_intervention", 
    question="Does the response consider if immediate life-saving interventions have been performed?", 
    dependencies={
        1.0: ["stabilization_check"],  # If interventions done, check stability
        0.0: ["emergency_protocols"]  # If interventions not done, emergency
    }
)

immobilization = BinaryRequirement(
    name="immobilization", 
    question="Does the response consider if the patient has been properly immobilized if needed?", 
    dependencies={
        1.0: ["transport_preparation"],  # If immobilized, prepare for transport
        0.0: ["injury_assessment"]  # If not immobilized, reassess injuries
    }
)

# Terminal nodes (no dependencies)
emergency_protocols = BinaryRequirement(
    name="emergency_protocols", 
    question="Does the response consider if emergency protocols have been activated and followed?"
)

transport_decision = BinaryRequirement(
    name="transport_decision", 
    question="Does the response consider if the appropriate transport decision has been made and executed?"
)

medical_history = BinaryRequirement(
    name="medical_history", 
    question="Does the response consider if relevant medical history has been obtained?"
)

symptom_assessment = BinaryRequirement(
    name="symptom_assessment", 
    question="Does the response consider if the patient's symptoms have been thoroughly assessed?"
)

observation_assessment = BinaryRequirement(
    name="observation_assessment", 
    question="Does the response consider if a thorough observational assessment has been completed?"
)

injury_assessment = BinaryRequirement(
    name="injury_assessment", 
    question="Does the response consider if all injuries have been properly assessed and documented?"
)

comfort_measures = BinaryRequirement(
    name="comfort_measures", 
    question="Does the response consider if appropriate comfort measures have been provided?"
)

pain_management = BinaryRequirement(
    name="pain_management", 
    question="Does the response consider if appropriate pain management has been provided?"
)

stabilization_check = BinaryRequirement(
    name="stabilization_check", 
    question="Does the response consider if the patient has been stabilized successfully?"
)

transport_preparation = BinaryRequirement(
    name="transport_preparation", 
    question="Does the response consider if the patient has been properly prepared for transport?"
)

# List of all requirements for the first responder workflow
first_responder_reqs = [
    scene_safety, initial_assessment, vital_signs, trauma_check,
    airway_management, breathing_support, bleeding_control, circulation_check,
    communication, pain_assessment, immediate_intervention, immobilization,
    emergency_protocols, transport_decision, medical_history, symptom_assessment,
    observation_assessment, injury_assessment, comfort_measures, pain_management,
    stabilization_check, transport_preparation
]



scenarios = [
    Scenario(
        prompt="You are a first responder arriving at a residential street. You come across a patient who is unconscious and not breathing, lying on the sidewalk. There are no immediate hazards visible, no electrical wires down, no fire, and no aggressive bystanders. The area appears secure.",
        completion="First, I'll check if the scene is safe. Since there are no visible hazards, I'll proceed. The patient is unconscious and not breathing, so I'll immediately check their airway and begin CPR. I'll call for advanced life support and continue resuscitation efforts.",
        answers={
            "scene_safety": {"answer": 1.0, "reasoning": "The prompt explicitly states there are no immediate hazards, electrical wires, fire, or aggressive bystanders, and the area appears secure."},
            "initial_assessment": {"answer": 0.0, "reasoning": "The prompt clearly states the patient is unconscious and not breathing, indicating they are completely unresponsive."},
            "airway_management": {"answer": 0.0, "reasoning": "Since the patient is unconscious and not breathing, the airway needs immediate intervention to establish and maintain patency."},
            "breathing_support": {"answer": 0.0, "reasoning": "The prompt explicitly states the patient is not breathing, requiring immediate breathing support through CPR or ventilation."},
            "emergency_protocols": {"answer": 1.0, "reasoning": "The completion mentions beginning CPR and calling for advanced life support, which are appropriate emergency protocols for cardiac arrest."}
        }
    ),
    Scenario(
        prompt="You arrive at a car accident scene on a quiet suburban road. The vehicle has come to rest safely on the shoulder, away from traffic. The patient is conscious, alert, and sitting in the driver's seat but has a deep laceration on their left arm that's bleeding heavily, soaking through their shirt.",
        completion="After confirming scene safety and ensuring no traffic hazards, I'll approach the patient. They're alert and responsive, so I'll introduce myself and explain what I'm doing. I'll immediately apply direct pressure to the arm wound to control bleeding while simultaneously assessing their vital signs and checking for other injuries. Once bleeding is controlled, I'll gather their medical history and symptoms, then prepare them for transport to the hospital.",
        answers={
            "scene_safety": {"answer": 1.0, "reasoning": "The vehicle is safely positioned on the shoulder away from traffic, and the completion confirms scene safety was assessed."},
            "initial_assessment": {"answer": 1.0, "reasoning": "The prompt states the patient is conscious and alert, indicating they are responsive and aware."},
            "trauma_check": {"answer": 1.0, "reasoning": "There is visible trauma in the form of a deep laceration on the arm that's bleeding heavily."},
            "bleeding_control": {"answer": 1.0, "reasoning": "The completion describes applying direct pressure to control the bleeding, which is the appropriate intervention."},
            "communication": {"answer": 1.0, "reasoning": "Since the patient is alert and responsive, they can communicate clearly about their condition and symptoms."},
            "transport_decision": {"answer": 1.0, "reasoning": "A deep laceration requiring bleeding control warrants hospital transport, and the completion mentions preparing for transport."}
        }
    ),
    Scenario(
        prompt="You find an elderly patient (approximately 75 years old) who has fallen in their bathroom. They are awake and oriented but complaining of severe pain in their right hip (8/10 on pain scale) and are completely unable to move their right leg. They describe hearing a 'pop' when they fell. The scene is secure with no ongoing hazards.",
        completion="After ensuring scene safety, I'll assess their level of consciousness - they're alert and oriented. Given the mechanism of injury (fall), their age, the severe hip pain, inability to move the leg, and the audible 'pop', I strongly suspect a hip fracture. I'll assess their current pain level, provide initial pain management if within my scope, and carefully immobilize them in position before any movement. I'll prepare them for transport while providing comfort measures.",
        answers={
            "scene_safety": {"answer": 1.0, "reasoning": "The prompt states the scene is secure with no ongoing hazards."},
            "initial_assessment": {"answer": 1.0, "reasoning": "The patient is described as awake and oriented, indicating they are conscious and responsive."},
            "trauma_check": {"answer": 1.0, "reasoning": "The fall mechanism, severe hip pain, inability to move the leg, and audible 'pop' are clear signs of traumatic injury."},
            "pain_assessment": {"answer": 1.0, "reasoning": "The prompt provides a specific pain rating (8/10) and the completion mentions assessing pain level."},
            "pain_management": {"answer": 1.0, "reasoning": "The completion mentions providing initial pain management within scope of practice."},
            "immobilization": {"answer": 1.0, "reasoning": "The completion specifically mentions carefully immobilizing the patient before movement, appropriate for suspected hip fracture."},
            "transport_preparation": {"answer": 1.0, "reasoning": "Hip fractures require hospital treatment, and the completion mentions preparing for transport with comfort measures."}
        }
    ),
    Scenario(
        prompt="At an active construction site, you receive a call about a worker trapped under a pile of steel beams and concrete debris. Other workers are frantically trying to dig him out. There's heavy equipment still operating nearby, loose materials overhead, and unstable structures. The trapped worker is conscious and calling for help, with visible bleeding from his head and arms.",
        completion="I need to immediately assess scene safety before approaching. This scene has multiple hazards - active heavy equipment, unstable structures, and loose overhead materials that could cause secondary collapse. I cannot safely approach the patient until the scene is secured. I'll coordinate with site supervisors to shut down equipment, establish a safety perimeter, and get proper rescue equipment before attempting patient access.",
        answers={
            "scene_safety": {"answer": 0.0, "reasoning": "The scene has multiple active hazards including operating heavy equipment, unstable structures, loose overhead materials, and risk of secondary collapse, making it unsafe to approach without proper safety measures."}
        }
    )
]