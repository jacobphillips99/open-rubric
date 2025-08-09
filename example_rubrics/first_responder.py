"""
First Responder Workflow Example.

This example demonstrates a complex, wide-branching workflow for first responder
emergency medical situations. It shows parallel assessments and multiple decision
points typical of emergency response protocols.
"""

from verifiers.rubrics.multistep.requirement import BinaryRequirement
from verifiers.rubrics.multistep.scenario import Scenario

# First responder workflow - shorter and wider with more branching
scene_safety = BinaryRequirement(
    name="scene_safety",
    question="Does the response consider if the scene is safe to approach?",
    dependencies={
        1.0: [
            "initial_assessment",
            "vital_signs",
            "trauma_check",
        ],  # If safe, do parallel assessments
        0.0: [],  # If unsafe, stop workflow
    },
)

initial_assessment = BinaryRequirement(
    name="initial_assessment",
    question="Does the response consider if the patient is conscious and responsive?",
    dependencies={
        1.0: [
            "communication",
            "pain_assessment",
        ],  # If responsive, assess communication and pain
        0.0: [
            "airway_management",
            "breathing_support",
        ],  # If unresponsive, prioritize ABCs
    },
)

vital_signs = BinaryRequirement(
    name="vital_signs",
    question="Does the response consider if the patient's vital signs are stable?",
    dependencies={
        1.0: ["transport_decision"],  # If stable, consider transport
        0.0: [
            "immediate_intervention",
            "emergency_protocols",
        ],  # If unstable, immediate action
    },
)

trauma_check = BinaryRequirement(
    name="trauma_check",
    question="Does the response consider if there are visible signs of trauma or injury?",
    dependencies={
        1.0: [
            "bleeding_control",
            "immobilization",
            "injury_assessment",
        ],  # If trauma, multiple interventions
        0.0: [
            "medical_history",
            "symptom_assessment",
        ],  # If no trauma, focus on medical causes
    },
)

airway_management = BinaryRequirement(
    name="airway_management",
    question="Does the response consider if the patient's airway is clear and protected?",
    dependencies={
        1.0: ["breathing_support"],  # If airway good, check breathing
        0.0: ["emergency_protocols"],  # If airway compromised, emergency
    },
)

breathing_support = BinaryRequirement(
    name="breathing_support",
    question="Does the response consider if the patient is breathing adequately?",
    dependencies={
        1.0: ["circulation_check"],  # If breathing good, check circulation
        0.0: ["emergency_protocols"],  # If breathing poor, emergency
    },
)

bleeding_control = BinaryRequirement(
    name="bleeding_control",
    question="Does the response consider if any significant bleeding has been controlled?",
    dependencies={
        1.0: ["transport_decision"],  # If bleeding controlled, ready for transport
        0.0: ["emergency_protocols"],  # If bleeding uncontrolled, emergency
    },
)

circulation_check = BinaryRequirement(
    name="circulation_check",
    question="Does the response consider if the patient has adequate circulation and pulse?",
    dependencies={
        1.0: ["transport_decision"],  # If circulation good, consider transport
        0.0: ["emergency_protocols"],  # If circulation poor, emergency
    },
)

communication = BinaryRequirement(
    name="communication",
    question="Does the response consider if the patient can communicate their symptoms clearly?",
    dependencies={
        1.0: [
            "symptom_assessment",
            "medical_history",
        ],  # If can communicate, gather info
        0.0: ["observation_assessment"],  # If can't communicate, rely on observation
    },
)

pain_assessment = BinaryRequirement(
    name="pain_assessment",
    question="Does the response consider if the patient's pain level has been assessed and managed?",
    dependencies={
        1.0: [
            "comfort_measures",
            "transport_decision",
        ],  # If pain managed, comfort and transport
        0.0: ["pain_management"],  # If pain not managed, intervene
    },
)

immediate_intervention = BinaryRequirement(
    name="immediate_intervention",
    question="Does the response consider if immediate life-saving interventions have been performed?",
    dependencies={
        1.0: ["stabilization_check"],  # If interventions done, check stability
        0.0: ["emergency_protocols"],  # If interventions not done, emergency
    },
)

immobilization = BinaryRequirement(
    name="immobilization",
    question="Does the response consider if the patient has been properly immobilized if needed?",
    dependencies={
        1.0: ["transport_preparation"],  # If immobilized, prepare for transport
        0.0: ["injury_assessment"],  # If not immobilized, reassess injuries
    },
)

