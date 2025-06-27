# example first responder rubric

from typing import List, Any, Optional

from verifiers.rewards.judge_reward import JudgeResponseFormat, binary_judge_response_format

class Requirement:
    def __init__(self, name: str, question: str, judge_response_format: JudgeResponseFormat, dependencies: Optional[dict[float, list[str]]] = None):
        self.name = name
        self.question = question
        self.dependencies = dependencies
        self.judge_response_format = judge_response_format

        if dependencies is not None:
            assert all(d in judge_response_format.options for d in dependencies.keys())

    def terminal(self):
        return self.dependencies is None
    
class BinaryRequirement(Requirement):
    def __init__(self, name: str, question: str, dependencies: Optional[dict[float, list[str]]] = None):
        super().__init__(name, question, binary_judge_response_format, dependencies)


# First responder workflow - shorter and wider with more branching
scene_safety = BinaryRequirement(
    name="scene_safety", 
    question="Is the scene safe to approach?", 
    dependencies={
        1.0: ["initial_assessment", "vital_signs", "trauma_check"],  # If safe, do parallel assessments
        0.0: []  # If unsafe, stop workflow
    }
)

initial_assessment = BinaryRequirement(
    name="initial_assessment", 
    question="Is the patient conscious and responsive?", 
    dependencies={
        1.0: ["communication", "pain_assessment"],  # If responsive, assess communication and pain
        0.0: ["airway_management", "breathing_support"]  # If unresponsive, prioritize ABCs
    }
)

vital_signs = BinaryRequirement(
    name="vital_signs", 
    question="Are the patient's vital signs stable?", 
    dependencies={
        1.0: ["transport_decision"],  # If stable, consider transport
        0.0: ["immediate_intervention", "emergency_protocols"]  # If unstable, immediate action
    }
)

trauma_check = BinaryRequirement(
    name="trauma_check", 
    question="Are there visible signs of trauma or injury?", 
    dependencies={
        1.0: ["bleeding_control", "immobilization", "injury_assessment"],  # If trauma, multiple interventions
        0.0: ["medical_history", "symptom_assessment"]  # If no trauma, focus on medical causes
    }
)

airway_management = BinaryRequirement(
    name="airway_management", 
    question="Is the patient's airway clear and protected?", 
    dependencies={
        1.0: ["breathing_support"],  # If airway good, check breathing
        0.0: ["emergency_protocols"]  # If airway compromised, emergency
    }
)

breathing_support = BinaryRequirement(
    name="breathing_support", 
    question="Is the patient breathing adequately?", 
    dependencies={
        1.0: ["circulation_check"],  # If breathing good, check circulation
        0.0: ["emergency_protocols"]  # If breathing poor, emergency
    }
)

bleeding_control = BinaryRequirement(
    name="bleeding_control", 
    question="Has any significant bleeding been controlled?", 
    dependencies={
        1.0: ["transport_decision"],  # If bleeding controlled, ready for transport
        0.0: ["emergency_protocols"]  # If bleeding uncontrolled, emergency
    }
)

circulation_check = BinaryRequirement(
    name="circulation_check", 
    question="Does the patient have adequate circulation and pulse?", 
    dependencies={
        1.0: ["transport_decision"],  # If circulation good, consider transport
        0.0: ["emergency_protocols"]  # If circulation poor, emergency
    }
)

communication = BinaryRequirement(
    name="communication", 
    question="Can the patient communicate their symptoms clearly?", 
    dependencies={
        1.0: ["symptom_assessment", "medical_history"],  # If can communicate, gather info
        0.0: ["observation_assessment"]  # If can't communicate, rely on observation
    }
)

pain_assessment = BinaryRequirement(
    name="pain_assessment", 
    question="Has the patient's pain level been assessed and managed?", 
    dependencies={
        1.0: ["comfort_measures", "transport_decision"],  # If pain managed, comfort and transport
        0.0: ["pain_management"]  # If pain not managed, intervene
    }
)

immediate_intervention = BinaryRequirement(
    name="immediate_intervention", 
    question="Have immediate life-saving interventions been performed?", 
    dependencies={
        1.0: ["stabilization_check"],  # If interventions done, check stability
        0.0: ["emergency_protocols"]  # If interventions not done, emergency
    }
)

