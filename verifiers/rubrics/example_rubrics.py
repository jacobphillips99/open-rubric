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

class Scenario:
    """
    Represents a test scenario for evaluating multi-step rubrics.
    
    Contains a prompt (situation description), completion (response), 
    and ground truth answer path for evaluation.
    """
    
    def __init__(self, prompt: str, answers: dict[str, float], completion: Optional[str] = None,
                 name: Optional[str] = None, description: Optional[str] = None):
        """
        Initialize a scenario.
        
        Args:
            prompt: The situation or question being presented
            completion: The response or actions taken
            answers: Ground truth path mapping requirement names to expected scores
            name: Optional name for the scenario
            description: Optional description of what this scenario tests
        """
        self.prompt = prompt
        self.answers = answers
        # scenarios may or may not have a completion; it might need to be generated
        self.completion = completion
        self.name = name
        self.description = description

    def to_content(self):
        return f"""
        prompt: {self.prompt}
        completion: {self.completion}
        """.strip()



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