"""
Quick demo of evaluation modes for the multistep system.
"""

import asyncio

from .tutorial import MultiStepTutorial


async def main():
    """Run just the evaluation modes demo."""
    tutorial = MultiStepTutorial()
    await tutorial.demonstrate_evaluation_modes()


if __name__ == "__main__":
    asyncio.run(main()) 