immobilization = BinaryRequirement(
    name="immobilization", 
    question="Has the patient been properly immobilized if needed?", 
    dependencies={
        1.0: ["transport_preparation"],  # If immobilized, prepare for transport
        0.0: ["injury_assessment"]  # If not immobilized, reassess injuries
    }
)

# Terminal nodes (no dependencies)
emergency_protocols = BinaryRequirement(
    name="emergency_protocols", 
    question="Have emergency protocols been activated and followed?"
)

transport_decision = BinaryRequirement(
    name="transport_decision", 
    question="Has the appropriate transport decision been made and executed?"
)

medical_history = BinaryRequirement(
    name="medical_history", 
    question="Has relevant medical history been obtained?"
)

symptom_assessment = BinaryRequirement(
    name="symptom_assessment", 
    question="Have the patient's symptoms been thoroughly assessed?"
)

observation_assessment = BinaryRequirement(
    name="observation_assessment", 
    question="Has a thorough observational assessment been completed?"
)

injury_assessment = BinaryRequirement(
    name="injury_assessment", 
    question="Have all injuries been properly assessed and documented?"
)

comfort_measures = BinaryRequirement(
    name="comfort_measures", 
    question="Have appropriate comfort measures been provided?"
)

pain_management = BinaryRequirement(
    name="pain_management", 
    question="Has appropriate pain management been provided?"
)

stabilization_check = BinaryRequirement(
    name="stabilization_check", 
    question="Has the patient been stabilized successfully?"
)

transport_preparation = BinaryRequirement(
    name="transport_preparation", 
    question="Has the patient been properly prepared for transport?"
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
    {
        "prompt": "you come across a patient who is unconcious and not breathing.",
        "completion": "First, I'll check if the scene is safe. Then I'll jump right into CPR.",
        "answer": {
            "scene_safety": 1.0,  # Scene is safe, proceed to assessments
            "initial_assessment": 0.0,  # Patient unconscious/unresponsive
            "airway_management": 0.0,  # Airway needs intervention
            "breathing_support": 0.0,  # Not breathing adequately
            "emergency_protocols": 1.0  # Emergency protocols activated
        }
    },
    {
        "prompt": "You arrive at a car accident where the patient is conscious and alert but has a deep laceration on their arm that's bleeding heavily.",
        "completion": "After ensuring scene safety, I'll apply direct pressure to control the bleeding while assessing their vital signs and checking for other injuries. Once bleeding is controlled, I'll gather their medical history and prepare for transport.",
        "answer": {
            "scene_safety": 1.0,  # Scene is safe
            "initial_assessment": 1.0,  # Patient conscious and responsive
            "trauma_check": 1.0,  # Visible trauma present
            "bleeding_control": 1.0,  # Bleeding controlled
            "communication": 1.0,  # Can communicate clearly
            "transport_decision": 1.0  # Ready for transport
        }
    },
    {
        "prompt": "You find an elderly patient who has fallen and is responsive but complaining of severe hip pain and unable to move their leg.",
        "completion": "I'll first ensure the scene is safe, then assess their consciousness and vital signs. Given the mechanism of injury and symptoms, I'll suspect a hip fracture and immobilize them before moving. I'll assess their pain level and provide comfort measures while preparing for transport.",
        "answer": {
            "scene_safety": 1.0,  # Scene is safe
            "initial_assessment": 1.0,  # Patient responsive
            "trauma_check": 1.0,  # Trauma from fall
            "pain_assessment": 0.0,  # Pain not yet managed
            "pain_management": 1.0,  # Pain management provided
            "immobilization": 1.0,  # Proper immobilization
            "transport_preparation": 1.0  # Prepared for transport
        }
    },
    {
        "prompt": "At a construction site, a worker is trapped under debris with visible injuries and is calling for help.",
        "completion": "This scene may not be safe to approach immediately. I need to ensure the area is secure and get proper equipment before approaching. Once safe, I'll assess their consciousness and injuries while coordinating with rescue teams for safe extrication and immediate trauma care.",
        "answer": {
            "scene_safety": 0.0  # Scene unsafe - terminates workflow early
        }
    }
]