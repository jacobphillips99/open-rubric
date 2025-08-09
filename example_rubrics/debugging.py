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
            "problem_reproduction": {
                "answer": 1.0,
                "reasoning": "Reproducing the issue with a test order over $100 to observe the exact error behavior",
            },
            "error_analysis": {
                "answer": 1.0,
                "reasoning": "Examining the specific 500 Internal Server Error and stack trace from server logs",
            },
            "log_examination": {
                "answer": 1.0,
                "reasoning": "Looking at server logs around 3 PM yesterday to identify the error patterns and timing",
            },
            "timeline_analysis": {
                "answer": 1.0,
                "reasoning": "Analyzing the timeline of when the error started (yesterday 3 PM) and recent deployments",
            },
            "hypothesis_formation": {
                "answer": 1.0,
                "reasoning": "Forming hypothesis about payment processing timeout based on error analysis and timeline",
            },
        },
        _hidden_description="""
        Root cause and complete technical context: The e-commerce platform uses a third-party payment processor (StripeConnect) with a tiered fraud detection system. Yesterday at 2:45 PM, the payment processor automatically updated their fraud detection algorithms and reduced the timeout threshold for "high-value" transactions from 30 seconds to 15 seconds as part of a security enhancement.
        Technical details: Orders over $100 are classified as "high-value" and trigger additional fraud checks including real-time identity verification, address validation, and velocity checking. These checks typically take 18-22 seconds to complete. With the new 15-second timeout, 20% of these transactions (those taking longer than 15 seconds) now fail with a SocketTimeoutException that manifests as a 500 error to end users.
        System behavior: The application's payment service wrapper catches the timeout exception and logs it as "Payment processing timeout for order ${orderId}" with stack trace pointing to the StripeConnect API call. The error occurs specifically in the PaymentProcessor.processHighValueOrder() method at line 127 where it waits for the fraud check response.
        Deployment and configuration: No code deployments occurred yesterday. The payment service configuration file still shows the old 30-second timeout expectation. The application assumes the external service will respond within 30 seconds, but the service now cuts off at 15 seconds. The issue is intermittent because fraud check duration varies based on customer history and transaction complexity.
        Environmental factors: The issue affects all environments (dev, staging, prod) equally. Logs show consistent patterns: all failed transactions are >$100, all have timestamp around when fraud checks would timeout, and all have the same stack trace signature. The payment processor's status page doesn't show any reported issues since this was an intentional security update on their side.
        Customer impact: Customers see generic "payment failed" message and assume their card was declined. Cart contents are preserved and they can retry, but customer satisfaction is declining. Customer service is receiving increased calls about "card declined" issues that actually aren't card problems.
        """,
    ),
    Scenario(
        name="iOS App Crash",
        description="Mobile app crashing on specific iOS version",
        prompt="The mobile app keeps crashing on startup for iOS users with version 14.5, but works fine on other iOS versions. The crash reports show it's happening in the authentication module, but the logs don't provide clear error messages.",
        completion="Since this is specific to iOS 14.5, I'll compare the authentication flow between different iOS versions to identify compatibility issues. I'll review recent changes to the authentication module and check if we're using any APIs that behave differently in iOS 14.5. I'll also examine our dependency versions to see if any libraries have known iOS 14.5 compatibility issues.",
        answers={
            "problem_reproduction": {
                "answer": 1.0,
                "reasoning": "Testing the app startup on iOS 14.5 specifically to reproduce the crash consistently",
            },
            "error_analysis": {
                "answer": 0.0,
                "reasoning": "Logs don't provide clear error messages, making specific error analysis difficult",
            },
            "system_state_analysis": {
                "answer": 1.0,
                "reasoning": "Analyzing the authentication module state and iOS version-specific behavior differences",
            },
            "environment_comparison": {
                "answer": 1.0,
                "reasoning": "Comparing authentication flow between iOS 14.5 and other iOS versions to identify differences",
            },
            "code_review": {
                "answer": 1.0,
                "reasoning": "Reviewing recent changes to authentication module and iOS 14.5 API compatibility",
            },
            "dependency_check": {
                "answer": 1.0,
                "reasoning": "Examining dependency versions for known iOS 14.5 compatibility issues",
            },
        },
    ),
    Scenario(
        name="Database Performance Issue",
        description="Slow query performance affecting user experience",
        prompt="Users are reporting that search functionality has become very slow over the past week. Database queries that used to take 100ms are now taking 3-5 seconds. The search feature worked fine until recently, but no code changes were made to the search module.",
        completion="I'll first try to reproduce the slow search behavior to understand the scope. Then I'll examine the database logs to see if there are any error messages or unusual patterns. I'll analyze the query execution plans to identify what's causing the slowdown and check if there have been any database configuration changes or if indexes need rebuilding.",
        answers={
            "problem_reproduction": {
                "answer": 1.0,
                "reasoning": "Reproducing the slow search behavior to understand the scope and timing of the issue",
            },
            "log_examination": {
                "answer": 1.0,
                "reasoning": "Examining database logs for error messages, unusual patterns, and query performance metrics",
            },
            "timeline_analysis": {
                "answer": 1.0,
                "reasoning": "Analyzing when the performance degraded (past week) and correlating with system changes",
            },
            "configuration_validation": {
                "answer": 1.0,
                "reasoning": "Checking for database configuration changes or index issues that could cause slowdowns",
            },
            "system_state_analysis": {
                "answer": 1.0,
                "reasoning": "Analyzing query execution plans and database system state for performance bottlenecks",
            },
        },
        _hidden_description="""
        Complete technical situation: The application is a product catalog system with a PostgreSQL database containing 2.5 million product records. The search functionality uses a complex query with multiple JOINs across products, categories, brands, and inventory tables, along with full-text search on product descriptions.
        Root cause analysis: Eight days ago, the marketing team bulk-imported 500,000 new product records for a seasonal catalog expansion. This import process ran over the weekend and completed successfully. However, the bulk import bypassed the normal incremental index maintenance that occurs during regular product additions.
        Database state details: The critical composite index on (category_id, brand_id, availability_status) that the search query relies on has become severely fragmented due to the bulk insert. Index fragmentation is at 87% (normal is <10%). The PostgreSQL query planner is now choosing table scans over index seeks because the fragmented index is less efficient than sequential reads for large result sets.
        Performance metrics: Query execution plans show the problematic query now performs full table scans on the products table (2.5M rows) and categories table (15K rows) instead of using the optimized index path. Disk I/O has increased 40x for search operations. Memory usage spikes during searches due to larger working sets needed for table scans.
        System behavior: The search slowdown affects all search queries, but is most pronounced for broad category searches that would normally benefit most from the index. Specific product ID lookups are still fast because they use the primary key index which wasn't affected. Database CPU utilization spikes to 80%+ during search operations, and query queue depths increase significantly during peak usage.
        Related symptoms: The nightly VACUUM ANALYZE job is taking 3x longer to complete due to the larger dataset and fragmented indexes. Application connection pool is occasionally exhausting during peak search times. No errors are logged - just poor performance metrics.
        """,
    ),
]
