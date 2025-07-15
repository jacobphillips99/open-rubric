"""
Software Debugging Workflow Example.

This example demonstrates a narrower, deeper workflow for software debugging
situations. It shows sequential investigation steps and hypothesis-driven
problem solving typical of debugging processes.
"""

from verifiers.rubrics.multistep.requirement import BinaryRequirement
from verifiers.rubrics.multistep.scenario import Scenario

# Software debugging workflow - narrower and deeper with sequential steps
problem_reproduction = BinaryRequirement(
    name="problem_reproduction",
    question="Does the response consider reproducing the reported problem to understand its scope?",
    dependencies={
        1.0: ["error_analysis", "log_examination"],  # If reproducible, analyze further
        0.0: ["information_gathering"],  # If not reproducible, gather more info
    },
)

error_analysis = BinaryRequirement(
    name="error_analysis",
    question="Does the response consider analyzing the specific error messages or symptoms?",
    dependencies={
        1.0: [
            "code_review",
            "dependency_check",
        ],  # If clear error, examine code and deps
        0.0: ["system_state_analysis"],  # If unclear error, check system state
    },
)

log_examination = BinaryRequirement(
    name="log_examination",
    question="Does the response consider examining relevant logs for additional context?",
    dependencies={
        1.0: ["timeline_analysis"],  # If logs available, analyze timeline
        0.0: ["monitoring_setup"],  # If no logs, set up monitoring
    },
)

information_gathering = BinaryRequirement(
    name="information_gathering",
    question="Does the response consider gathering additional information about the problem context?",
    dependencies={
        1.0: ["environment_comparison"],  # If more info gathered, compare environments
        0.0: [],  # Dead end - insufficient information
    },
)

code_review = BinaryRequirement(
    name="code_review",
    question="Does the response consider reviewing the relevant code sections for potential issues?",
    dependencies={
        1.0: ["hypothesis_formation"],  # If code issues found, form hypothesis
        0.0: ["dependency_check"],  # If code looks good, check dependencies
    },
)

dependency_check = BinaryRequirement(
    name="dependency_check",
    question="Does the response consider checking dependencies, versions, and external services?",
    dependencies={
        1.0: ["configuration_validation"],  # If dependency issues, check config
        0.0: ["hypothesis_formation"],  # If dependencies OK, form other hypothesis
    },
)

system_state_analysis = BinaryRequirement(
    name="system_state_analysis",
    question="Does the response consider analyzing the overall system state and resources?",
    dependencies={
        1.0: ["configuration_validation"],  # If system issues found, check config
        0.0: ["monitoring_setup"],  # If system state unclear, set up monitoring
    },
)

timeline_analysis = BinaryRequirement(
    name="timeline_analysis",
    question="Does the response consider analyzing the timeline of events leading to the problem?",
    dependencies={
        1.0: ["hypothesis_formation"],  # If timeline reveals patterns, form hypothesis
        0.0: ["monitoring_setup"],  # If timeline unclear, need better monitoring
    },
)

environment_comparison = BinaryRequirement(
    name="environment_comparison",
    question="Does the response consider comparing different environments (dev, staging, prod)?",
    dependencies={
        1.0: ["configuration_validation"],  # If env differences found, check config
        0.0: ["hypothesis_formation"],  # If envs similar, form other hypothesis
    },
)

hypothesis_formation = BinaryRequirement(
    name="hypothesis_formation",
    question="Does the response consider forming a testable hypothesis about the root cause?",
    dependencies={
        1.0: ["testing_strategy"],  # If hypothesis formed, create test strategy
        0.0: ["monitoring_setup"],  # If can't form hypothesis, set up better monitoring
    },
)

configuration_validation = BinaryRequirement(
    name="configuration_validation",
    question="Does the response consider validating configuration files and settings?",
    dependencies={
        1.0: ["fix_implementation"],  # If config issues found, implement fix
        0.0: ["monitoring_setup"],  # If config OK, need more monitoring for insights
    },
)

testing_strategy = BinaryRequirement(
    name="testing_strategy",
    question="Does the response consider developing a strategy to test the hypothesis?",
    dependencies={
        1.0: ["fix_implementation"],  # If test confirms hypothesis, implement fix
        0.0: ["monitoring_setup"],  # If test disproves hypothesis, need better data
    },
)

# Terminal nodes
monitoring_setup = BinaryRequirement(
    name="monitoring_setup",
    question="Does the response consider setting up monitoring or logging to gather more data?",
)

fix_implementation = BinaryRequirement(
    name="fix_implementation",
    question="Does the response consider implementing a fix and validating it works?",
)

# List of all requirements for the debugging workflow
requirements = [
    problem_reproduction,
    error_analysis,
    log_examination,
    information_gathering,
    code_review,
    dependency_check,
    system_state_analysis,
    timeline_analysis,
    environment_comparison,
    hypothesis_formation,
    configuration_validation,
    testing_strategy,
    monitoring_setup,
    fix_implementation,
]

# Test scenarios for debugging workflow
scenarios = [
    Scenario(
        name="E-commerce Checkout Error",
        description="Payment processing failure for large orders",
        prompt="A user reports that the checkout process on your e-commerce website is failing with a '500 Internal Server Error' but only for orders over $100. The error started happening yesterday around 3 PM and affects about 20% of users attempting large purchases.",
        completion="I'll start by reproducing the issue with a test order over $100 to see the exact error. Looking at the server logs around 3 PM yesterday, I can see the specific error stack trace pointing to a payment processing timeout. I'll examine the payment service configuration and recent deployments to understand what changed.",
        answers={
            "problem_reproduction": 1.0,
            "error_analysis": 1.0,
            "log_examination": 1.0,
            "timeline_analysis": 1.0,
            "hypothesis_formation": 1.0,
        },
    ),
    Scenario(
        name="iOS App Crash",
        description="Mobile app crashing on specific iOS version",
        prompt="The mobile app keeps crashing on startup for iOS users with version 14.5, but works fine on other iOS versions. The crash reports show it's happening in the authentication module, but the logs don't provide clear error messages.",
        completion="Since this is specific to iOS 14.5, I'll compare the authentication flow between different iOS versions to identify compatibility issues. I'll review recent changes to the authentication module and check if we're using any APIs that behave differently in iOS 14.5. I'll also examine our dependency versions to see if any libraries have known iOS 14.5 compatibility issues.",
        answers={
            "problem_reproduction": 1.0,
            "error_analysis": 0.0,
            "system_state_analysis": 1.0,
            "environment_comparison": 1.0,
            "code_review": 1.0,
            "dependency_check": 1.0,
        },
    ),
    Scenario(
        name="Database Performance Issue",
        description="Slow query performance affecting user experience",
        prompt="Users are reporting that search functionality has become very slow over the past week. Database queries that used to take 100ms are now taking 3-5 seconds. The search feature worked fine until recently, but no code changes were made to the search module.",
        completion="I'll first try to reproduce the slow search behavior to understand the scope. Then I'll examine the database logs to see if there are any error messages or unusual patterns. I'll analyze the query execution plans to identify what's causing the slowdown and check if there have been any database configuration changes or if indexes need rebuilding.",
        answers={
            "problem_reproduction": 1.0,
            "log_examination": 1.0,
            "timeline_analysis": 1.0,
            "configuration_validation": 1.0,
            "system_state_analysis": 1.0,
        },
    ),
]