# Terminal nodes (no dependencies)
emergency_protocols = BinaryRequirement(
    name="emergency_protocols",
    question="Does the response consider if emergency protocols have been activated and followed?",
)

transport_decision = BinaryRequirement(
    name="transport_decision",
    question="Does the response consider if the appropriate transport decision has been made and executed?",
)

medical_history = BinaryRequirement(
    name="medical_history",
    question="Does the response consider if relevant medical history has been obtained?",
)

symptom_assessment = BinaryRequirement(
    name="symptom_assessment",
    question="Does the response consider if the patient's symptoms have been thoroughly assessed?",
)

observation_assessment = BinaryRequirement(
    name="observation_assessment",
    question="Does the response consider if a thorough observational assessment has been completed?",
)

injury_assessment = BinaryRequirement(
    name="injury_assessment",
    question="Does the response consider if all injuries have been properly assessed and documented?",
)

comfort_measures = BinaryRequirement(
    name="comfort_measures",
    question="Does the response consider if appropriate comfort measures have been provided?",
)

pain_management = BinaryRequirement(
    name="pain_management",
    question="Does the response consider if appropriate pain management has been provided?",
)

stabilization_check = BinaryRequirement(
    name="stabilization_check",
    question="Does the response consider if the patient has been stabilized successfully?",
)

transport_preparation = BinaryRequirement(
    name="transport_preparation",
    question="Does the response consider if the patient has been properly prepared for transport?",
)

# List of all requirements for the first responder workflow
requirements = [
    scene_safety,
    initial_assessment,
    vital_signs,
    trauma_check,
    airway_management,
    breathing_support,
    bleeding_control,
    circulation_check,
    communication,
    pain_assessment,
    immediate_intervention,
    immobilization,
    emergency_protocols,
    transport_decision,
    medical_history,
    symptom_assessment,
    observation_assessment,
    injury_assessment,
    comfort_measures,
    pain_management,
    stabilization_check,
    transport_preparation,
]

