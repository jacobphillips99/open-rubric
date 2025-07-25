"""
Demo script showcasing the enhanced dependency graph visualization capabilities.

This demo creates a sample rubric with dependencies and shows improved visualization options
with better terminal state handling and usability improvements.
Run with: python -m multistep_extras.demos.demo_visualizer
"""

from pathlib import Path

import plotly.graph_objects as go

from multistep_extras.example_rubrics import get_workflow
from multistep_extras.visualization.visualizer import (
    RequirementsVisualizer, create_dependency_graph, create_metrics_dashboard)
from verifiers.rubrics.multistep.requirement import Requirement


def demo_enhanced_visualization(requirements: list[Requirement]) -> go.Figure:
    """Demonstrate enhanced dependency graph visualization with terminal state emphasis."""
    print("=== Enhanced Dependency Graph Demo ===")

    # Create enhanced dependency graph with terminal state emphasis
    fig = create_dependency_graph(
        requirements,
        show_answer_labels=True,
        show_terminal_states=True,
        show_requirement_types=True,
        width=1400,
        height=900,
    )

    # Add custom annotations for better usability
    fig.add_annotation(
        text="💎 Diamond shapes = Terminal states<br>🔵 Circles = Non-terminal states<br>🟢 Green edges = Positive answers<br>🔴 Red edges = Negative answers",
        xref="paper",
        yref="paper",
        x=0.02,
        y=0.98,
        showarrow=False,
        font=dict(size=12, color="#2c3e50"),
        align="left",
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="lightgray",
        borderwidth=1,
    )

    # Ensure outputs directory exists
    outputs_dir = Path("outputs") / "visualizations"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Save as HTML file for viewing
    output_file = outputs_dir / "enhanced_dependency_graph.html"
    fig.write_html(str(output_file))
    print(f"✅ Saved enhanced dependency graph to: {output_file}")

    return fig


def demo_enhanced_metrics_dashboard(requirements: list[Requirement]) -> go.Figure:
    """Demonstrate enhanced metrics dashboard with terminal state focus."""
    print("\n=== Enhanced Metrics Dashboard Demo ===")

    # Create enhanced metrics dashboard
    metrics_fig = create_metrics_dashboard(requirements)

    # Add terminal state analysis to the dashboard
    viz = RequirementsVisualizer(requirements)
    terminal_analysis = viz.create_terminal_analysis()

    # Add terminal state summary as annotation
    non_terminal_count = len(requirements) - terminal_analysis["terminal_nodes"]
    terminal_summary = (
        f"💎 Terminal Analysis:<br>"
        f"• {terminal_analysis['terminal_nodes']} terminal nodes<br>"
        f"• {non_terminal_count} non-terminal nodes<br>"
        f"• {terminal_analysis['terminal_percentage']:.1f}% terminal rate"
    )

    metrics_fig.add_annotation(
        text=terminal_summary,
        xref="paper",
        yref="paper",
        x=0.02,
        y=0.98,
        showarrow=False,
        font=dict(size=12, color="#2c3e50"),
        align="left",
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="lightgray",
        borderwidth=1,
    )

    # Ensure outputs directory exists
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)

    # Save as HTML file
    output_file = outputs_dir / "enhanced_metrics_dashboard.html"
    metrics_fig.write_html(str(output_file))
    print(f"✅ Saved enhanced metrics dashboard to: {output_file}")

    # Print detailed metrics
    metrics = viz.analyze_metrics()

    print("\n📊 Enhanced Workflow Metrics:")
    print(f"   Total Requirements: {metrics['total_requirements']}")
    print(
        f"   Terminal Nodes: {metrics['terminal_nodes']} ({terminal_analysis['terminal_percentage']:.1f}%)"
    )
    non_terminal_nodes = metrics["total_requirements"] - metrics["terminal_nodes"]
    print(f"   Non-Terminal Nodes: {non_terminal_nodes}")
    print(f"   Branching Nodes: {metrics['branching_nodes']}")
    print(f"   Maximum Depth: {metrics['max_depth']} levels")
    print(f"   Average Branching Factor: {metrics['avg_branching_factor']:.2f}")
    print(f"   Root Nodes: {', '.join(metrics['root_nodes'])}")

    return metrics_fig


def main():
    """Run enhanced visualization demos focusing on analytics and terminal states."""
    print(" Enhanced MultiStep Rubric Dependency Visualization Demo")
    print("=" * 70)
    print("Focus: Analytics & Terminal State Analysis")
    print("=" * 70)

    try:
        # Run only the enhanced demos (removed unwanted layouts)
        requirements, _ = get_workflow("first_responder")
        demo_enhanced_visualization(requirements)
        demo_enhanced_metrics_dashboard(requirements)

        print("\n🎉 Enhanced demos completed successfully!")
        print("   Key features:")
        print("   • 💎 Terminal states highlighted with diamond shapes")
        print("   • 🔵 Non-terminal states shown as circles")
        print("   • 🟢🔴 Edge colors indicate answer values")
        print("   • 📊 Enhanced metrics with terminal analysis")
        print("   • 🎯 Better usability with hover details and annotations")
        print("   • 📁 Files created in outputs/ directory:")

        output_files = [
            "outputs/visualizations/enhanced_dependency_graph.html",
            "outputs/enhanced_metrics_dashboard.html",
        ]

        for file_path in output_files:
            print(f"     - {file_path}")

        print(
            f"\n   Open the HTML files in your browser to explore the enhanced visualizations!"
        )

    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Please install: uv add plotly")
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        raise


if __name__ == "__main__":
    main()