# Test scenarios for first responder workflow
scenarios = [
    Scenario(
        name="Unconscious Non-Breathing Patient",
        description="Patient is unconscious and not breathing in a safe environment",
        prompt="You are a first responder arriving at a residential street. You come across a patient who is unconscious and not breathing, lying on the sidewalk. There are no immediate hazards visible, no electrical wires down, no fire, and no aggressive bystanders. The area appears secure.",
        completion="First, I'll check if the scene is safe. Since there are no visible hazards, I'll proceed. The patient is unconscious and not breathing, so I'll immediately check their airway and begin CPR. I'll call for advanced life support and continue resuscitation efforts.",
        answers={
            "scene_safety": {
                "answer": 1.0,
                "reasoning": "The residential street has no visible hazards, electrical wires, fire, or aggressive bystanders",
            },
            "initial_assessment": {
                "answer": 0.0,
                "reasoning": "Patient is unconscious and not breathing, requiring immediate life support",
            },
            "airway_management": {
                "answer": 0.0,
                "reasoning": "Airway needs immediate attention as patient is not breathing",
            },
            "breathing_support": {
                "answer": 0.0,
                "reasoning": "Patient is not breathing and requires immediate respiratory support",
            },
            "emergency_protocols": {
                "answer": 1.0,
                "reasoning": "CPR initiated and advanced life support called",
            },
        },
    ),
    Scenario(
        name="Car Accident with Bleeding",
        description="Conscious patient with significant bleeding from car accident",
        prompt="You arrive at a car accident scene on a quiet suburban road. The vehicle has come to rest safely on the shoulder, away from traffic. The patient is conscious, alert, and sitting in the driver's seat but has a deep laceration on their left arm that's bleeding heavily, soaking through their shirt.",
        completion="After confirming scene safety and ensuring no traffic hazards, I'll approach the patient. They're alert and responsive, so I'll introduce myself and explain what I'm doing. I'll immediately apply direct pressure to the arm wound to control bleeding while simultaneously assessing their vital signs and checking for other injuries. Once bleeding is controlled, I'll gather their medical history and symptoms, then prepare them for transport to the hospital.",
        answers={
            "scene_safety": {
                "answer": 1.0,
                "reasoning": "Vehicle is safely positioned on the shoulder away from traffic hazards",
            },
            "initial_assessment": {
                "answer": 1.0,
                "reasoning": "Patient is conscious, alert, and sitting upright in driver's seat",
            },
            "trauma_check": {
                "answer": 1.0,
                "reasoning": "Visible deep laceration on left arm with heavy bleeding identified",
            },
            "bleeding_control": {
                "answer": 1.0,
                "reasoning": "Direct pressure applied to arm wound to control bleeding",
            },
            "communication": {
                "answer": 1.0,
                "reasoning": "Patient is alert and responsive, able to communicate effectively",
            },
            "transport_decision": {
                "answer": 1.0,
                "reasoning": "Patient prepared for hospital transport after bleeding control",
            },
        },
        _hidden_description="""
        Complete scene details: A 28-year-old female driver lost control of her sedan on a wet suburban road around 2 PM during light rain. Vehicle skidded off the road and collided with a roadside sign post at approximately 25 mph before coming to rest completely on the grass shoulder, 15 feet from active traffic lanes. Vehicle sustained front-end damage but no structural compromise to passenger compartment.
        Patient status: Driver was wearing seatbelt and remained conscious throughout incident. No head impact with steering wheel or windows. Deep 4-inch laceration on left forearm from broken side window glass during impact. Bleeding is arterial but controllable with direct pressure. No other visible injuries. Patient reports pain level 6/10 at injury site, neck and back feel fine. No dizziness, nausea, or vision changes. Fully alert and oriented to person, place, and time.
        Environmental conditions: Scene is stable with no ongoing hazards. Vehicle is off roadway with hazard lights activated. Good visibility and weather has improved. No fuel leaks, electrical hazards, or structural collapse risks. Other motorists are giving appropriate distance. Patient has cell phone and was able to call for help. No other occupants in vehicle.
        Medical history: Patient reports no significant medical history, no current medications, no allergies. Last meal was lunch 2 hours ago. Not pregnant. Lives locally and has family members who can meet at hospital.
        """,
    ),
    Scenario(
        name="Elderly Fall with Hip Injury",
        description="Elderly patient with suspected hip fracture from fall",
        prompt="You find an elderly patient (approximately 75 years old) who has fallen in their bathroom. They are awake and oriented but complaining of severe pain in their right hip (8/10 on pain scale) and are completely unable to move their right leg. They describe hearing a 'pop' when they fell. The scene is secure with no ongoing hazards.",
        completion="After ensuring scene safety, I'll assess their level of consciousness - they're alert and oriented. Given the mechanism of injury (fall), their age, the severe hip pain, inability to move the leg, and the audible 'pop', I strongly suspect a hip fracture. I'll assess their current pain level, provide initial pain management if within my scope, and carefully immobilize them in position before any movement. I'll prepare them for transport while providing comfort measures.",
        answers={
            "scene_safety": {
                "answer": 1.0,
                "reasoning": "Bathroom environment is secure with no ongoing hazards",
            },
            "initial_assessment": {
                "answer": 1.0,
                "reasoning": "Patient is awake, oriented, and able to communicate",
            },
            "trauma_check": {
                "answer": 1.0,
                "reasoning": "Fall mechanism with audible 'pop' and inability to move leg indicates trauma",
            },
            "pain_assessment": {
                "answer": 1.0,
                "reasoning": "Severe hip pain assessed at 8/10 on pain scale",
            },
            "pain_management": {
                "answer": 1.0,
                "reasoning": "Initial pain management provided within scope of practice",
            },
            "immobilization": {
                "answer": 1.0,
                "reasoning": "Patient carefully immobilized in position due to suspected hip fracture",
            },
            "transport_preparation": {
                "answer": 1.0,
                "reasoning": "Patient prepared for transport with comfort measures",
            },
        },
        _hidden_description="""
        Complete incident details: Margaret Thompson, 75-year-old retired teacher, lives alone in a single-story home. Around 6 AM while getting ready for the day, she stepped out of her shower onto a slightly wet bath mat. The mat slipped on the tile floor, causing her to fall backwards and land hard on her right side, striking her hip against the edge of the bathtub.

        Patient condition: Right hip fracture (displaced femoral neck fracture). Patient heard and felt distinct 'pop' during impact. Severe pain rated 8/10, localized to right hip and radiating down thigh. Right leg is externally rotated and shortened by approximately 1 inch compared to left leg. Cannot bear any weight or move right leg voluntarily. Pain increases dramatically with any attempted movement.

        Patient status: Fully conscious and oriented to person, place, time. Vital signs: BP 150/90 (elevated due to pain), HR 95, RR 18, temp 98.6°F. Skin pale and diaphoretic from pain but no signs of shock. No head injury, no loss of consciousness. Alert and cooperative but distressed from pain. No other injuries identified.

        Environment and access: Bathroom floor is now dry and safe. Patient is lying on bathroom floor next to bathtub. Space is adequate for responder access and equipment. Front door was unlocked - patient called neighbor who let responders in. Heat is on, patient has blanket over torso. No obstacles or hazards present.

        Medical history: Osteoporosis (takes calcium and vitamin D), mild hypertension (on lisinopril), no other significant medical conditions. No drug allergies. Last meal was evening snack around 9 PM yesterday. Lives independently, very active for her age, does her own shopping and cooking.
        """,
    ),
]
advanced_scenarios = [
    Scenario(
        name="Progressive Emergency Response",
        description="First responder scenario with progressive information revelation",
        prompt="You are a first responder arriving at a scene. A person is on the ground. Your view is limited.",
        answers={
            "scene_safety": {
                "answer": 1.0,
                "reasoning": "Area is secure with no traffic, electrical, or personal safety hazards",
            },
            "initial_assessment": {
                "answer": 0.0,
                "reasoning": "Patient is unconscious with no response to verbal stimuli",
            },
            "vital_signs": {
                "answer": 0.0,
                "reasoning": "Patient vitals are unstable - unconscious with irregular breathing pattern",
            },
            "trauma_check": {
                "answer": 0.0,
                "reasoning": "No visible signs of trauma or injury observed during initial assessment",
            },
            "breathing_support": {
                "answer": 0.0,
                "reasoning": "Inadequate breathing pattern detected requiring immediate intervention",
            },
            "emergency_protocols": {
                "answer": 1.0,
                "reasoning": "Emergency services contacted and advanced life support en route",
            },
        },
        revealed_info={
            "scene_safety": "Scene Assessment: No traffic, electrical hazards, or dangerous individuals present.",
            "initial_assessment": "Patient Status: Adult male, unconscious. Eyes closed, no response to verbal stimuli.",
            "vital_signs": "Vital Signs: Pulse weak and rapid, blood pressure dropping, skin pale and clammy.",
            "trauma_check": "Trauma Assessment: No visible external bleeding, no obvious fractures or deformities.",
            "breathing_support": "Breathing Assessment: Shallow, irregular breathing pattern detected.",
            "emergency_protocols": "Emergency Resources: Emergency radio frequencies are available and functioning.",
        },
        _hidden_description="""
        Complete incident details: James Rodriguez, 42-year-old construction supervisor, was inspecting a residential construction site at 7:30 AM when he suffered a massive heart attack (STEMI - ST-elevation myocardial infarction) due to undiagnosed severe coronary artery disease. He collapsed instantly while standing on level ground near the foundation of a house under construction.
        Patient medical status: Acute anterior wall myocardial infarction with complete blockage of the left anterior descending (LAD) coronary artery. Patient is in cardiogenic shock with severely compromised cardiac output. Blood pressure: 70/40 and dropping, heart rate: 140 irregular (ventricular tachycardia), respiratory rate: 6-8 irregular and shallow. Oxygen saturation: 78%. Skin is cold, clammy, pale, and cyanotic around lips and fingernails.
        Consciousness and neurological: Patient is unconscious due to poor cerebral perfusion from cardiogenic shock. No response to verbal stimuli, minimal response to painful stimuli. Pupils are equal and reactive but sluggish. No signs of head trauma or seizure activity. Glasgow Coma Scale: 6 (E1 V1 M4).
        Physical assessment: No external trauma, no visible bleeding, no obvious fractures. Patient fell straight down when he collapsed, so no mechanism for traumatic injury. Breathing is agonal - irregular, gasping pattern indicating brainstem response to severe hypoxia. Chest appears symmetrical but patient will likely need immediate advanced cardiac life support.
        Environmental conditions: Construction site is secure with no active hazards. Site has been cleared of workers and equipment. Good access for emergency vehicles. Weather is clear and dry. Scene is well-lit and safe to approach. No electrical hazards, no structural dangers, no traffic concerns. Emergency communications are available and functional.
        Timeline and prognosis: Collapse occurred approximately 5 minutes before responder arrival. For this type of cardiac event, immediate advanced life support and rapid transport to a cardiac catheterization lab is critical. Patient will need immediate CPR, defibrillation, cardiac medications, and emergency PCI (percutaneous coronary intervention) to survive.
        """,
    ),
]
